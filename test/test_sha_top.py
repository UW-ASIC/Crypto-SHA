import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, with_timeout
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

# Opcodes (match RTL)
OP_NOP          = 0  # 2'b00
OP_LOAD_TEXT    = 1  # 2'b01
OP_WRITE_RESULT = 2  # 2'b10
OP_HASH         = 3  # 2'b11

# SHA-256 takes 64 rounds x ~2 cycles + overhead; 300 cycles is a safe ceiling.
HASH_TIMEOUT_CYCLES = 300

# NIST FIPS 180-4 known-answer test vectors for exactly 32-byte messages.
NIST_VECTORS = [
    (
        "00" * 32,
        "66687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925",
    ),
    (
        "ff" * 32,
        "af9613760f72635fbdb44a5a0a63c39f12af30f950a6ee5c971be188e89c4051",
    ),
    (
        "6162636465666768696a6b6c6d6e6f707172737475767778797a414243444546",
        "cfd2f1fad75a1978da0a444883db7251414b139f31f5a04704c291fdb0e175e6",
    ),
]

# ---------------------------------------------------------------------------
# Pin helpers
# Pin mapping (from project.v):
#   ui_in[7:0]  -> data_in
#   uio_in[0]   -> valid_in
#   uio_in[1]   -> data_ready
#   uio_in[2]   -> ack_ready
#   uio_in[4:3] -> opcode[1:0]
#   uo_out[7:0] <- data_out
#   uio_out[5]  <- ready_in
#   uio_out[6]  <- data_valid
#   uio_out[7]  <- ack_valid
# ---------------------------------------------------------------------------

def _set_inputs(dut, data_in=0, valid_in=0, data_ready=0,
                ack_ready=0, opcode=0):
    dut.ui_in.value  = data_in & 0xFF
    uio = (valid_in  & 1)       | \
          ((data_ready & 1) << 1) | \
          ((ack_ready  & 1) << 2) | \
          ((opcode     & 3) << 3)
    dut.uio_in.value = uio

def _get_ready_in(dut):
    return (int(dut.uio_out.value) >> 5) & 1

def _get_data_valid(dut):
    return (int(dut.uio_out.value) >> 6) & 1

def _get_ack_valid(dut):
    return (int(dut.uio_out.value) >> 7) & 1

def _get_data_out(dut):
    return int(dut.uo_out.value) & 0xFF


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.ena.value   = 1
    _set_inputs(dut)
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    dut._log.info("Reset complete")


async def load_message_32(dut, msg: bytes):
    assert len(msg) == 32, "DUT expects exactly 32 bytes"
    dut._log.info(f"Loading 32-byte message: {msg.hex()}")

    for b in msg:
        _set_inputs(dut, data_in=b, valid_in=1, opcode=OP_LOAD_TEXT)
        while True:
            await RisingEdge(dut.clk)
            if _get_ready_in(dut):
                break

    _set_inputs(dut)
    dut._log.info("Finished sending 32-byte message")
    await ClockCycles(dut.clk, 2)


async def start_hash(dut):
    dut._log.info("Issuing OP_HASH")
    _set_inputs(dut, opcode=OP_HASH)
    await ClockCycles(dut.clk, 2)
    _set_inputs(dut)

    dut._log.info(f"Waiting for hash (timeout = {HASH_TIMEOUT_CYCLES} cycles)")
    await ClockCycles(dut.clk, HASH_TIMEOUT_CYCLES)
    dut._log.info("Hash wait complete")


async def read_digest(dut, num_bytes=32) -> bytes:
    digest = bytearray()
    dut._log.info("Requesting digest via OP_WRITE_RESULT")

    # Hold ack_ready LOW so ACK_HOLD doesn't self-clear before we can observe it
    _set_inputs(dut, data_ready=1, ack_ready=0, opcode=OP_WRITE_RESULT)

    dut._log.info("Waiting for digest bytes from DUT")
    timeout = 2000
    cycles  = 0
    while len(digest) < num_bytes and cycles < timeout:
        await RisingEdge(dut.clk)
        cycles += 1
        if _get_data_valid(dut):
            digest.append(_get_data_out(dut))

    _set_inputs(dut, ack_ready=0)
    assert len(digest) == num_bytes, \
        f"Only received {len(digest)}/{num_bytes} bytes within {timeout} cycles"
    dut._log.info(f"Received digest ({len(digest)} bytes)")

    # Now raise ack_ready so the DUT can exit ACK_HOLD
    _set_inputs(dut, ack_ready=1)
    ack_seen = False
    for _ in range(50):
        await RisingEdge(dut.clk)
        if _get_ack_valid(dut):
            dut._log.info("Got ack_valid")
            ack_seen = True
            break

    assert ack_seen, "DUT never asserted ack_valid after transmitting digest"
    _set_inputs(dut)
    return bytes(digest)


async def _run_one_hash(dut, msg: bytes) -> bytes:
    await load_message_32(dut, msg)
    await start_hash(dut)
    return await read_digest(dut)


# ---------------------------------------------------------------------------
# Test 1: NIST known-answer vectors
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_sha_nist_vectors(dut):
    """Known-answer tests using fixed NIST-style vectors for 32-byte messages."""
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
    """Random 256-bit (32-byte) message test: compare DUT against Python SHA-256."""
    dut._log.info("Starting SHA-256 random 256-bit message test")
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    await ClockCycles(dut.clk, 5)
    await reset_dut(dut)

    msg        = get_random_bytes(32)
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
    """Hash two different messages consecutively without resetting the DUT."""
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