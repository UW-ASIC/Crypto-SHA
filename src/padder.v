module padder (
  input  wire clk,
  input  wire rst_n,
  input  wire in_valid,
  output wire in_ready,
  input  wire [7:0] in_data,
  input  wire in_last,
  output reg blk_valid,
  input  wire blk_ready,
  output reg [511:0] blk_data
);

  localparam
    Idle = 3'b000,
    Receive = 3'b001,
    Pad1 = 3'b010,
    Pad2 = 3'b011,
    Append_len = 3'b100,
    Drive = 3'b101;
  
  reg [511:0] storage;
  reg [5:0] counter;
  reg [63:0] bitlen;
  reg [2:0] state;
  reg emit_req;

  wire out_blocked = (blk_valid && !blk_ready) || emit_req;
  assign in_ready = ((state == Idle) || (state == Receive)) && !out_blocked;
  wire [12:0] be_low = 13'd511 - {counter, 3'b000};

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state <= Idle;
      counter <= 0;
      storage <= 0;
      blk_valid <= 0;
      blk_data <= 0;
      bitlen <= 0;
      emit_req <= 0;
    end else begin
      if (emit_req && !blk_valid) begin
        blk_data <= storage;
        blk_valid <= 1'b1;
        emit_req  <= 1'b0;
      end

      if (blk_valid && blk_ready) begin
        blk_valid <= 1'b0;
      end

      case (state)
        Idle: begin
          counter <= 6'd0;
          if (in_valid && in_ready) begin
            state <= Receive;
          end
        end

        Receive: begin
          if (in_valid && in_ready) begin
            storage[be_low -: 8] <= in_data;
            bitlen <= bitlen + 64'd8;
            if (counter == 6'd63) begin
              emit_req <= 1'b1;
              counter <= 6'd0;
            end else begin
              counter <= counter + 6'd1;
            end

            if (in_last) begin
              state <= Pad1;
            end
          end
        end

        Pad1: begin
          if (!out_blocked) begin
            storage[be_low -: 8] <= 8'h80;
            if (counter == 6'd63) begin
              emit_req <= 1'b1;
              counter <= 6'd0;
            end else begin
              counter <= counter + 6'd1;
            end
            state <= Pad2;
          end
        end

        Pad2: begin
          if (!out_blocked) begin
            if (counter == 6'd56) begin
              state <= Append_len;
            end else begin
              storage[be_low -: 8] <= 8'h00;
              if (counter == 6'd63) begin
                emit_req <= 1'b1;
                counter <= 6'd0;
              end else begin
                counter <= counter + 6'd1;
              end
            end
          end
        end

        Append_len: begin
          if (!out_blocked) begin
            storage[63:0] <= bitlen;
            state <= Drive;
          end
        end

        Drive: begin
          if (!blk_valid && !emit_req) begin
            blk_data <= storage;
            blk_valid <= 1'b1;
          end
          if (blk_valid && blk_ready) begin
            blk_valid <= 1'b0;
            state <= Idle;
            counter <= 6'd0;
            bitlen <= 64'd0;
            storage <= 512'd0;
          end
        end

        default: state <= Idle;
      endcase
    end
  end

endmodule