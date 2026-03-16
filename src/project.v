/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_example (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // ---------------------------------------------------------------
  // Pin mapping
  //
  //  INPUTS
  //    ui_in[7:0]   -> data_in[7:0]
  //    uio_in[0]    -> valid_in
  //    uio_in[1]    -> data_ready
  //    uio_in[2]    -> ack_ready
  //    uio_in[3]    -> opcode[0]
  //    uio_in[4]    -> opcode[1]
  //    uio_in[7:5]  -> (unused)
  //
  //  OUTPUTS
  //    uo_out[7:0]  -> data_out[7:0]
  //    uio_out[5]   -> ready_in
  //    uio_out[6]   -> data_valid
  //    uio_out[7]   -> ack_valid
  //    uio_out[4:0] -> 0
  // ---------------------------------------------------------------

  // uio[7:5] are outputs, uio[4:0] are inputs
  assign uio_oe = 8'b1110_0000;

  // ---- extract control fields from uio_in ----
  wire [1:0] opcode_w = {uio_in[4], uio_in[3]};

  // Derive source_id / dest_id from opcode so we don't need
  // dedicated pins for them (only two IDs are ever used):
  //   LOAD_TEXT   (01) : source = MEM (00), dest = SHA (01)
  //   WRITE_RESULT(10) : source = SHA (01), dest = MEM (00)
  //   HASH        (11) : source = MEM (00), dest = SHA (01)
  //   idle        (00) : source = 00,       dest = 00
  reg [1:0] source_id_w;
  reg [1:0] dest_id_w;

  always @(*) begin
    case (opcode_w)
      2'b01:   begin source_id_w = 2'b00; dest_id_w = 2'b01; end
      2'b10:   begin source_id_w = 2'b01; dest_id_w = 2'b00; end
      2'b11:   begin source_id_w = 2'b00; dest_id_w = 2'b01; end
      default: begin source_id_w = 2'b00; dest_id_w = 2'b00; end
    endcase
  end

  // ---- SHA-256 core ----
  wire        ready_in_w;
  wire [7:0]  data_out_w;
  wire        data_valid_w;
  wire        ack_valid_w;
  wire [1:0]  module_source_id_w;

  sha sha_inst (
      .clk            (clk),
      .rst_n          (rst_n),

      // Data bus
      .data_in        (ui_in),
      .ready_in       (ready_in_w),
      .valid_in       (uio_in[0]),
      .data_out       (data_out_w),
      .data_ready     (uio_in[1]),
      .data_valid     (data_valid_w),

      // Ack bus
      .ack_ready      (uio_in[2]),
      .ack_valid      (ack_valid_w),
      .module_source_id(module_source_id_w),

      // Transaction bus
      .opcode         (opcode_w),
      .source_id      (source_id_w),
      .dest_id        (dest_id_w),
      .encdec         (1'b0),
      .addr           (24'd0)
  );

  // ---- wire outputs ----
  assign uo_out       = data_out_w;

  assign uio_out[4:0] = 5'b0;
  assign uio_out[5]   = ready_in_w;
  assign uio_out[6]   = data_valid_w;
  assign uio_out[7]   = ack_valid_w;

  // Tie off unused signals
  wire _unused = &{ena, uio_in[7:5], module_source_id_w, 1'b0};

endmodule