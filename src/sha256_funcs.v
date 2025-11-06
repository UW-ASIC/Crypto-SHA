function [31:0] rotr;
  input [31:0] x;
  input [4:0] n;

  rotr = (x >> n) | (x << (32 - n));
endfunction

function [31:0] shr;
  input [31:0] x;
  input [4:0] n;

  shr = (x >> n);
endfunction

module sha256_funcs(
  input  wire [31:0] x, y, z,
  output wire [31:0] Ch,      // (x & y) ^ (~x & z)
  output wire [31:0] Maj,     // (x & y) ^ (x & z) ^ (y & z)
  output wire [31:0] Sigma0,  // ROTR2 ^ ROTR13 ^ ROTR22
  output wire [31:0] Sigma1,  // ROTR6 ^ ROTR11 ^ ROTR25
  output wire [31:0] sigma0,  // ROTR7 ^ ROTR18 ^ SHR3
  output wire [31:0] sigma1   // ROTR17 ^ ROTR19 ^ SHR10
);

  // Only implement sigma0 and sigma1 for 
  // sake of testing message_schedule
  //
  // Assuming `x` is W[t - 15] and 
  // `y` is W[t - 2]

  assign sigma0 = rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3);
  assign sigma1 = rotr(y, 17) ^ rotr(y, 19) ^ shr(y, 10);

  // Rest of outputs not used in message_schedule
  assign Sigma0 = 0;
  assign Sigma1 = 0;
  assign Ch = 0;
  assign Maj = 0;

endmodule