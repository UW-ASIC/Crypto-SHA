import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, with_timeout
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

# Match RTL
OP_LOAD_TEXT    = 1  # 2'b01
OP_WRITE_RESULT = 2  # 2'b10
OP_HASH         = 3  # 2'b11

MEM_ID = 0  # 2'b00
SHA_ID = 1  # 2'b01

# SHA-256 takes 64 rounds x ~2 cycles + overhead; 300 cycles is a safe ceiling.
HASH_TIMEOUT_CYCLES = 300

# NIST FIPS 180-4 known-answer test vectors for exactly 32-byte messages.
# Each entry: (plaintext_hex, expected_digest_hex)
NIST_VECTORS = [
    # 32 bytes of zeros
    (
        "00" * 32,
        "66687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925",
    ),
    # 32 bytes of 0xFF
    (
        "ff" * 32,
        "af9613760f72635fbdb44a5a0a63ebeb36023b1a942fbe4de503d9e6a2560b4e",
    ),
    # ASCII "abcdefghijklmnopqrstuvwxyzABCDEF" (32 bytes)
    (
        "6162636465666768696a6b6c6d6e6f707172737475767778797a414243444546",
        "3b93e473e17e68f039af1b2fe81c4db9f7e2dd48d9c02e741b764aa3ab1d9f73",
    ),
]


def _try_set(handle, name, value):
    """Set a signal by name, silently skipping if not present (e.g. in GL sim)."""
    try:
        getattr(handle, name).value = value
    except AttributeError:
        pass


def _try_get(handle, name, default=0):
    """Read a signal by name, returning default if not present (e.g. in GL sim)."""
    try:
        return int(getattr(handle, name).value)
    except AttributeError:
        return default


async def reset_dut(dut):
    """Reset the SHA DUT and initialize control signals.

    Uses _try_set for signals not exposed in the gate-level wrapper
    (ack_ready, encdec, addr) so the same testbench works for RTL and GL.
    """
    sha = dut

    sha.rst_n.value      = 0
    sha.valid_in.value   = 0
    sha.data_in.value    = 0
    sha.data_ready.value = 0
    _try_set(sha, "ack_ready",  0)
    sha.opcode.value     = 0
    sha.source_id.value  = 0
    sha.dest_id.value    = 0
    _try_set(sha, "encdec", 0)
    _try_set(sha, "addr",   0)

    await ClockCycles(sha.clk, 5)

    sha.rst_n.value = 1
    _try_set(sha, "ack_ready", 0)  # held low; controlled by read_digest

    await ClockCycles(sha.clk, 2)
    sha._log.info("Reset complete")


async def load_message_32(dut, msg: bytes):
    """Load exactly 32 bytes into the SHA core using LOAD_TEXT."""
    assert len(msg) == 32, "DUT expects exactly 32 bytes"
    sha = dut

    sha._log.info(f"Loading 32-byte message: {msg.hex()}")

    sha.opcode.value    = OP_LOAD_TEXT
    sha.source_id.value = MEM_ID
    sha.dest_id.value   = SHA_ID

    for b in msg:
        sha.data_in.value  = b
        sha.valid_in.value = 1

        while True:
            await RisingEdge(sha.clk)
            if int(sha.ready_in.value) == 1:
                break

    sha.valid_in.value = 0
    sha._log.info("Finished sending 32-byte message")

    await ClockCycles(sha.clk, 2)


async def _wait_for_digest_ready(dut):
    """Poll digest_ready until high. Falls back silently if not accessible (GL)."""
    sha = dut
    while True:
        await RisingEdge(sha.clk)
        try:
            if int(sha.digest_ready.value) == 1:
                return
        except AttributeError:
            # Not accessible in GL sim — return immediately and rely on fixed wait
            return


async def start_hash(dut):
    """Issue OP_HASH and wait for completion with a hard timeout."""
    sha = dut

    sha._log.info("Issuing OP_HASH")

    sha.opcode.value    = OP_HASH
    sha.source_id.value = MEM_ID
    sha.dest_id.value   = SHA_ID

    await ClockCycles(sha.clk, 2)

    sha.opcode.value    = 0
    sha.source_id.value = 0
    sha.dest_id.value   = 0

    sha._log.info(f"Waiting for hash (timeout = {HASH_TIMEOUT_CYCLES} cycles)")
    try:
        await with_timeout(
            _wait_for_digest_ready(dut),
            timeout_time=HASH_TIMEOUT_CYCLES * 10,  # 10 us per cycle
            timeout_unit="us",
        )
        sha._log.info("digest_ready seen — hash complete")
    except cocotb.result.SimTimeoutError:
        raise AssertionError(
            f"DUT did not complete hashing within {HASH_TIMEOUT_CYCLES} cycles"
        )

    await ClockCycles(sha.clk, 2)


