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


endmodule