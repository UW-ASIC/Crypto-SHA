import cocotb
import random
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.triggers import RisingEdge
from cocotb.triggers import Timer, First
from cocotb.types import Logic
from cocotb.types import LogicArray
from cocotb.types import Range


async def send_message(dut, msg): # msg is a binary string
    
    msg_size = 0
    data = [] # data[0] is blk1 data, data[1] is blk2 data (if it exists)
    dut.in_last.value = 0
    dut.in_valid.value = 0
    dut.blk_ready.value = 0
    msg_size = int(len(msg)/8)

    # await for in_ready before transmitting data
    while not dut.in_ready.value:
        await RisingEdge(dut.clk)

    # feed in data bytes every clock edge
    for i in range(msg_size):

        dut.in_valid.value = 1

        await RisingEdge(dut.clk)
        dut.in_data.value = LogicArray(msg[8*i:8*i+8])

        if i == msg_size - 1:
            dut.in_last.value = 1
    
    # edge case for empty messages
    if msg_size == 0:
        dut.in_last.value = 1
        
    await RisingEdge(dut.clk)
    dut.blk_ready.value = 1

    # wait until device is ready to accept blocks
    while not dut.blk_valid.value:
        await RisingEdge(dut.clk)

    dut.in_valid.value = 0
    dut.in_last.value = 0

    data.append(dut.blk_data.value) # read in first block
    await RisingEdge(dut.clk)
    if dut.blk_valid.value == Logic(1): # read in second block if remaining data not empty
        data.append(dut.blk_data.value)

    return data

def reference_padder(msg):

    padded_msg = msg+"10000000"
    padded_msg_array = []
    
    while len(padded_msg) % 512 != 448:
        padded_msg += "0"*8
        
    
    padded_msg += format(len(msg), "064b")

    if len(padded_msg) == 512:
        padded_msg_array.append(int(padded_msg[0:512],2))

    else:
        padded_msg_array = [int(padded_msg[0:512],2), int(padded_msg[512:1024],2)]
    
    return padded_msg_array
    
def randomize_message(length = 0):

    if length == 0:
        rand_length = random.choice(range(0, 953, 8))
    else:
        rand_length = length
    return ''.join(random.choice("01") for _ in range(rand_length))
    
    

@cocotb.test()
async def test_padder_edge_cases(dut):
    dut._log.info("Starting edge case tests for padder") # Log the start of the test
    
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())  # Start the clock
    
    dut.rst_n.value = 0
    dut.in_last.value = 0
    dut.in_valid.value = 0
    dut.in_data.value = 0
    dut.in_last.value = 0
    dut.blk_ready.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    ''' FUNCTIONAL REQUIREMENTS

    1) If bitlen = 0, blk_data = 1 << 511
    2) If 0 < bitlen <= 440, last 64 bits of first/only block are msglen
    3) If 448 <= bitlen <= 952, last 64 bits of second block are msglen
    4) 0 < bitlen <= 952
    5) No data is processed until in_ready = 1
    6) in_valid signals empty messages
    7) blk_valid = 0 after all blocks are transmitted
    
    '''

    dut._log.info("Edge Cases")

    dut._log.info("0 bit length message before messages have been padded") 
    msg = ""
    data = await send_message(dut, msg)
    assert int(data[0]) == reference_padder(msg)[0], print(f"Expected (1 << 511), got {int(data[0])}")
    
    dut._log.info("440 bit length integer message")
    msg = "1011"*55 + "11"*110
    data = await send_message(dut, msg)
    assert int(data[0]) == reference_padder(msg)[0], print(f"Expected (441 1s, 7 0s, and 64 bit rep of 440), got {int(data[0])}")
    
    dut._log.info("448 bit length integer message")
    msg = "1"*448
    data = await send_message(dut, msg)
    assert int(data[0]) == reference_padder(msg)[0], print(f"Expected (449 1s, 63 0s), got {int(data[0])}")
    assert int(data[1]) == reference_padder(msg)[1], print(f"Expected (448 0s, 64 bit rep of 448), got {int[data[1]]}")
    
    dut._log.info("512 bit length integer message")
    msg = "1"*512
    data = await send_message(dut, msg)
    assert int(data[0]) == reference_padder(msg)[0], print(f"Expected (512 1s), got {int(data[0])}")
    assert int(data[1]) == reference_padder(msg)[1], print(f"Expected (1 1, 447 0s, 64 bit rep of 512), got {int[data[1]]}")

    dut._log.info("952 bit length integer message")
    msg = "1"*952
    data = await send_message(dut, msg)
    assert int(data[0]) == reference_padder(msg)[0], print(f"Expected (512 1s), got {int(data[0])}")
    assert int(data[1]) == reference_padder(msg)[1], print(f"Expected (441 1s, 7 0s, and 64 bit rep of 952), got {int(data[0])}")

    dut._log.info("0 bit length message after all messages have been padded") 
    msg = ""
    data = await send_message(dut, msg)
    assert int(data[0]) == reference_padder(msg)[0], print(f"Expected (1 << 511), got {int(data[0])}")

    dut._log.info("Edge case tests finished!")

@cocotb.test()
async def test_padder_random(dut):

    dut._log.info("Starting edge case tests for padder") # Log the start of the test
    
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())  # Start the clock
    
    dut.rst_n.value = 0
    dut.in_last.value = 0
    dut.in_valid.value = 0
    dut.in_data.value = 0
    dut.in_last.value = 0
    dut.blk_ready.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    dut._log.info("Randomized Tests")

    for i in range(20):
        msg = randomize_message(440)
        data = await send_message(dut, msg)
        assert int(data[0]) == reference_padder(msg)[0], print(f"Expected {reference_padder(msg)[0]}, got {int(data[0])}")
        if len(data) == 2:
            assert int(data[1]) == reference_padder(msg)[1], print(f"Expected {reference_padder(msg)[1]}, got {int(data[1])}")

    for i in range(20):
        msg = randomize_message(448)
        data = await send_message(dut, msg)
        assert int(data[0]) == reference_padder(msg)[0], print(f"Expected {reference_padder(msg)[0]}, got {int(data[0])}")
        if len(data) == 2:
            assert int(data[1]) == reference_padder(msg)[1], print(f"Expected {reference_padder(msg)[1]}, got {int(data[1])}")

    for i in range(20):
        msg = randomize_message(512)
        data = await send_message(dut, msg)
        assert int(data[0]) == reference_padder(msg)[0], print(f"Expected {reference_padder(msg)[0]}, got {int(data[0])}")
        if len(data) == 2:
            assert int(data[1]) == reference_padder(msg)[1], print(f"Expected {reference_padder(msg)[1]}, got {int(data[1])}")

    for i in range(20):
        msg = randomize_message(952)
        data = await send_message(dut, msg)
        assert int(data[0]) == reference_padder(msg)[0], print(f"Expected {reference_padder(msg)[0]}, got {int(data[0])}")
        if len(data) == 2:
            assert int(data[1]) == reference_padder(msg)[1], print(f"Expected {reference_padder(msg)[1]}, got {int(data[1])}")

    for i in range(20):
        msg = randomize_message()
        data = await send_message(dut, msg)
        assert int(data[0]) == reference_padder(msg)[0], print(f"Expected {reference_padder(msg)[0]}, got {int(data[0])}")
        if len(data) == 2:
            assert int(data[1]) == reference_padder(msg)[1], print(f"Expected {reference_padder(msg)[1]}, got {int(data[1])}")
    
    dut._log.info("Randomized tests finished!")