module round(
  input  wire         clk,
  input  wire         rst_n,

  input  wire [31:0]  a_i, b_i, c_i, d_i, e_i, f_i, g_i, h_i,
  input  wire [31:0]  K_t,
  input  wire [31:0]  W_t,
  input  wire         in_valid,
  output wire         in_ready,

  output reg  [31:0]  a_o, b_o, c_o, d_o, e_o, f_o, g_o, h_o,
  output reg          out_valid,
  input  wire         out_ready
);

// note: this version of the file has not been tested
// do not integrate with top level yet

reg [31:0] T1, T2;
reg [31:0] rt1, rt2;

localparam IDLE = 1'd0;
localparam COMP = 1'd1;
reg phase;

// i
function automatic [31:0] Ch(input [31:0] xi, input [31:0] yi, input [31:0] zi)
    begin
        Ch <= (xi and yi) xor ((not xi) and zi);
    end
endfunction

function automatic [31:0] Ma(input [31:0] xi, input [31:0] yi, input [31:0] zi)
    begin
        Ma <= (xi and yi) xor (xi and zi) xor (yi and zi);
    end
endfunction

function automatic [31:0] S0(input [31:0] xi)
    begin
        //rotr2x
        rt1[31:30] <= xi[1:0];
        rt1[29:0]  <= xi[31:2];

        //rotr13x
        rt2[31:19] <= xi[12:0];
        rt2[18:0]  <= xi[31:13];

        rt1 <= rt1 xor rt2;

        //rotr22x
        rt2[31:10] <= xi[21:0];
        rt2[9:0]   <= xi[31:22];

        S0 <= rt1 xor rt2;
    end
endfunction

function automatic [31:0] S1(input [31:0] xi)
    begin
        //rotr6x
        rt1[31:26] <= xi[5:0];
        rt1[25:0]  <= xi[31:6];

        //rotr11x
        rt2[31:21] <= xi[10:0];
        rt2[20:0]  <= xi[31:11];

        rt1 <= rt1 xor rt2;

        //rotr25x
        rt2[31:7] <= xi[24:0];
        rt2[6:0]   <= xi[31:25];

        S1 <= rt1 xor rt2;
    end
endfunction




always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        out_valid <= 0;
        in_ready <= 0;

    end

    else begin
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
                T1  <= h_i + S1(e_i) + Ch(e_i, f_i, g_i) + K_t + W_t;
                T2  <= S0(a_i) + Ma(a_i, b_i, c_i);
                a_o <= T1 + T2;
                b_o <= a_i;
                c_o <= b_i;
                d_o <= c_i;
                e_o <= d_i + T1;
                f_o <= e_i;
                g_o <= f_i;
                h_o <= g_i;
                out_valid <= 1;

                if (out_ready == 1) begin
                    phase <= IDLE;
                end
            end

end




endmodule