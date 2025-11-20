/*
    THIS FILE IS A COPY FROM THE SHA256_FUNCS BRANCH.
*/

module sha256_funcs(
  input  wire [31:0] x, y, z,
  output wire [31:0] Ch,      // (x & y) ^ (~x & z)
  output wire [31:0] Maj,     // (x & y) ^ (x & z) ^ (y & z)
  output wire [31:0] Sigma0,  // ROTR2 ^ ROTR13 ^ ROTR22
  output wire [31:0] Sigma1,  // ROTR6 ^ ROTR11 ^ ROTR25
  output wire [31:0] sigma0,  // ROTR7 ^ ROTR18 ^ SHR3
  output wire [31:0] sigma1   // ROTR17 ^ ROTR19 ^ SHR10
);

    function automatic [31:0] ROTR(input [31:0] x, input [4:0] n);
        begin
            ROTR = (x>>n) | (x<<(32-n));
        end
    endfunction

    function automatic [31:0] SHR(input [31:0] x, input [4:0] n);
        begin
            SHR = (x>>n);
        end
    endfunction

    assign Ch = (x & y) ^ (~x & z);
    assign Maj = (x & y) ^ (x & z) ^ (y & z);
    assign Sigma0 = ROTR(x, 2) ^ ROTR(x, 13) ^ ROTR(x, 22);
    assign Sigma1 = ROTR(x, 6) ^ ROTR(x, 11) ^ ROTR(x, 25);
    assign sigma0 = ROTR(x, 7) ^ ROTR(x, 18) ^ SHR(x, 3);
    assign sigma1 = ROTR(y, 17) ^ ROTR(y, 19) ^ SHR(y, 10);

endmodule
