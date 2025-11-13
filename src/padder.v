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

    reg [2:0] state;
    reg [63:0] bit_len;
    reg [6:0] counter = 7'd64;
    reg extra;
    reg extra1;
    reg extra0;
    assign in_ready = ((state == Receive) && (counter > 0));

always @(posedge clk or negedge rst_n) begin
    if (!rst_n)begin
        counter <= 7'd64;
        bit_len <= 64'b0;
        extra <= 1'b0;
        blk_valid <= 0;
        extra1 <= 1'b0;
        state <= Idle;
        extra0 <= 0;
    end else begin
        case (state)
            Idle: begin
                if (in_valid) begin
                    state <= Receive;
                end
                if (in_last && !(in_valid)) begin
                    state <= Pad1;
                end
            end

            Receive: begin
                if ((counter > 7) && (in_valid && in_ready)) begin
                    blk_data[(counter*8)-1 -: 8] <= in_data;
                    counter <= counter-1;
                    bit_len <= bit_len + 8;
                    if (in_last) begin
                        state <= Pad1;
                    end
                end else if ((counter > 1) && in_valid && in_ready) begin
                    blk_data[(counter*8)-1 -: 8] <= in_data;
                    bit_len <= bit_len + 8;
                    counter <= counter - 1;
                    if (in_last && in_valid && in_ready) begin
                        state <= Pad1;
                    end
                end else if ((counter == 1) && in_last && in_ready && in_valid) begin
                        blk_data[(counter*8)-1 -: 8] <= in_data;
                        bit_len <= bit_len + 8;
                        extra1 <= 1;
                        state <= Drive;
                end else if (counter == 1 && in_ready && in_valid) begin
                    blk_data[(counter*8)-1 -: 8] <= in_data;
                    bit_len <= bit_len + 8;
                    extra <= 1;
                    state <= Drive;
                end
            end

            Pad1: begin
                blk_data[(counter*8)-1 -: 8] <= 8'b10000000;
                counter <= counter-1;
                state <= Pad2;
            end

            Pad2: begin
                if (counter > 8) begin
                    blk_data[(counter*8)-1 -: 8] <= 8'b00000000;
                    counter <= counter - 1;
                    if (counter == 8) begin
                        state <= Append_len;
                    end
                end else if (counter == 8) begin
                    state <= Append_len;
                end
                else if ( (counter < 8) && (counter >= 0)) begin
                    if (counter == 0) begin
                        extra0 <= 1;
                        state <= Drive;
                    end else begin
                        blk_data[(counter*8)-1 -: 8] <= 8'b00000000;
                        counter <= counter - 1;    
                    end
                end
            end
            
            Append_len: begin 
                blk_data[63:0] <= bit_len;
                state <= Drive;
            end
            
            Drive: begin
                blk_valid <= 1;
                if (blk_ready) begin
                    blk_valid <= 0;
                    counter <= 7'd64;
                    if (extra) begin
                    state <= Receive;
                    extra1 <= 0;
                    extra <= 0;
                    extra0 <= 0;
                    end else if (extra1)begin
                        state <= Pad1;
                        extra1 <= 0;
                        extra <= 0;
                        extra0 <= 0;
                    end else if (extra0) begin
                        state <= Pad2;
                        extra1 <= 0;
                        extra <= 0;
                        extra0 <= 0;
                    end else begin
                        state <= Idle;
                        bit_len <= 0;
                    end
                end
            end
            default: state <= Idle;
        endcase
    end
end

endmodule