module message_schedule(
  input  wire         clk,
  input  wire         rst_n,

  // Control
  input  wire         init,     // Load W[0..15] from block
  input  wire         shift,    // When t>=16: compute next W and slide window
  input  wire [5:0]   t,        // Current round index (0..63)

  // Data
  input  wire [511:0] block,    // Raw 512-bit block, big-endian bytes→words
  output reg  [31:0]  W_t,      // Word for current round
  output reg          valid     // High when W_t is valid
);


reg [31:0] W_window [15:0]; // 16*32 bit register sliding window
reg [31:0] W_window_new [15:0]; // To update values when window slides

reg [5:0] first_entry_idx; // Keep track of where window begins

// Driven high to update W_window with W_window_new after 
// W_window_new has been assigned appropriate values
reg W_window_write_enable; 

// To increment in loops
integer i;

//---------------Calculate/Slide W_window_new---------------//

wire [31:0] s0;
wire [31:0] s1;

// Instantiate sha256_funcs to obtain sigma0 and sigma1 values
sha256_funcs sha256_funcs_inst(
    .x(W_window[1]),
    .y(W_window[14]),

    .sigma0(s0),
    .sigma1(s1),

    // Intentionally left unconnected
    // because not needed for message schedule
    .z(0), // Input
    .Ch(),
    .Maj(),
    .Sigma0(),
    .Sigma1()
);

// To store index of actual window since directly
// indexing `t` would be beyond window size (16) at some point
reg [5:0] window_idx;

// Combinational logic
always @(*) begin

    window_idx = t - first_entry_idx;
    W_t = W_window[ window_idx[3:0] ];


    // Because the change is applied during the
    // next clock cycle, we need to check `t + 1`
    if (init && (t + 1 < 16)) begin

        for (i = 0; i < 16; i = i + 1) begin
            W_window_new[i] = block[(511 - 32*i) -: 32];
        end

        W_window_write_enable = 1;

    end else if (shift && (t + 1 >= 16)) begin

        // Slide window towards MSB
        for (i = 0; i < 15; i = i + 1) begin
            W_window_new[i] = W_window[i + 1];
        end

        // Unlike in test/gen_test_cases.py, no need to AND
        // with 0xffffffff because W_t is only 32 bits long
        W_window_new[15] = s0 + W_window[9] + s1 + W_window[0];

        W_window_write_enable = 1;

    end else begin

        // Default values to avoid inferring latches
        
        for (i = 0; i < 16; i = i + 1) begin
            W_window_new[i] = 32'b0;
        end 

        W_window_write_enable = 0;

    end
end

//-------------Update W_window with W_window_new--------------//

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        first_entry_idx <= 0;

        valid <= 0;

        for (i = 0; i < 16; i = i + 1) begin
            W_window[i] <= 32'b0;
        end

        // W_window_new, W_window_write_enable, and W_t driven by combinational logic

    end else if (W_window_write_enable) begin

        for (i = 0; i < 16; i = i + 1) begin
            W_window[i] <= W_window_new[i];
        end

        if ( t >= 16 ) begin
            first_entry_idx <= first_entry_idx + 1;
        end else if (t == 0) begin
            first_entry_idx <= 6'b0;
        end
        
        valid <= 1;

    end else begin
        valid <= 0;
    end
end

endmodule