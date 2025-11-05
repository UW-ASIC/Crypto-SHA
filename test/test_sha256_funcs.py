import random
import cocotb
from cocotb.triggers import Timer

# reference model for randomized tests
def sha256_funcs_ref(x,y,z):
    Ch = (x & y) ^ (~x & z)
    Maj = (x & y) ^ (x & z) ^ (y & z)
    Sigma0 = ROTR(x, 2) ^ ROTR(x, 13) ^ ROTR(x, 22)
    Sigma1 = ROTR(x, 6) ^ ROTR(x, 11) ^ ROTR(x, 25)
    sigma0 = ROTR(x, 7) ^ ROTR(x, 18) ^ SHR(x, 3)
    sigma1 = ROTR(y, 17) ^ ROTR(y, 19) ^ SHR(y, 10)
    results = [Ch, Maj, Sigma0 & 0xFFFFFFFF, Sigma1 & 0xFFFFFFFF, sigma0 & 0xFFFFFFFF, sigma1 & 0xFFFFFFFF]
    return results

def ROTR(x, n):
     return (x>>n) | (x<<(32-n))

def SHR(x, n):
     return x>>n
  

@cocotb.test()
async def sha256_funcs(dut):
    dut._log.info("Starting test for SHA256 functions") 

    dut._log.info(f"Edge Cases") 

    # min refers to value 0x00000000 
    # max refers to value 0xFFFFFFFF

    dut._log.info("x,y,z = min,min,min")
    dut.x.value = 0
    dut.y.value = 0
    dut.z.value = 0
    await Timer(1, units='ns')
    assert dut.Ch.value == 0, f"Expected 0, got Ch: 0x{int(dut.Ch.value):08X}"
    assert dut.Maj.value == 0, f"Expected 0, got Maj: 0x{int(dut.Maj.value):08X}"
    assert dut.Sigma0.value == 0, f"Expected 0, got Sigma0: 0x{int(dut.Sigma0.value):08X}"
    assert dut.Sigma1.value == 0, f"Expected 0, got Sigma1: 0x{int(dut.Sigma1.value):08X}"
    assert dut.sigma0.value == 0, f"Expected 0, got sigma0: 0x{int(dut.sigma0.value):08X}"
    assert dut.sigma1.value == 0, f"Expected 0, got sigma1: 0x{int(dut.sigma1.value):08X}"

    dut._log.info("x,y,z = min,min,max")
    dut.x.value = 0
    dut.y.value = 0
    dut.z.value = 0xFFFFFFFF
    await Timer(1, units='ns')
    assert dut.Ch.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Ch: 0x{int(dut.Ch.value):08X}"
    assert dut.Maj.value == 0, f"Expected 0, got Maj: 0x{int(dut.Maj.value):08X}"
    assert dut.Sigma0.value == 0, f"Expected 0, got Sigma0: 0x{int(dut.Sigma0.value):08X}"
    assert dut.Sigma1.value == 0, f"Expected 0, got Sigma1: 0x{int(dut.Sigma1.value):08X}"
    assert dut.sigma0.value == 0, f"Expected 0, got sigma0: 0x{int(dut.sigma0.value):08X}"
    assert dut.sigma1.value == 0, f"Expected 0, got sigma1: 0x{int(dut.sigma1.value):08X}"

    dut._log.info("x,y,z = min,max,min")
    dut.x.value = 0
    dut.y.value = 0xFFFFFFFF
    dut.z.value = 0
    await Timer(1, units='ns')
    assert dut.Ch.value == 0, f"Expected 0, got Ch: 0x{int(dut.Ch.value):08X}"
    assert dut.Maj.value == 0, f"Expected 0, got Maj: 0x{int(dut.Maj.value):08X}"
    assert dut.Sigma0.value == 0, f"Expected 0, got Sigma0: 0x{int(dut.Sigma0.value):08X}"
    assert dut.Sigma1.value == 0, f"Expected 0, got Sigma1: 0x{int(dut.Sigma1.value):08X}"
    assert dut.sigma0.value == 0, f"Expected 0, got sigma0: 0x{int(dut.sigma0.value):08X}"
    assert dut.sigma1.value == 0x003FFFFF, f"Expected 0x003FFFFF, got sigma1: 0x{int(dut.sigma1.value):08X}"

    dut._log.info("x,y,z = min,max,max")
    dut.x.value = 0
    dut.y.value = 0xFFFFFFFF
    dut.z.value = 0xFFFFFFFF
    await Timer(1, units='ns')
    assert dut.Ch.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Ch: 0x{int(dut.Ch.value):08X}"
    assert dut.Maj.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Maj: 0x{int(dut.Maj.value):08X}"
    assert dut.Sigma0.value == 0, f"Expected 0, got Sigma0: 0x{int(dut.Sigma0.value):08X}"
    assert dut.Sigma1.value == 0, f"Expected 0, got Sigma1: 0x{int(dut.Sigma1.value):08X}"
    assert dut.sigma0.value == 0, f"Expected 0, got sigma0: 0x{int(dut.sigma0.value):08X}"
    assert dut.sigma1.value == 0x003FFFFF, f"Expected 0x003FFFFF, got sigma1: 0x{int(dut.sigma1.value):08X}"

    dut._log.info("x,y,z = max,min,min")
    dut.x.value = 0xFFFFFFFF
    dut.y.value = 0
    dut.z.value = 0
    await Timer(1, units='ns')
    assert dut.Ch.value == 0, f"Expected 0, got Ch: 0x{int(dut.Ch.value):08X}"
    assert dut.Maj.value == 0, f"Expected 0, got Maj: 0x{int(dut.Maj.value):08X}"
    assert dut.Sigma0.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Sigma0: 0x{int(dut.Sigma0.value):08X}"
    assert dut.Sigma1.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Sigma1: 0x{int(dut.Sigma1.value):08X}"
    assert dut.sigma0.value == 0x1FFFFFFF, f"Expected 0x1FFFFFFF, got sigma0: 0x{int(dut.sigma0.value):08X}"
    assert dut.sigma1.value == 0, f"Expected 0, got sigma1: 0x{int(dut.sigma1.value):08X}"

    dut._log.info("x,y,z = max,min,max")
    dut.x.value = 0xFFFFFFFF
    dut.y.value = 0
    dut.z.value = 0xFFFFFFFF
    await Timer(1, units='ns')
    assert dut.Ch.value == 0, f"Expected 0, got Ch: 0x{int(dut.Ch.value):08X}"
    assert dut.Maj.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Maj: 0x{int(dut.Maj.value):08X}"
    assert dut.Sigma0.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Sigma0: 0x{int(dut.Sigma0.value):08X}"
    assert dut.Sigma1.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Sigma1: 0x{int(dut.Sigma1.value):08X}"
    assert dut.sigma0.value == 0x1FFFFFFF, f"Expected 0x1FFFFFFF, got sigma0: 0x{int(dut.sigma0.value):08X}"
    assert dut.sigma1.value == 0x0, f"Expected 0, got sigma1: 0x{int(dut.sigma1.value):08X}"

    dut._log.info("x,y,z = max,max,min")
    dut.x.value = 0xFFFFFFFF
    dut.y.value = 0xFFFFFFFF
    dut.z.value = 0
    await Timer(1, units='ns')
    assert dut.Ch.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Ch: 0x{int(dut.Ch.value):08X}"
    assert dut.Maj.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Maj: 0x{int(dut.Maj.value):08X}"
    assert dut.Sigma0.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Sigma0: 0x{int(dut.Sigma0.value):08X}"
    assert dut.Sigma1.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Sigma1: 0x{int(dut.Sigma1.value):08X}"
    assert dut.sigma0.value == 0x1FFFFFFF, f"Expected 0x1FFFFFFF, got sigma0: 0x{int(dut.sigma0.value):08X}"
    assert dut.sigma1.value == 0x003FFFFF, f"Expected 0x003FFFFF, got sigma1: 0x{int(dut.sigma1.value):08X}"
    
    dut._log.info("x,y,z = max,max,max")
    dut.x.value = 0xFFFFFFFF
    dut.y.value = 0xFFFFFFFF
    dut.z.value = 0xFFFFFFFF
    await Timer(1, units='ns')
    assert dut.Ch.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Ch: 0x{int(dut.Ch.value):08X}"
    assert dut.Maj.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Maj: 0x{int(dut.Maj.value):08X}"
    assert dut.Sigma0.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Sigma0: 0x{int(dut.Sigma0.value):08X}"
    assert dut.Sigma1.value == 0xFFFFFFFF, f"Expected 0xFFFFFFFF, got Sigma1: 0x{int(dut.Sigma1.value):08X}"
    assert dut.sigma0.value == 0x1FFFFFFF, f"Expected 0x1FFFFFFF, got sigma0: 0x{int(dut.sigma0.value):08X}"
    assert dut.sigma1.value == 0x003FFFFF, f"Expected 0x003FFFFF, got sigma1: 0x{int(dut.sigma1.value):08X}"

    dut._log.info(f"Constrained Random Tests") 

    for i in range(100):

        dut.x.value = random.randint(0,0xFFFFFFFF)
        dut.y.value = random.randint(0,0xFFFFFFFF)
        dut.z.value = random.randint(0,0xFFFFFFFF)

        dut._log.info(f"x,y,z = {dut.x.value}, {dut.y.value}, {dut.z.value}")     

        await Timer(1, units='ns')

        ref_results = sha256_funcs_ref(int(dut.x.value), int(dut.y.value), int(dut.z.value))

        assert dut.Ch.value == ref_results[0], f"Expected 0x{ref_results[0]:0X}, got Ch: 0x{int(dut.Ch.value):08X}"
        assert dut.Maj.value == ref_results[1], f"Expected 0x{ref_results[1]:0X}, got Maj: 0x{int(dut.Maj.value):08X}"
        assert dut.Sigma0.value == ref_results[2], f"Expected 0x{ref_results[2]:0X}, got Sigma0: 0x{int(dut.Sigma0.value):08X}"
        assert dut.Sigma1.value == ref_results[3], f"Expected 0x{ref_results[3]:0X}, got Sigma1: 0x{int(dut.Sigma1.value):08X}"
        assert dut.sigma0.value == ref_results[4], f"Expected 0x{ref_results[4]:0X}, got sigma0: 0x{int(dut.sigma0.value):08X}"
        assert dut.sigma1.value == ref_results[5], f"Expected 0x{ref_results[5]:0X}, got sigma1: 0x{int(dut.sigma1.value):08X}"

    dut._log.info("Tests passed!")