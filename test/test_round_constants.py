import cocotb
from cocotb.triggers import Timer
import random

# ---------- Initial constant values ---------- #
K_CONSTANTS = ["428a2f98", "71374491", "b5c0fbcf", "e9b5dba5", "3956c25b", "59f111f1", "923f82a4", "ab1c5ed5",
               "d807aa98", "12835b01", "243185be", "550c7dc3", "72be5d74", "80deb1fe", "9bdc06a7", "c19bf174",
               "e49b69c1", "efbe4786", "0fc19dc6", "240ca1cc", "2de92c6f", "4a7484aa", "5cb0a9dc", "76f988da",
               "983e5152", "a831c66d", "b00327c8", "bf597fc7", "c6e00bf3", "d5a79147", "06ca6351", "14292967",
               "27b70a85", "2e1b2138", "4d2c6dfc", "53380d13", "650a7354", "766a0abb", "81c2c92e", "92722c85",
               "a2bfe8a1", "a81a664b", "c24b8b70", "c76c51a3", "d192e819", "d6990624", "f40e3585", "106aa070",
               "19a4c116", "1e376c08", "2748774c", "34b0bcb5", "391c0cb3", "4ed8aa4a", "5b9cca4f", "682e6ff3",
               "748f82ee", "78a5636f", "84c87814", "8cc70208", "90befffa", "a4506ceb", "bef9a3f7", "c67178f2"]

IV = "6a09e667bb67ae853c6ef372a54ff53a510e527f9b05688c1f83d9ab5be0cd19"

K_CONSTANTS_INT = [int(k, 16) for k in K_CONSTANTS]
IV_INT = int(IV, 16)

# ---------- Test K_t Constants ---------- #
@cocotb.test(name="K_t Constants")
async def test_K_t(dut):
    dut._log.info("Starting test for K_t constants")

    dut.idx.value = 0
    await Timer(1, unit='ns')

    for idx in range(64):
        dut.idx.value = idx
        await Timer(1, unit='ns')

        assert dut.K_t.value == K_CONSTANTS_INT[idx], f"Expected K_t = {K_CONSTANTS_INT[idx]}"

    dut._log.info("Test Passed!")

# ---------- Test K_t Constants ---------- #
@cocotb.test(name="Initial Vector")
async def test_initial_vector(dut):
    dut._log.info("Starting test for the Initial Vector")

    dut.idx.value = 0
    await Timer(1, unit='ns')

    assert dut.IV.value == IV_INT, f"Expected Initial Vector to be: {IV_INT}"

    dut._log.info("Test Passed!")