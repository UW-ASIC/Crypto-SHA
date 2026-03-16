import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, with_timeout
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

# -----------------------------------------------------------------------
# Opcodes (match RTL)
# -----------------------------------------------------------------------
OP_NOP          = 0  # 2'b00
OP_LOAD_TEXT    = 1  # 2'b01
OP_WRITE_RESULT = 2  # 2'b10
OP_HASH         = 3  # 2'b11

# SHA-256 takes 64 rounds x ~3 cycles + overhead; 300 cycles is safe.
HASH_TIMEOUT_CYCLES = 300

# -----------------------------------------------------------------------
# NIST FIPS 180-4 known-answer test vectors for exactly 32-byte messages.
# Each entry: (plaintext_hex, expected_digest_hex)
# -----------------------------------------------------------------------
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


# -----------------------------------------------------------------------
# TT pin-level driver
# -----------------------------------------------------------------------
#
#  ui_in[7:0]   -> data_in
#  uio_in[0]    -> valid_in
#  uio_in[1]    -> data_ready
#  uio_in[2]    -> ack_ready
#  uio_in[3]    -> opcode[0]
#  uio_in[4]    -> opcode[1]
#  uio_in[7:5]  -> unused (0)
#
#  uo_out[7:0]  <- data_out
#  uio_out[5]   <- ready_in
#  uio_out[6]   <- data_valid
#  uio_out[7]   <- ack_valid
# -----------------------------------------------------------------------

class TTDriver:
    """Thin wrapper that maps logical SHA signals to TT physical pins."""

    def __init__(self, dut):
        self.dut = dut
        self._uio = 0          # shadow register for uio_in

    # ---- helpers for uio_in bit-fields ----
    def _flush_uio(self):
        self.dut.uio_in.value = self._uio

    def set_valid_in(self, v):
        self._uio = (self._uio & ~0x01) | (int(v) & 1)
        self._flush_uio()

    def set_data_ready(self, v):
        self._uio = (self._uio & ~0x02) | ((int(v) & 1) << 1)
        self._flush_uio()

    def set_ack_ready(self, v):
        self._uio = (self._uio & ~0x04) | ((int(v) & 1) << 2)
        self._flush_uio()

    def set_opcode(self, op):
        self._uio = (self._uio & ~0x18) | ((int(op) & 3) << 3)
        self._flush_uio()

    def set_data_in(self, v):
        self.dut.ui_in.value = int(v) & 0xFF

    # ---- output readers ----
    def get_data_out(self):
        return int(self.dut.uo_out.value) & 0xFF

    def get_ready_in(self):
        return (int(self.dut.uio_out.value) >> 5) & 1

    def get_data_valid(self):
        return (int(self.dut.uio_out.value) >> 6) & 1

    def get_ack_valid(self):
        return (int(self.dut.uio_out.value) >> 7) & 1

    # ---- bulk set / clear ----
    def clear_all(self):
        """Drive all inputs low."""
        self.dut.ui_in.value = 0
        self._uio = 0
        self._flush_uio()


# -----------------------------------------------------------------------
# Testbench helpers
# -----------------------------------------------------------------------

async def reset_dut(dut, drv):
    """Reset the DUT and initialise all TT input pins to 0."""
    drv.clear_all()
    dut.ena.value = 1

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)

    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    dut._log.info("Reset complete")


async def load_message_32(dut, drv, msg: bytes):
    """Load exactly 32 bytes into the SHA core via LOAD_TEXT."""
    assert len(msg) == 32, "DUT expects exactly 32 bytes"

    dut._log.info(f"Loading 32-byte message: {msg.hex()}")

    drv.set_opcode(OP_LOAD_TEXT)

    for b in msg:
        drv.set_data_in(b)
        drv.set_valid_in(1)

        # Wait until DUT asserts ready_in
        while True:
            await RisingEdge(dut.clk)
            if drv.get_ready_in():
                break

    drv.set_valid_in(0)
    drv.set_opcode(OP_NOP)
    dut._log.info("Finished sending 32-byte message")

    # Give DUT a couple cycles to return to IDLE
    await ClockCycles(dut.clk, 2)


async def start_hash(dut, drv):
    """Issue OP_HASH and wait for completion."""
    dut._log.info("Issuing OP_HASH")

    drv.set_opcode(OP_HASH)
    await ClockCycles(dut.clk, 2)

    drv.set_opcode(OP_NOP)

    # Wait for hash to complete.  SHA-256 = 64 rounds × ~3 cycles + overhead
    # ≈ 200 cycles.  300 is a safe ceiling.  In RTL we could poll
    # digest_ready, but in GL that internal signal is not accessible,
    # so a fixed wait is the most portable approach.
    dut._log.info(f"Waiting for hash (fixed wait = {HASH_TIMEOUT_CYCLES} cycles)")
    await ClockCycles(dut.clk, HASH_TIMEOUT_CYCLES)
    dut._log.info("Hash wait complete")


