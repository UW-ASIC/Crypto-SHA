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
  output reg  [63:0]  bitlen
);

    reg [63:0] msglen; // length of input data
    reg [951:0] msg_q; // stores msg (up to 952 bits since maximum amount of blocks module produces is 2)
    reg [1023:0] padded; // stores final padded message
    reg inter_ready; // intermediate signal to allow comb. logic with in_ready
    reg double_blk;
    integer i;

    assign in_ready = inter_ready;
    assign bitlen = msglen;

    always @ (posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            inter_ready <= 1;
            blk_valid <= 0;
            blk_data <= 512'b0;
            msg_q <= 1024'b0;
            msglen <= 64'b0;
            double_blk <= 0;

        end
        
        else begin

            if (!in_valid && inter_ready) begin // for empty messages

                if (in_last) begin

                    inter_ready <= 0;
                    blk_valid <= 1;
                    blk_data <= 1<<511;

                end

            end

            else begin

                if (msglen == 0) begin
                    
                    blk_valid <= 0;
                    inter_ready <= 1;

                end

                if (in_valid && inter_ready) begin

                    if (in_last) inter_ready <= 0;
                    else msglen <= msglen + 8;
                
                    msg_q <= {msg_q[943:0], in_data}; 

                end

                else if (blk_ready) begin

                    if (msglen != 0) begin

                        blk_valid <= 1;

                        if (!double_blk) begin
                            
                            blk_data <= padded[1023:512];
                            if (msglen >= 448) double_blk <= 1;
                            else msglen <= 0;

                        end

                        else begin
                            
                            blk_data <= padded[511:0];
                            msglen <= 0;
                            double_blk <= 0;

                        end

                    end

                end


            end

        end

    end

    always @ (*) begin

        padded = 1024'd0;  

        // Copy message bytes
        for(i = 0; i < msglen/8; i = i + 1)
            padded[1023 - 8*i -: 8] = msg_q[msglen-1 - 8*i -: 8];

        // Append the 0x80 bit
        padded[1023 - msglen -: 8] = 8'h80;

        // Append 64-bit message length
        if (msglen <= 440) padded[575:512] = msglen;
        else padded[63:0] = msglen;

    end



endmodule