module message_schedule(
  input  wire         clk,
  input  wire         rst_n,

  // Control
  input  wire         init,     // Pulse to load W[0..15] from block
  input  wire         shift,    // For t>=15: compute W[t+1] and slide window
  input  wire [5:0]   t,        // Current round index (0..63)

  // Data
  input  wire [255:0] msg_block,  // 8×32-bit message, big-endian
  output reg  [31:0]  W_t,      // Word for current round t
  output reg          valid     // High when W_t is meaningful (after init)
);

  // 16-word sliding window
  // For t >= 15, invariant: W_window[i] = W[t-15+i]
  reg [31:0] W_window [0:15];

  // Flag that we've done init and window holds valid data
  reg initialized;

  integer i;

  // --------------------------------------------------------
  // σ0, σ1 computation for message schedule
  // Using the "look-ahead" formula for W[t+1]:
  //   W[t+1] = σ1(W[t-1]) + W[t-6] + σ0(W[t-14]) + W[t-15]
  // which maps to W_window indices:
  //   W[t-15] -> W_window[0]
  //   W[t-14] -> W_window[1]
  //   W[t-6]  -> W_window[9]
  //   W[t-1]  -> W_window[14]
  // --------------------------------------------------------

    function automatic [31:0] rotr(input [31:0] x, input integer n);
    rotr = (x >> n) | (x << (32-n));
    endfunction

    function automatic [31:0] sigma0(input [31:0] x);
    sigma0 = rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3);
    endfunction

    function automatic [31:0] sigma1(input [31:0] x);
    sigma1 = rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10);
    endfunction

    wire [31:0] s0 = sigma0(W_window[1]);
    wire [31:0] s1 = sigma1(W_window[14]);


  // Next word to append at tail: W[t+1]
  wire [31:0] W_next = s1 + W_window[9] + s0 + W_window[0];

  // --------------------------------------------------------
  // Combinational "next" values for W_t and valid
  // --------------------------------------------------------

  reg  [3:0]  read_idx;
  reg  [31:0] W_t_next;
  reg         valid_next;

  always @(*) begin
    if (!initialized) begin
      // Not initialized yet: no valid output
      read_idx   = 4'd0;
      W_t_next   = 32'b0;
      valid_next = 1'b0;
    end else begin
      // Once initialized, window holds W[0..15] at first.
      // For t < 16, W_t = W[t] = W_window[t]
      // For t >= 16, W_t = W[t] = W_window[15] (tail of sliding window)
      if (t < 16)
        read_idx = t[3:0];
      else
        read_idx = 4'd15;

      W_t_next   = W_window[read_idx];
      valid_next = 1'b1;  // Window initialized ⇒ W_t is meaningful for any 0..63
    end
  end

  // --------------------------------------------------------
  // Sequential state updates:
  //   - Load initial window from block on init
  //   - Slide window + append W_next when shift asserted for t >= 15
  //   - Register W_t and valid (so they line up cleanly with t)
  // --------------------------------------------------------

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      initialized <= 1'b0;
      W_t         <= 32'b0;
      valid       <= 1'b0;

      for (i = 0; i < 16; i = i + 1)
        W_window[i] <= 32'b0;

    end else begin
      // Register outputs *before* mutating the window
      W_t   <= W_t_next;
      valid <= valid_next;

      // Load initial W[0..15] from the 512-bit block
    if (init) begin
        // W[0..7] from 256-bit message block
        W_window[0] <= msg_block[255:224];
        W_window[1] <= msg_block[223:192];
        W_window[2] <= msg_block[191:160];
        W_window[3] <= msg_block[159:128];
        W_window[4] <= msg_block[127:96];
        W_window[5] <= msg_block[95:64];
        W_window[6] <= msg_block[63:32];
        W_window[7] <= msg_block[31:0];

        // Fixed padding for a 256-bit message
        W_window[8]  <= 32'h8000_0000;
        W_window[9]  <= 32'h0000_0000;
        W_window[10] <= 32'h0000_0000;
        W_window[11] <= 32'h0000_0000;
        W_window[12] <= 32'h0000_0000;
        W_window[13] <= 32'h0000_0000;
        W_window[14] <= 32'h0000_0000;
        W_window[15] <= 32'h0000_0100; // 256 bits

        initialized <= 1'b1;
      end else if (initialized && shift && (t >= 6'd15) && (t < 6'd63)) begin
        // Ignore shift before init.
        // First shift at t = 15 generates W[16] for t = 16.
        // Stop at t = 62 so we generate up to W[63] (t+1 = 63).

        // Slide window left: drop oldest word, shift others up
        for (i = 0; i < 15; i = i + 1) begin
          W_window[i] <= W_window[i+1];
        end

        // Append newly computed W[t+1] at the tail
        W_window[15] <= W_next;
      end
    end
  end

endmodule