async def read_digest(dut, drv, num_bytes=32) -> bytes:
    """
    Request the digest via OP_WRITE_RESULT and clock out ``num_bytes``
    using the data_valid / data_ready handshake.
    """
    digest = bytearray()

    dut._log.info("Requesting digest via OP_WRITE_RESULT")

    # Hold ack_ready LOW so ACK_HOLD waits for us
    drv.set_ack_ready(0)

    # Issue WRITE_RESULT
    drv.set_opcode(OP_WRITE_RESULT)
    drv.set_data_ready(1)

    dut._log.info("Waiting for digest bytes from DUT")

    timeout = 2000  # generous cycle ceiling
    cycles = 0
    while len(digest) < num_bytes and cycles < timeout:
        await RisingEdge(dut.clk)
        cycles += 1
        if drv.get_data_valid():
            digest.append(drv.get_data_out())

    drv.set_data_ready(0)
    assert len(digest) == num_bytes, (
        f"Only received {len(digest)}/{num_bytes} digest bytes "
        f"within {timeout} cycles"
    )
    dut._log.info(f"Received digest ({len(digest)} bytes)")

    # Now raise ack_ready and wait for ack_valid
    drv.set_ack_ready(1)
    ack_seen = False
    for _ in range(50):
        await RisingEdge(dut.clk)
        if drv.get_ack_valid():
            dut._log.info("Got ack_valid")
            ack_seen = True
            break

    assert ack_seen, "DUT never asserted ack_valid after transmitting digest"

    # Clear bus
    drv.set_opcode(OP_NOP)
    drv.set_ack_ready(0)

    return bytes(digest)


async def _run_one_hash(dut, drv, msg: bytes) -> bytes:
    """Load a message, hash it, and return the digest."""
    await load_message_32(dut, drv, msg)
    await start_hash(dut, drv)
    return await read_digest(dut, drv, num_bytes=32)


# -----------------------------------------------------------------------
# Test 1: Fixed NIST known-answer vectors
# -----------------------------------------------------------------------
@cocotb.test()
async def test_sha_nist_vectors(dut):
    """
    Known-answer tests using fixed NIST-style vectors for 32-byte messages.
    """
    dut._log.info("Starting NIST known-answer vector tests")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    drv = TTDriver(dut)

    await ClockCycles(dut.clk, 5)
    await reset_dut(dut, drv)

    for i, (msg_hex, expected_hex) in enumerate(NIST_VECTORS):
        msg      = bytes.fromhex(msg_hex)
        expected = bytes.fromhex(expected_hex)

        dut._log.info(f"Vector {i}: {msg_hex}")

        hw_digest = await _run_one_hash(dut, drv, msg)

        assert hw_digest == expected, (
            f"NIST vector {i} mismatch\n"
            f"  input:    {msg_hex}\n"
            f"  expected: {expected_hex}\n"
            f"  got:      {hw_digest.hex()}"
        )
        dut._log.info(f"Vector {i} PASSED")

    dut._log.info("All NIST vectors passed")


# -----------------------------------------------------------------------
# Test 2: Random 256-bit message
# -----------------------------------------------------------------------
@cocotb.test()
async def test_sha_random_256bit(dut):
    """
    Random 256-bit (32-byte) message test: compare DUT against Python SHA-256.
    """
    dut._log.info("Starting SHA-256 random 256-bit message test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    drv = TTDriver(dut)

    await ClockCycles(dut.clk, 5)
    await reset_dut(dut, drv)

    msg = get_random_bytes(32)

    hw_digest  = await _run_one_hash(dut, drv, msg)
    ref_digest = SHA256.new(msg).digest()

    dut._log.info(f"Random msg : {msg.hex()}")
    dut._log.info(f"HW digest  : {hw_digest.hex()}")
    dut._log.info(f"REF digest : {ref_digest.hex()}")

    assert hw_digest == ref_digest, (
        "SHA-256 mismatch for random 256-bit message\n"
        f"  expected: {ref_digest.hex()}\n"
        f"  got:      {hw_digest.hex()}"
    )


# -----------------------------------------------------------------------
# Test 3: Back-to-back hashes
# -----------------------------------------------------------------------
@cocotb.test()
async def test_sha_back_to_back(dut):
    """
    Hash two different messages consecutively without resetting the DUT.
    """
    dut._log.info("Starting back-to-back hash test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    drv = TTDriver(dut)

    await ClockCycles(dut.clk, 5)
    await reset_dut(dut, drv)

    msg_a = get_random_bytes(32)
    msg_b = get_random_bytes(32)
    while msg_b == msg_a:
        msg_b = get_random_bytes(32)

    ref_a = SHA256.new(msg_a).digest()
    ref_b = SHA256.new(msg_b).digest()

    dut._log.info(f"Message A: {msg_a.hex()}")
    hw_a = await _run_one_hash(dut, drv, msg_a)
    assert hw_a == ref_a, (
        "Back-to-back test: first hash mismatch\n"
        f"  expected: {ref_a.hex()}\n"
        f"  got:      {hw_a.hex()}"
    )
    dut._log.info("First hash correct, proceeding to second")

    dut._log.info(f"Message B: {msg_b.hex()}")
    hw_b = await _run_one_hash(dut, drv, msg_b)
    assert hw_b == ref_b, (
        "Back-to-back test: second hash mismatch\n"
        f"  expected: {ref_b.hex()}\n"
        f"  got:      {hw_b.hex()}"
    )
    dut._log.info("Second hash correct — back-to-back test PASSED")