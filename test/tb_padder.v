`default_nettype none
`timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb_padder ();

  // Dump the signals to a VCD file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb_padder.vcd");
    $dumpvars(0, tb_padder);
    #1;
  end

  // Wire up the inputs and outputs:
  wire clk;
  wire rst_n;

  // Ingress bytes for exactly one message
  wire in_valid;
  wire in_ready;
  wire [7:0] in_data;
  wire in_last; // marks last byte of the message

  // 512-bit block out
  reg blk_valid;
  wire blk_ready;
  reg  [511:0] blk_data;

  // Optional: message length out (debug)
  reg [63:0] bitlen;

  // Replace tt_um_example with your module name:
  padder INST1 (

    .clk(clk),
    .rst_n(rst_n),
    .in_valid(in_valid),
    .in_ready(in_ready),
    .in_data(in_data),
    .in_last(in_last),       
    .blk_valid(blk_valid),
    .blk_ready(blk_ready),
    .blk_data(blk_data),
    .bitlen(bitlen)
  );

endmodule