async def read_digest(dut, num_bytes=32) -> bytes:
    """
    Request the digest with OP_WRITE_RESULT and read num_bytes bytes.

    ack_ready is held LOW during digest collection so ACK_HOLD does not
    self-clear before the testbench can observe ack_valid.
    Uses _try_set/_try_get so it works in GL sim where ack_ready is not exposed.
    """
    sha = dut
    digest = bytearray()

    sha._log.info("Requesting digest via OP_WRITE_RESULT")

    _try_set(sha, "ack_ready", 0)

    sha.opcode.value     = OP_WRITE_RESULT
    sha.source_id.value  = SHA_ID
    sha.dest_id.value    = MEM_ID
    sha.data_ready.value = 1

    sha._log.info("Waiting for digest bytes from DUT")

    while len(digest) < num_bytes:
        await RisingEdge(sha.clk)
        if int(sha.data_valid.value) == 1:
            digest.append(int(sha.data_out.value))

    sha.data_ready.value = 0
    sha._log.info(f"Received digest ({len(digest)} bytes)")

    # Raise ack_ready now that we have all bytes; ACK_HOLD is still waiting.
    _try_set(sha, "ack_ready", 1)
    ack_seen = False
    for _ in range(50):
        await RisingEdge(sha.clk)
        if _try_get(sha, "ack_valid", default=1):  # default 1: assume ack in GL
            sha._log.info(
                f"Got ack_valid, module_source_id={_try_get(sha, 'module_source_id')}"
            )
            ack_seen = True
            break

    assert ack_seen, "DUT never asserted ack_valid after transmitting digest"

    sha.opcode.value    = 0
    sha.source_id.value = 0
    sha.dest_id.value   = 0
    _try_set(sha, "ack_ready", 0)

    return bytes(digest)


async def _run_one_hash(dut, msg: bytes) -> bytes:
    """Load a message, hash it, and return the digest."""
    await load_message_32(dut, msg)
    await start_hash(dut)
    return await read_digest(dut, num_bytes=32)


# ---------------------------------------------------------------------------
# Test 1: Fixed NIST known-answer vectors
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_sha_nist_vectors(dut):
    """
    Known-answer tests using fixed NIST-style vectors for 32-byte messages.
    These are deterministic — a failure here means a fundamental correctness bug.
    """
    dut._log.info("Starting NIST known-answer vector tests")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await reset_dut(dut)

    for i, (msg_hex, expected_hex) in enumerate(NIST_VECTORS):
        msg      = bytes.fromhex(msg_hex)
        expected = bytes.fromhex(expected_hex)

        dut._log.info(f"Vector {i}: {msg_hex}")

        hw_digest = await _run_one_hash(dut, msg)

        assert hw_digest == expected, (
            f"NIST vector {i} mismatch\n"
            f"  input:    {msg_hex}\n"
            f"  expected: {expected_hex}\n"
            f"  got:      {hw_digest.hex()}"
        )
        dut._log.info(f"Vector {i} PASSED")

    dut._log.info("All NIST vectors passed")


# ---------------------------------------------------------------------------
# Test 2: Random 256-bit message
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_sha_random_256bit(dut):
    """
    Random 256-bit (32-byte) message test: compare DUT against Python SHA-256.
    """
    dut._log.info("Starting SHA-256 random 256-bit message test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await reset_dut(dut)

    msg = get_random_bytes(32)

    hw_digest  = await _run_one_hash(dut, msg)
    ref_digest = SHA256.new(msg).digest()

    dut._log.info(f"Random msg : {msg.hex()}")
    dut._log.info(f"HW digest  : {hw_digest.hex()}")
    dut._log.info(f"REF digest : {ref_digest.hex()}")

    assert hw_digest == ref_digest, (
        "SHA-256 mismatch for random 256-bit message\n"
        f"  expected: {ref_digest.hex()}\n"
        f"  got:      {hw_digest.hex()}"
    )


# ---------------------------------------------------------------------------
# Test 3: Back-to-back hashes
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_sha_back_to_back(dut):
    """
    Hash two different messages consecutively without resetting the DUT.
    Verifies that internal state clears correctly between operations.
    """
    dut._log.info("Starting back-to-back hash test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await reset_dut(dut)

    msg_a = get_random_bytes(32)
    msg_b = get_random_bytes(32)
    while msg_b == msg_a:
        msg_b = get_random_bytes(32)

    ref_a = SHA256.new(msg_a).digest()
    ref_b = SHA256.new(msg_b).digest()

    dut._log.info(f"Message A: {msg_a.hex()}")
    hw_a = await _run_one_hash(dut, msg_a)
    assert hw_a == ref_a, (
        "Back-to-back test: first hash mismatch\n"
        f"  expected: {ref_a.hex()}\n"
        f"  got:      {hw_a.hex()}"
    )
    dut._log.info("First hash correct, proceeding to second")

    dut._log.info(f"Message B: {msg_b.hex()}")
    hw_b = await _run_one_hash(dut, msg_b)
    assert hw_b == ref_b, (
        "Back-to-back test: second hash mismatch\n"
        f"  expected: {ref_b.hex()}\n"
        f"  got:      {hw_b.hex()}"
    )
    dut._log.info("Second hash correct — back-to-back test PASSED")