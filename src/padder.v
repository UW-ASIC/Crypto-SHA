module msg_buffer_256b (
  input  wire       clk,
  input  wire       rst_n,
  input [5:0]       byte_cnt,

  // 32-byte message input
  input  wire       in_valid,
  output wire       in_ready,
  input  wire [7:0] in_data,
  input  wire       in_last,   // must be 1 on 32nd byte

  output reg        msg_valid,
  input  wire       msg_ready,
  output reg [255:0] msg_block   // 32 bytes, big-endian
);

  reg       collecting;
  assign in_ready = collecting;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      collecting <= 1'b1;
      msg_valid  <= 1'b0;
      msg_block  <= 256'd0;
    end else begin
      if (collecting && in_valid && in_ready) begin
        // Big-endian: first byte -> bits [255:248], second -> [247:240], ...
        msg_block[255 - 8*byte_cnt -: 8] <= in_data;

        if (byte_cnt == 5'd31) begin
          collecting <= 1'b0;
          msg_valid  <= 1'b1;
        end
      end

      if (!collecting && msg_valid && msg_ready) begin
        // ready for next message
        msg_valid <= 1'b0;
        collecting <= 1'b1;
        msg_block  <= 256'd0;
      end
    end
  end

endmodule
