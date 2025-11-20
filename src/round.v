module round(
  input  wire         clk,
  input  wire         rst_n,

  input  wire [31:0]  a_i, b_i, c_i, d_i, e_i, f_i, g_i, h_i,
  input  wire [31:0]  K_t,
  input  wire [31:0]  W_t,
  input  wire         in_valid,
  output reg          in_ready, // changed this to a reg (if thats ok with the rest of the design, if not i can change it back)

  output reg  [31:0]  a_o, b_o, c_o, d_o, e_o, f_o, g_o, h_o,
  output reg          out_valid,
  input  wire         out_ready
);


reg [31:0] T1, T2;

localparam IDLE = 1'd0;
localparam COMP = 1'd1;
reg phase;

function automatic [31:0] Ch(input [31:0] xi, input [31:0] yi, input [31:0] zi);
    begin
        Ch = (xi & yi) ^ ((~xi) & zi);
    end
endfunction

function automatic [31:0] Ma(input [31:0] xi, input [31:0] yi, input [31:0] zi);
    begin
        Ma = (xi & yi) ^ (xi & zi) ^ (yi & zi);
    end
endfunction

function automatic [31:0] ROTR(input [31:0] xi, input integer n);
    begin
        ROTR = (xi >> n) | (xi << (32-n));
    end
endfunction

function automatic [31:0] S0(input [31:0] xi);
    begin
        S0 = ROTR(xi, 2) ^ ROTR(xi, 13) ^ ROTR(xi, 22);
    end
endfunction

function automatic [31:0] S1(input [31:0] xi);
    begin
        S1 = ROTR(xi, 6) ^ ROTR(xi, 11) ^ ROTR(xi, 25);
    end
endfunction



always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        out_valid <= 0;
        in_ready  <= 0;
        phase     <= IDLE;
    end else begin
        case (phase)
            IDLE: begin
                in_ready <= 1;
                out_valid <= 0;
                if (out_ready == 1 && in_valid == 1) begin
                    phase <= COMP;
                end
            end
            COMP: begin
                in_ready <= 0;
                //T1  <= h_i + S1(e_i) + Ch(e_i, f_i, g_i) + K_t + W_t;
                //T2  <= S0(a_i) + Ma(a_i, b_i, c_i);
                //a_o <= T1 + T2;
                a_o <= h_i + S1(e_i) + Ch(e_i, f_i, g_i) + K_t + W_t + S0(a_i) + Ma(a_i, b_i, c_i);
                b_o <= a_i;
                c_o <= b_i;
                d_o <= c_i;
                //e_o <= d_i + T1;
                e_o <= d_i + h_i + S1(e_i) + Ch(e_i, f_i, g_i) + K_t + W_t;
                f_o <= e_i;
                g_o <= f_i;
                h_o <= g_i;
                out_valid <= 1;

                if (out_ready == 1) begin
                    phase <= IDLE;
                end
            end
        endcase
    end
end
endmodule
