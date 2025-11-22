import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

# Match RTL
OP_LOAD_TEXT    = 1  # 2'b01
OP_WRITE_RESULT = 2  # 2'b10
OP_HASH         = 3  # 2'b11

MEM_ID = 0  # 2'b00
SHA_ID = 1  # 2'b01


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
    sha.ack_ready.value  = 1  # always ready to accept acks

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


async def start_hash(dut):
    """
    Issue OP_HASH to start hashing the loaded 32-byte message.
    Must happen while msg_valid from msg_buffer is high.
    """
    sha = dut

    sha._log.info("Issuing OP_HASH")

    sha.opcode.value    = OP_HASH
    sha.source_id.value = MEM_ID
    sha.dest_id.value   = SHA_ID

    # Hold OP_HASH for a couple of cycles so IDLE can see it
    await ClockCycles(sha.clk, 2)

    # Optionally clear back to idle
    sha.opcode.value    = 0
    sha.source_id.value = 0
    sha.dest_id.value   = 0

    # Wait some cycles to allow HASH_OP to run and digest_ready to be set
    await ClockCycles(sha.clk, 200)


async def read_digest(dut, num_bytes=32) -> bytes:
    """
    Request the digest with OP_WRITE_RESULT and read `num_bytes` using
    data_valid/data_ready handshake.
    """
    sha = dut
    digest = bytearray()

    sha._log.info("Requesting digest via OP_WRITE_RESULT")

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

    # After TX_RES, DUT enters ACK_HOLD and asserts ack_valid
    for _ in range(50):
        await RisingEdge(sha.clk)
        if int(sha.ack_valid.value) == 1:
            sha._log.info(
                f"Got ack_valid, module_source_id={int(sha.module_source_id.value)}"
            )
            break

    # Optionally clear bus
    sha.opcode.value    = 0
    sha.source_id.value = 0
    sha.dest_id.value   = 0

    return bytes(digest)


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

    # Exactly 256 bits = 32 bytes
    msg = get_random_bytes(32)
    msg_len = len(msg)
    assert msg_len == 32

    # 1) Load message
    await load_message_32(dut, msg)

    # 2) Start hashing
    await start_hash(dut)

    # 3) Request and read digest
    hw_digest = await read_digest(dut, num_bytes=32)

    # Reference digest
    ref_digest = SHA256.new(msg).digest()

    dut._log.info(f"Random msg ({msg_len} bytes): {msg.hex()}")
    dut._log.info(f"HW digest : {hw_digest.hex()}")
    dut._log.info(f"REF digest: {ref_digest.hex()}")

    assert hw_digest == ref_digest, (
        "SHA-256 mismatch for random 256-bit message\n"
        f"  len:      {msg_len}\n"
        f"  expected: {ref_digest.hex()}\n"
        f"  got:      {hw_digest.hex()}"
    )
