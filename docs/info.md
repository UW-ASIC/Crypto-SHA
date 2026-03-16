## How it works

This project implements a SHA-256 hardware accelerator optimized for fixed 256-bit (32-byte) messages. It accepts a message over a byte-serial bus, computes the SHA-256 digest using a fully unrolled 64-round pipeline, and streams the resulting 32-byte digest back out.

The design is split into four main submodules:

**Message buffer (`padder.v`)** collects the 32 incoming bytes and assembles them into a 256-bit block. Because the input is always exactly 32 bytes, SHA-256 padding is applied statically: a `0x80` byte is appended at word 8, all intermediate words are zero, and the final word encodes the message length (256 bits) as a big-endian 64-bit integer split across words 14–15.

**Message schedule (`message_schedule.v`)** expands the 16 initial words W[0..15] into 64 round words using a 16-entry sliding window. At each round t ≥ 16, the next word is computed as σ1(W[t-2]) + W[t-7] + σ0(W[t-15]) + W[t-16], where σ0 and σ1 are the standard SHA-256 small-sigma functions (ROTR7 ⊕ ROTR18 ⊕ SHR3 and ROTR17 ⊕ ROTR19 ⊕ SHR10 respectively).

**Round unit (`round.v`)** performs one SHA-256 compression round per invocation. It computes T1 = h + Σ1(e) + Ch(e,f,g) + K[t] + W[t] and T2 = Σ0(a) + Maj(a,b,c), then shifts the eight working variables accordingly. It uses a two-phase handshake (IDLE → COMP) and exposes valid/ready signals for flow control.

**Round constants (`round_constants.v`)** provides the 64 SHA-256 constants K[0..63] derived from the fractional parts of the cube roots of the first 64 primes.

The top-level SHA module (`SHA.v`) sequences these blocks through a bus-protocol FSM. Three opcodes are supported: `LOAD_TEXT` (01) streams 32 bytes into the message buffer, `HASH` (11) initiates hashing, and `WRITE_RESULT` (10) streams the 32-byte digest back out. After the digest is transmitted the module asserts `ack_valid` and waits for `ack_ready` before returning to idle.

## How to test

The design is tested using [cocotb](https://www.cocotb.org/) with Icarus Verilog. Three test cases are included:

1. **NIST known-answer vectors** — three fixed 32-byte inputs with precomputed SHA-256 digests are hashed and compared against expected values. These are deterministic and catch fundamental correctness regressions.

2. **Random 256-bit message** — a random 32-byte message is hashed by the DUT and compared against Python's `pycryptodome` SHA256 reference implementation.

3. **Back-to-back hashes** — two different random messages are hashed consecutively without resetting the DUT, verifying that internal state (working variables, digest register, message buffer) clears correctly between operations.

To run the tests:

```bash
cd test
make
```

The testbench drives the SHA core using the byte-serial bus interface directly. A message is loaded with `LOAD_TEXT`, hashing is triggered with `HASH`, and the result is read back with `WRITE_RESULT`. The `ack_ready` signal is held low during digest readout so the `ACK_HOLD` state does not self-clear before the testbench can observe `ack_valid`.

## External hardware

None. The design is entirely self-contained and requires only a clock and reset.

## SHA Rounds

### How the SHA-256 standard defines the process

SHA-256 requires 64 rounds of bitwise math on eight 32-bit working registers (a–h). Two temporary values are calculated each round using rotations and bitwise operations from the six core SHA-256 functions (Ch, Maj, Σ0, Σ1, σ0, σ1), combined with a unique round constant and message schedule word. The registers are then shifted: b←a, c←b, ..., h←g, with e receiving d+T1 and a receiving T1+T2.

### Implementation

The round unit uses a two-phase design:

- **IDLE**: waits until `in_valid` and `out_ready` are both asserted before accepting new inputs.
- **COMP**: computes the next set of outputs combinatorially and registers them, then asserts `out_valid`.

All six SHA-256 functions (Ch, Maj, Σ0, Σ1, σ0, σ1) are implemented as Verilog functions using bitwise operations and barrel-shifter rotations.

### Testing Methodology

The module was tested against known SHA-256 test vectors including the NIST FIPS 180-4 examples. The full 64-round sequence is exercised for each test vector, with the final digest compared against a Python reference implementation.

### Integration Notes

Outputs are not cleared in the idle state or reset state. The round unit feeds into the top-level SHA FSM, which manages working variable registers (a–h) and sequences the 64 rounds using a counter. The message schedule sliding window is advanced by one position per round for rounds 16–63.