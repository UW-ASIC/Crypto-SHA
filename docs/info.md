<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

Explain how your project works

## How to test

Explain how to use your project

## External hardware

List external hardware used in your project (e.g. PMOD, LED display, etc), if any

## SHA Rounds

### How the SHA-256 standard defines the process



### Implementation

2 phase design:
COMP: computes the next set of outputs
IDLE: waits until out_ready and in_valid to accept next set of inputs


### Testing Methodology

The module was tested against the first test case in https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/SHA256.pdf

Only 8 iterations were tested for simplicity, to verify that the module behaves as expected.


### Integration Notes (remove or update once integration complete)

Outputs are not cleared in the idle state or in the reset state. To calculate next set of values, might be possible to use output registers to calculate next set of values based on a counter, or simply feed the output values from the next module back into this module as input.



