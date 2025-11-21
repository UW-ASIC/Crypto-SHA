import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes


async def reset_dut(dut):
    """Reset the SHA DUT and initialize control signals."""

    # If sha is instantiated inside a top as sha_inst, change to: sha = dut.sha_inst
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
    sha.rst_n.value = 1
    sha.ack_ready.value = 1  # always ready to accept acks
    await ClockCycles(sha.clk, 2)
    sha._log.info("Reset complete")


async def send_message(dut, msg: bytes):
    """
    Stream a message into the SHA core, byte by byte, using valid_in/ready_in.
    """
    sha = dut

    sha._log.info(f"Sending message ({len(msg)} bytes): {msg.hex()}")

    for b in msg:
        sha.data_in.value = b
        sha.valid_in.value = 1

        # Wait until DUT asserts ready_in on a rising clock edge
        while True:
            await RisingEdge(sha.clk)
            if sha.ready_in.value == 1:
                break

    sha.valid_in.value = 0
    sha._log.info("Finished sending message")


async def read_digest(dut, num_bytes=32) -> bytes:
    """
    Read the SHA-256 digest (32 bytes) from the DUT using data_valid/data_ready.
    """
    sha = dut
    digest = bytearray()

    sha.data_ready.value = 1
    sha._log.info("Waiting for digest bytes from DUT")

    while len(digest) < num_bytes:
        await RisingEdge(sha.clk)
        if sha.data_valid.value == 1:
            digest.append(int(sha.data_out.value))

    sha.data_ready.value = 0
    sha._log.info(f"Received digest ({len(digest)} bytes)")

    return bytes(digest)


@cocotb.test()
async def test_sha_abc(dut):
    """
    Simple sanity test: SHA-256("abc") vs Python reference.
    """
    dut._log.info("Starting SHA-256 'abc' test")
    
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await reset_dut(dut)

    # Example fixed message
    msg = b"abc"

    # Set up a simple transaction; adapt opcode/source/dest to your protocol
    dut.opcode.value    = 0  # e.g. 0 = "hash" command
    dut.source_id.value = 1
    dut.dest_id.value   = 0
    dut.encdec.value    = 0
    dut.addr.value      = 0

    # Stream message in
    await send_message(dut, msg)

    # Optional: wait for ack_valid (if your protocol uses it to signal "done")
    # This is just a soft wait with a timeout so sim doesn't hang forever.
    for _ in range(5000):
        await RisingEdge(dut.clk)
        if dut.ack_valid.value == 1:
            dut._log.info(
                f"Got ack_valid, module_source_id={int(dut.module_source_id.value)}"
            )
            break

    # Read digest from DUT
    hw_digest = await read_digest(dut, num_bytes=32)

    # Reference digest via Crypto.Hash.SHA256
    ref_digest = SHA256.new(msg).digest()

    dut._log.info(f"HW digest : {hw_digest.hex()}")
    dut._log.info(f"REF digest: {ref_digest.hex()}")

    assert hw_digest == ref_digest, (
        "SHA-256 mismatch for 'abc'\n"
        f"  expected: {ref_digest.hex()}\n"
        f"  got:      {hw_digest.hex()}"
    )


@cocotb.test()
async def test_sha_random_message(dut):
    """
    Random message test: compare DUT against Python SHA-256 for a random length.
    """
    dut._log.info("Starting SHA-256 random message test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await reset_dut(dut)

    # Random message length (not aligned to a block to also test padding)
    msg_len = 1 + (get_random_bytes(1)[0] % 100)  # 1..100 bytes
    msg = get_random_bytes(msg_len)

    dut.opcode.value    = 0
    dut.source_id.value = 2
    dut.dest_id.value   = 0
    dut.encdec.value    = 0
    dut.addr.value      = 0

    await send_message(dut, msg)

    # Wait for ack_valid (optional)
    for _ in range(10000):
        await RisingEdge(dut.clk)
        if dut.ack_valid.value == 1:
            dut._log.info(
                f"Got ack_valid, module_source_id={int(dut.module_source_id.value)}"
            )
            break

    hw_digest = await read_digest(dut, num_bytes=32)
    ref_digest = SHA256.new(msg).digest()

    dut._log.info(f"Random msg ({msg_len} bytes): {msg.hex()}")
    dut._log.info(f"HW digest : {hw_digest.hex()}")
    dut._log.info(f"REF digest: {ref_digest.hex()}")

    assert hw_digest == ref_digest, (
        "SHA-256 mismatch for random message\n"
        f"  len:      {msg_len}\n"
        f"  expected: {ref_digest.hex()}\n"
        f"  got:      {hw_digest.hex()}"
    )
