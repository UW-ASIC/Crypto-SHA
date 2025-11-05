`default_nettype none
`timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb_sha256_funcs ();

  // Dump the signals to a VCD file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb_sha256_funcs.vcd");
    $dumpvars(0, tb_sha256_funcs);
    #1;
  end

  // Wire up the inputs and outputs:
  wire [31:0] x, y, z;
  wire [31:0] Ch;     // (x & y) ^ (~x & z)
  wire [31:0] Maj;     // (x & y) ^ (x & z) ^ (y & z)
  wire [31:0] Sigma0;  // ROTR2 ^ ROTR13 ^ ROTR22
  wire [31:0] Sigma1;  // ROTR6 ^ ROTR11 ^ ROTR25
  wire [31:0] sigma0;  // ROTR7 ^ ROTR18 ^ SHR3
  wire [31:0] sigma1;   // ROTR17 ^ ROTR19 ^ SHR10

  // Replace tt_um_example with your module name:
  sha256_funcs INST1 (

      .x      (x),
      .y      (y),
      .z      (z),
      .Ch     (Ch),
      .Maj    (Maj),
      .Sigma0 (Sigma0),
      .Sigma1 (Sigma1),
      .sigma0 (sigma0),
      .sigma1 (sigma1)

  );

endmodule
