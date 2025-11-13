# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

@cocotb.test()
async def test_sharounds(dut):
    """Test round"""

    dut._log.info("=== Starting SHARounds test ===")

    # 10us clock
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # reset phase
    dut._log.info("Applying reset")
    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.out_ready.value = 0
    await Timer(100, unit="ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut._log.info("Reset released")

    K = [
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5,
    0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5
    ]

    W = [
    0x61626380, 0x00000000, 0x00000000, 0x00000000,
    0x00000000, 0x00000000, 0x00000000, 0x00000000
    ]

    H0 = [
    0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
    0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19
    ]

    H1 = [   
    0x5D6AEBCD, 0x6A09E667, 0xBB67AE85, 0x3C6EF372,
    0xFA2A4622, 0x510E527F, 0x9B05688C, 0x1F83D9AB
    ]

    H2 = [
    0x5A6AD9AD, 0x5D6AEBCD, 0x6A09E667, 0xBB67AE85,
    0x78CE7989, 0xFA2A4622, 0x510E527F, 0x9B05688C
    ]

    H3 = [
    0xC8C347A7, 0x5A6AD9AD, 0x5D6AEBCD, 0x6A09E667,
    0xF92939EB, 0x78CE7989, 0xFA2A4622, 0x510E527F
    ]

    H4 = [
    0xD550F666, 0xC8C347A7, 0x5A6AD9AD, 0x5D6AEBCD,
    0x24E00850, 0xF92939EB, 0x78CE7989, 0xFA2A4622
    ]

    H5 = [
    0x04409A6A, 0xD550F666, 0xC8C347A7, 0x5A6AD9AD,
    0x43ADA245, 0x24E00850, 0xF92939EB, 0x78CE7989
    ]

    H6 = [
    0x2B4209F5, 0x04409A6A, 0xD550F666, 0xC8C347A7,
    0x714260AD, 0x43ADA245, 0x24E00850, 0xF92939EB
    ]

    H7 = [
    0xE5030380, 0x2B4209F5, 0x04409A6A, 0xD550F666,
    0x9B27A401, 0x714260AD, 0x43ADA245, 0x24E00850
    ]

    H8 = [
    0x85A07B5F, 0xE5030380, 0x2B4209F5, 0x04409A6A,
    0x0C657A79, 0x9B27A401, 0x714260AD, 0x43ADA245
    ]



    async def run_round(Hin, i, expected):
        dut.a_i.value = Hin[0]
        dut.b_i.value = Hin[1]
        dut.c_i.value = Hin[2]
        dut.d_i.value = Hin[3]
        dut.e_i.value = Hin[4]
        dut.f_i.value = Hin[5]
        dut.g_i.value = Hin[6]
        dut.h_i.value = Hin[7]

        dut.W_t.value = W[i]
        dut.K_t.value = K[i]

        dut.out_ready.value = 1
        dut.in_valid.value = 1

        await RisingEdge(dut.clk)
        dut.in_valid.value = 0

        while True:
            await RisingEdge(dut.clk)
            if dut.out_valid.value == 1:
                break
        
        a = int(dut.a_o.value)
        b = int(dut.b_o.value)
        c = int(dut.c_o.value)
        d = int(dut.d_o.value)
        e = int(dut.e_o.value)
        f = int(dut.f_o.value)
        g = int(dut.g_o.value)
        h = int(dut.h_o.value)

        dut._log.info(f"A={a:08x} B={b:08x} C={c:08x} D={d:08x}")
        dut._log.info(f"E={e:08x} F={f:08x} G={g:08x} H={h:08x}")


        got = [a,b,c,d,e,f,g,h]
        assert got == expected, f"t={i} mismatch! expected {expected}, got {got}"

        dut._log.info(f"✓ t={i} PASSED")

        # reset phase
        dut._log.info("Applying reset")
        dut.rst_n.value = 0
        dut.in_valid.value = 0
        dut.out_ready.value = 0
        await Timer(100, unit="ns")
        dut.rst_n.value = 1
        await RisingEdge(dut.clk)
        dut._log.info("Reset released")

    await run_round(H0, 0, H1)
    await run_round(H1, 1, H2)
    await run_round(H2, 2, H3)
    await run_round(H3, 3, H4)
    await run_round(H4, 4, H5)
    await run_round(H5, 5, H6)
    await run_round(H6, 6, H7)
    await run_round(H7, 7, H8)