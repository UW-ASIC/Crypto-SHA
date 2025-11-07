import cocotb, json
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.types import Range
from cocotb.types import LogicArray

from gen_test_cases import generate_test_cases

def to_int(list):
    for i in range(len(list)):
        list[i] = int(list[i], 16)

    return list

def to_logic_array(list):
    bits = []
    for num in list:
        num_logic = LogicArray(num, Range(31, "downto", 0))
        bits.extend(num_logic)
    
    return LogicArray(bits, Range(511, "downto", 0))

async def reset_msg_schedule(dut):
    dut.rst_n.value = 0
    dut.init.value = 0
    dut.shift.value = 0
    dut.t.value = 0
    dut.block.value = 0
    await ClockCycles(dut.clk, 2)

    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

async def test_msg_schedule_case(dut, input, expected):
    dut.block.value = to_logic_array(input)
    dut.init.value = 1
    dut.shift.value = 0

    await ClockCycles(dut.clk, 1)

    for i in range(64):
        dut.t.value = i

        await ClockCycles(dut.clk, 1)

        if i == 16:
            dut.shift.value = 1
            dut.init.value = 0
            
            await ClockCycles(dut.clk, 1)

        # Don't sample data until `valid` is asserted
        while dut.valid.value == 0:
            await ClockCycles(dut.clk, 1)
        
        assert dut.W_t.value == expected[i], \
            f"Incorrect at t == {i}. Expected W_t == {LogicArray(expected[i], Range(31, "downto", 0))}, received {dut.W_t.value}"

@cocotb.test()
async def test_msg_schedule(dut):
    dut._log.info("Generating test cases")
    generate_test_cases()

    dut._log.info("Starting message schedule test")

    # Set clock to 10 MHz
    clock = Clock(dut.clk, 100, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_msg_schedule(dut)

    num_test_cases = 10

    for i in range(num_test_cases):
        with open(f"test_cases/test_case_{i + 1}.json", 'r') as file:
            test_case = json.load(file)
        
        dut._log.info(f"Running test_case_{i + 1}")

        input = to_int(test_case["input"])
        expected = to_int(test_case["expected"])

        await test_msg_schedule_case(dut, input, expected)