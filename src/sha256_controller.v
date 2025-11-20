`default_nettype none
`include "sha256_funcs.v"


module sha256_controller(
  input  wire         clk,
  input  wire         rst_n,

  // Block input (pre-padded 512b)
  input  wire         blk_valid,
  output wire         blk_ready,
  input  wire [511:0] blk_data,
  input  wire         start_new_msg,  // reinit H to IV at message start

  // Digest output (asserted after last block processed)
  output reg          digest_valid,
  input  wire         digest_ready,
  output reg  [255:0] digest,

  // Status
  output reg          busy
);

    // Hash Setup
    localparam H0_0 = 32'h6a09e667;
    localparam H1_0 = 32'hbb67ae85;
    localparam H2_0 = 32'h3c6ef372;
    localparam H3_0 = 32'ha54ff53a;
    localparam H4_0 = 32'h510e527f;
    localparam H5_0 = 32'h9b05688c;
    localparam H6_0 = 32'h1f83d9ab;
    localparam H7_0 = 32'h5be0cd19;
    reg [31:0] H [7:0];
    wire [31:0] H_next [7:0];

    reg[31:0] a, b, c, d, e, f, g, h;
    wire[31:0] a_next, b_next, c_next, d_next, e_next, f_next, g_next, h_next;

    initial begin
      H[0] = H0_0;  H[1] = H1_0;   H[2] = H2_0;   H[3] = H3_0;
      H[4] = H4_0;  H[5] = H5_0;   H[6] = H6_0;   H[7] = H7_0;

      a = H0_0;  b = H1_0;   c = H2_0;   d = H3_0;
      e = H4_0;  f = H5_0;   g = H6_0;   h = H7_0;
    end


    // Reg Setup:
    
    wire [31:0] T1, T2;
    reg [7:0] t;


    // WORD SETUP ----------------------------------------
    reg [2047:0] W;
    wire [31:0] 
      W_t, 
      W_t_next,
      W_t_minus_2, 
      W_t_minus_7, 
      W_t_minus_15, 
      W_t_minus_16;

    // Function Setup
    wire [31:0]sigma1_t_minus_2;
    sha256_funcs sigma1(
      .x (32'h0),
      .y (W_t_minus_2),
      .z (32'h0),
      .Ch (),
      .Maj (),
      .Sigma0 (),
      .Sigma1 (),
      .sigma0 (),
      .sigma1 (sigma1_t_minus_2)
    );
    
    wire [31:0]sigma0_t_minus_15;
    sha256_funcs sigma0(
      .x (W_t_minus_15),
      .y (32'h0),
      .z (32'h0),
      .Ch (),
      .Maj (),
      .Sigma0 (),
      .Sigma1 (),
      .sigma0 (sigma0_t_minus_15),
      .sigma1 ()
    );

    wire [31:0]Sigma1_e;
    sha256_funcs Sigma1(
      .x (e),
      .y (32'h0),
      .z (32'h0),
      .Ch (),
      .Maj (),
      .Sigma0 (),
      .Sigma1 (Sigma1_e),
      .sigma0 (),
      .sigma1 ()
    );

    wire [31:0]Sigma0_a;
    sha256_funcs Sigma0(
      .x (a),
      .y (32'h0),
      .z (32'h0),
      .Ch (),
      .Maj (),
      .Sigma0 (Sigma0_a),
      .Sigma1 (),
      .sigma0 (),
      .sigma1 ()
    );

    wire [31:0]Ch_e_f_g;
    sha256_funcs Ch(
      .x (e),
      .y (f),
      .z (g),
      .Ch (Ch_e_f_g),
      .Maj (),
      .Sigma0 (),
      .Sigma1 (),
      .sigma0 (),
      .sigma1 ()
    );

    wire [31:0]Maj_a_b_c;
    sha256_funcs Maj(
      .x (a),
      .y (b),
      .z (c),
      .Ch (),
      .Maj (Maj_a_b_c),
      .Sigma0 (),
      .Sigma1 (),
      .sigma0 (),
      .sigma1 ()
    );
    // ----------------------------------------------------


    /* =================================================================
       =============================== FSM ============================= 
       ================================================================= */ 

    // next state logic
    assign W_t_next = sigma1_t_minus_2 + W_t_minus_7 + sigma0_t_minus_15 + W_t_minus_16;

    wire [31:0] k_t;  // how do i calculate k?
    assign T1 = h + Sigma1_e + Ch_e_f_g + k_t + W[(32*t) +: 32];
    assign T2 = Sigma0_a + Maj_a_b_c;
    assign h_next = g;
    assign g_next = f;
    assign f_next = e;
    assign e_next = d + T1;
    assign d_next = c;
    assign c_next = b;
    assign b_next = a;
    assign a_next = T1 + T2;

    assign H_next[0] = a + H[0];
    assign H_next[1] = b + H[1];
    assign H_next[2] = c + H[2];
    assign H_next[3] = d + H[3];
    assign H_next[4] = e + H[4];
    assign H_next[5] = f + H[5];
    assign H_next[6] = g + H[6];
    assign H_next[7] = h + H[7];
    


    // state update
    always@(posedge clk, negedge rst_n) begin
      if (!rst_n) begin
        t <= 8'd0;
        // reset  conditions
      end else  begin


        // Word Assigning -------------
        if (t < 8'd16) begin
          W[(t*32) +: 32] <= blk_data[(t*32) +: 32];
        end else  begin
          W[(t*32) +: 32] <= W_t_next;
        end

        // Letter Updates -------------
        a <= a_next;
        b <= b_next;
        c <= c_next;
        d <= d_next;
        e <= e_next;
        f <= f_next;
        g <= g_next;
        h <= h_next;

        // Hash Value Update ----------
        H[0] = H_next[0];
        H[1] = H_next[1];
        H[2] = H_next[2];
        H[3] = H_next[3];
        H[4] = H_next[4];
        H[5] = H_next[5];
        H[6] = H_next[6];
        H[7] = H_next[7];

        // Increment t ----------------
        t <= t + 1;

      end

    end

    // assignments



endmodule