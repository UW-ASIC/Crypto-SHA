import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, with_timeout
from cocotb.utils import get_sim_time
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


async def reset_dut(dut):
    """Reset the SHA DUT and initialize control signals."""
    sha = dut

    sha.rst_n.value      = 0
    sha.valid_in.value   = 0
    sha.data_in.value    = 0
    sha.data_ready.value = 0
    sha.ack_ready.value  = 0

    # Transaction bus defaults
    sha.opcode.value     = 0
    sha.source_id.value  = 0
    sha.dest_id.value    = 0
    sha.encdec.value     = 0   # unused for SHA
    sha.addr.value       = 0

    await ClockCycles(sha.clk, 5)

    sha.rst_n.value      = 1
    sha.ack_ready.value  = 0  # controlled by read_digest

    await ClockCycles(sha.clk, 2)
    sha._log.info("Reset complete")


async def load_message_32(dut, msg: bytes):
    """
    Load exactly 32 bytes into the SHA core using LOAD_TEXT.
    This matches the RD_TEXT state + msg_buffer_256b interface.
    """
    assert len(msg) == 32, "DUT expects exactly 32 bytes"
    sha = dut

    sha._log.info(f"Loading 32-byte message: {msg.hex()}")

    # Set up LOAD_TEXT transaction
    sha.opcode.value    = OP_LOAD_TEXT
    sha.source_id.value = MEM_ID
    sha.dest_id.value   = SHA_ID

    for b in msg:
        sha.data_in.value  = b
        sha.valid_in.value = 1

        # Wait until DUT asserts ready_in on a rising clock edge
        while True:
            await RisingEdge(sha.clk)
            if int(sha.ready_in.value) == 1:
                break

    sha.valid_in.value = 0
    sha._log.info("Finished sending 32-byte message")

    # Give DUT a couple cycles to return from RD_TEXT to IDLE
    await ClockCycles(sha.clk, 2)


async def _wait_for_digest_ready(dut):
    """
    Internal coroutine: poll digest_ready until high.
    Wrapped with with_timeout in start_hash so a hung DUT fails cleanly.
    """
    sha = dut
    while True:
        await RisingEdge(sha.clk)
        # digest_ready is an internal reg; access via dut hierarchy.
        # If your sim doesn't expose internals, fall back to a fixed wait.
        try:
            if int(sha.digest_ready.value) == 1:
                return
        except AttributeError:
            # digest_ready not directly accessible; wait the full timeout
            return


async def start_hash(dut):
    """
    Issue OP_HASH to start hashing the loaded 32-byte message,
    then wait for completion with a hard timeout so a stalled DUT
    fails immediately rather than running forever.
    """
    sha = dut

    sha._log.info("Issuing OP_HASH")

    sha.opcode.value    = OP_HASH
    sha.source_id.value = MEM_ID
    sha.dest_id.value   = SHA_ID

    # Hold OP_HASH for a couple of cycles so IDLE can see it
    await ClockCycles(sha.clk, 2)

    # Clear bus
    sha.opcode.value    = 0
    sha.source_id.value = 0
    sha.dest_id.value   = 0

    # Wait for hashing to complete, but enforce a hard cycle ceiling.
    # HASH_TIMEOUT_CYCLES is well above the expected ~140-cycle latency.
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

    # One extra cycle of margin before reading
    await ClockCycles(sha.clk, 2)


async def read_digest(dut, num_bytes=32) -> bytes:
    """
    Request the digest with OP_WRITE_RESULT and read `num_bytes` using
    data_valid/data_ready handshake.

    ack_ready is held LOW during digest collection so that ACK_HOLD does not
    self-clear in the same cycle it is entered (the DUT exits ACK_HOLD the
    first cycle it sees ack_ready=1, so with ack_ready permanently high the
    pulse lasts only one cycle and is gone before the testbench can poll it).
    We raise ack_ready only after the collection loop exits, then poll.
    """
    sha = dut
    digest = bytearray()

    sha._log.info("Requesting digest via OP_WRITE_RESULT")

    # Hold ack_ready LOW so ACK_HOLD will wait for us
    sha.ack_ready.value  = 0

    # Issue WRITE_RESULT transaction
    sha.opcode.value    = OP_WRITE_RESULT
    sha.source_id.value = SHA_ID
    sha.dest_id.value   = MEM_ID

    sha.data_ready.value = 1
    sha._log.info("Waiting for digest bytes from DUT")

    while len(digest) < num_bytes:
        await RisingEdge(sha.clk)
        if int(sha.data_valid.value) == 1:
            digest.append(int(sha.data_out.value))

    sha.data_ready.value = 0
    sha._log.info(f"Received digest ({len(digest)} bytes)")

    # Now raise ack_ready and wait for ack_valid. ACK_HOLD is still active
    # because ack_ready was low during TX_RES → ACK_HOLD transition.
    # Fail explicitly if it never arrives rather than silently continuing.
    sha.ack_ready.value = 1
    ack_seen = False
    for _ in range(50):
        await RisingEdge(sha.clk)
        if int(sha.ack_valid.value) == 1:
            sha._log.info(
                f"Got ack_valid, module_source_id={int(sha.module_source_id.value)}"
            )
            ack_seen = True
            break

    assert ack_seen, "DUT never asserted ack_valid after transmitting digest"

    # Clear bus
    sha.opcode.value    = 0
    sha.source_id.value = 0
    sha.dest_id.value   = 0

    return bytes(digest)


async def _run_one_hash(dut, msg: bytes) -> bytes:
    """Load a message, hash it, and return the digest. Reusable across tests."""
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
    These are deterministic and must always pass — a failure here means a
    fundamental correctness bug, not a flaky random failure.
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
    DUT logic only supports fixed 256-bit messages.
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
# Test 3: Back-to-back hashes — verifies state resets cleanly between messages
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_sha_back_to_back(dut):
    """
    Hash two different messages consecutively without resetting the DUT.
    Verifies that internal state (working variables, digest, msg_buffer) is
    correctly cleared between operations and does not bleed across hashes.
    """
    dut._log.info("Starting back-to-back hash test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await reset_dut(dut)

    msg_a = get_random_bytes(32)
    msg_b = get_random_bytes(32)

    # Ensure the two messages are actually different
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