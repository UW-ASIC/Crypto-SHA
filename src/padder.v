module padder(
  input  wire         clk,
  input  wire         rst_n,

  // Ingress bytes for exactly one message
  input  wire         in_valid,
  output wire         in_ready,
  input  wire [7:0]   in_data,
  input  wire         in_last,       // marks last byte of the message

  // 512-bit block out
  output reg          blk_valid,
  input  wire         blk_ready,
  output reg  [511:0] blk_data,

  // Optional: message length out (debug)
  //output reg  [63:0]  bitlen
);

    reg [63:0] msgidx; // used for indexing blk_q after initial msg length is determined
    reg [63:0] msglen; // length of input data
    reg [1023:0] blk_q; // stores up to 2 blocks after padding
    reg inter_ready; // intermediate signal to allow comb. logic with in_ready

    assign in_ready = inter_ready;

    reg [3:0] current_state, next_state;
    localparam IDLE = 3'b000, 
               MSG = 3'b001, // receive data bytes
               PAD_0x80 = 3'b010, // pads first 0x80 byte
               PAD_ZEROS = 3'b011, // pads 0x00 until 64 bits remain in block
               BLK_DOUBLE = 3'b100, // shifts in first out of two blocks
               BLK_SINGLE = 3'b101; // shifts in last block out of 2 blocks OR shifts in single block

    assign bitlen = msglen;

    always @ (posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            blk_q <= 1024'b0;
            msgidx <= 64'b0;
            msglen <= 64'b0;
            current_state <= IDLE;

        end
        
        else begin

            current_state <= next_state;

            if (current_state == IDLE) begin

                blk_q <= 1024'b0;
                msgidx <= 64'b0;
                msglen <= 64'b0;
                
            end


            if (current_state == MSG) begin
                
                if (in_valid) begin // for non empty messages
                    blk_q <= {blk_q[1015:0], in_data};
                    msgidx <= msgidx+8;
                end


            end

            else if (current_state == PAD_0x80) begin

                msglen <= msgidx;
                blk_q <= {blk_q[1015:0], 8'h80};
                msgidx <= msgidx+8;

            end

            else if (current_state == PAD_ZEROS) begin

                if (msgidx%512 == 448) begin
                    blk_q <= {blk_q[959:0], msglen[63:0]};
                end
                else begin
                    blk_q <= {blk_q[1015:0], 8'h00};
                    msgidx <= msgidx+8;
                end

            end

        end

    end

    // STATE TRANSITION LOGIC

    always @ (*) begin

        case (current_state) 

            IDLE: begin
                
                if (!in_valid) begin
                    if (in_last) next_state = BLK_SINGLE; // for empty messages
                    else next_state = IDLE;
                end
                else next_state = MSG;

            end

            MSG: begin

                if (in_valid) begin
                
                    if (!in_last) next_state = MSG;
                    else next_state = PAD_0x80;

                end

                else next_state = IDLE;


            end

            PAD_0x80: begin

                next_state = PAD_ZEROS;

            end

            PAD_ZEROS: begin

                if (msgidx%512 == 448) begin
                    if (msgidx == 448) next_state = BLK_SINGLE;
                    else next_state = BLK_DOUBLE;
                end
                else next_state = PAD_ZEROS;

            end

            BLK_DOUBLE: begin

                if (!blk_ready) next_state = BLK_DOUBLE;
                else next_state = BLK_SINGLE;

            end

            BLK_SINGLE: begin

                if (!blk_ready) next_state = BLK_SINGLE;
                else next_state = IDLE;

            end

        endcase

    end

    // OUTPUT LOGIC

    always @ (*) begin

        case (current_state) 

            IDLE: begin

                inter_ready = 1;
                blk_valid = 0;
                blk_data = 0;

            end

            MSG: begin

                if (in_last) inter_ready = 0;
            
            end

            BLK_DOUBLE: begin

                blk_valid = 1;

                if (blk_ready) blk_data = blk_q[1023:512];
                    
            end

            BLK_SINGLE: begin

                blk_valid = 1;

                if (blk_ready) begin

                    if (!in_valid && in_last) blk_data = 1<<511;

                    else begin
                
                        if (msgidx > 512) begin
                            if (blk_q[511:0] == 512'b0) blk_valid = 0;
                            else blk_data = blk_q[511:0];
                        end
                        else blk_data = blk_q[511:0];

                    end

                end
            
            end



        endcase

    end

endmodule