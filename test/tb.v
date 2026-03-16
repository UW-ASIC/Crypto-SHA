`default_nettype none
`timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb ();

  // Dump the signals to a VCD file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb.vcd");
    $dumpvars(0, tb);
    #1;
  end

  // Wire up the inputs and outputs:

    //   input wire clk,
    // input wire rst_n,

    // // DATA BUS
    // input  wire [7:0] data_in,
    // output wire       ready_in,
    // input  wire       valid_in,
    // output wire [7:0] data_out,
    // input  wire       data_ready,
    // output wire       data_valid,

    // // ACK BUS
    // input  wire       ack_ready,
    // output wire       ack_valid,
    // output wire [1:0] module_source_id,

    // // TRANSACTION BUS
    // input  wire [1:0]  opcode,
    // input  wire [1:0]  source_id,
    // input  wire [1:0]  dest_id,
    // input  wire        encdec,      // unused for SHA
    // input  wire [23:0] addr         // unused
  reg clk;
  reg rst_n;
  reg [7:0] data_in;
  wire       ready_in;
  reg       valid_in;
  wire [7:0] data_out;
  reg       data_ready;
  wire       data_valid;
  reg       ack_ready;
  wire       ack_valid;
  wire [1:0] module_source_id;
  reg [1:0]  opcode;
  reg [1:0]  source_id;
  reg [1:0]  dest_id;
  reg        encdec;
  reg [23:0] addr;
`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;

  // In gate-level simulation the netlist top is tt_um_example.
  // The SHA bus signals are packed into the TinyTapeout ui/uo/uio ports:
  //   ui[7:0]  = data_in[7:0]
  //   uo[7:0]  = data_out[7:0]
  //   uio[0]   = opcode[0]
  //   uio[1]   = opcode[1]
  //   uio[2]   = source_id[0]
  //   uio[3]   = source_id[1]
  //   uio[4]   = dest_id[0]
  //   uio[5]   = dest_id[1]
  //   uio[6]   = valid_in (input) / data_valid (output)
  //   uio[7]   = ready_in (input) / data_ready (input)
  // Additional control signals are not exposed through the TT wrapper,
  // so gate-level test coverage is limited to the wrapper I/O.
  wire [7:0] uio_out;
  wire [7:0] uio_oe;
  wire [7:0] uio_in;
  assign uio_in[1:0] = opcode;
  assign uio_in[3:2] = source_id;
  assign uio_in[5:4] = dest_id;
  assign uio_in[6]   = valid_in;
  assign uio_in[7]   = data_ready;
  assign data_valid  = uio_out[6];
  assign ready_in    = uio_out[7];

  tt_um_example dut (
    .clk     (clk),
    .rst_n   (rst_n),
    .ena     (1'b1),
    .ui_in   (data_in),
    .uo_out  (data_out),
    .uio_in  (uio_in),
    .uio_out (uio_out),
    .uio_oe  (uio_oe),
    .VPWR    (VPWR),
    .VGND    (VGND)
  );

`else

  sha sha(
    .clk(clk),
    .rst_n(rst_n),
    .data_in(data_in),
    .ready_in(ready_in),
    .valid_in(valid_in),
    .data_out(data_out),
    .data_ready(data_ready),
    .data_valid(data_valid),
    .ack_ready(ack_ready),
    .ack_valid(ack_valid),
    .module_source_id(module_source_id),
    .opcode(opcode),
    .source_id(source_id),
    .dest_id(dest_id),
    .encdec(encdec),
    .addr(addr)
  );

`endif

endmodule