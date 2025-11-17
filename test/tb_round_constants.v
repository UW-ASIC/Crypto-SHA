`default_nettype none
`timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb_round_constants ();

  // Dump the signals to a VCD file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb_round_constants.vcd");
    $dumpvars(0, tb_round_constants);
    #1;
  end

  // Wire up the inputs and outputs:
  wire [6:0] idx;
  wire [31:0] K_t;
  wire [255:0] IV;    

  // Replace tt_um_example with your module name:
  round_constants INST1 (
    .idx    (idx),
    .K_t    (K_t),
    .IV     (IV)
  );

endmodule
