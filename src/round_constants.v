module round_constants(
    input  wire [6:0]  idx,     // 0..63
    output wire [31:0] K_t,     // round constant
    output wire [255:0] IV      // {H0,H1,...,H7}, big-endian word order
);

    reg [31:0] K_CONSTANTS [63:0];

    assign K_t = K_CONSTANTS[idx];
    assign IV = { 32'h6a09e667, 32'hbb67ae85, 32'h3c6ef372, 32'ha54ff53a,
                  32'h510e527f, 32'h9b05688c, 32'h1f83d9ab, 32'h5be0cd19 };

    initial begin
        K_CONSTANTS[0]   = 32'h428a2f98;
        K_CONSTANTS[1]   = 32'h71374491;
        K_CONSTANTS[2]   = 32'hb5c0fbcf;
        K_CONSTANTS[3]   = 32'he9b5dba5;
        K_CONSTANTS[4]   = 32'h3956c25b;
        K_CONSTANTS[5]   = 32'h59f111f1;
        K_CONSTANTS[6]   = 32'h923f82a4;
        K_CONSTANTS[7]   = 32'hab1c5ed5;

        K_CONSTANTS[8]   = 32'hd807aa98;
        K_CONSTANTS[9]   = 32'h12835b01;
        K_CONSTANTS[10]  = 32'h243185be;
        K_CONSTANTS[11]  = 32'h550c7dc3;
        K_CONSTANTS[12]  = 32'h72be5d74;
        K_CONSTANTS[13]  = 32'h80deb1fe;
        K_CONSTANTS[14]  = 32'h9bdc06a7;
        K_CONSTANTS[15]  = 32'hc19bf174;

        K_CONSTANTS[16]  = 32'he49b69c1;
        K_CONSTANTS[17]  = 32'hefbe4786;
        K_CONSTANTS[18]  = 32'h0fc19dc6;
        K_CONSTANTS[19]  = 32'h240ca1cc;
        K_CONSTANTS[20]  = 32'h2de92c6f;
        K_CONSTANTS[21]  = 32'h4a7484aa;
        K_CONSTANTS[22]  = 32'h5cb0a9dc;
        K_CONSTANTS[23]  = 32'h76f988da;

        K_CONSTANTS[24]  = 32'h983e5152;
        K_CONSTANTS[25]  = 32'ha831c66d;
        K_CONSTANTS[26]  = 32'hb00327c8;
        K_CONSTANTS[27]  = 32'hbf597fc7;
        K_CONSTANTS[28]  = 32'hc6e00bf3;
        K_CONSTANTS[29]  = 32'hd5a79147;
        K_CONSTANTS[30]  = 32'h06ca6351;
        K_CONSTANTS[31]  = 32'h14292967;

        K_CONSTANTS[32]  = 32'h27b70a85;
        K_CONSTANTS[33]  = 32'h2e1b2138;
        K_CONSTANTS[34]  = 32'h4d2c6dfc;
        K_CONSTANTS[35]  = 32'h53380d13;
        K_CONSTANTS[36]  = 32'h650a7354;
        K_CONSTANTS[37]  = 32'h766a0abb;
        K_CONSTANTS[38]  = 32'h81c2c92e;
        K_CONSTANTS[39]  = 32'h92722c85;

        K_CONSTANTS[40]  = 32'ha2bfe8a1;
        K_CONSTANTS[41]  = 32'ha81a664b;
        K_CONSTANTS[42]  = 32'hc24b8b70;
        K_CONSTANTS[43]  = 32'hc76c51a3;
        K_CONSTANTS[44]  = 32'hd192e819;
        K_CONSTANTS[45]  = 32'hd6990624;
        K_CONSTANTS[46]  = 32'hf40e3585;
        K_CONSTANTS[47]  = 32'h106aa070;

        K_CONSTANTS[48]  = 32'h19a4c116;
        K_CONSTANTS[49]  = 32'h1e376c08;
        K_CONSTANTS[50]  = 32'h2748774c;
        K_CONSTANTS[51]  = 32'h34b0bcb5;
        K_CONSTANTS[52]  = 32'h391c0cb3;
        K_CONSTANTS[53]  = 32'h4ed8aa4a;
        K_CONSTANTS[54]  = 32'h5b9cca4f;
        K_CONSTANTS[55]  = 32'h682e6ff3;

        K_CONSTANTS[56]  = 32'h748f82ee;
        K_CONSTANTS[57]  = 32'h78a5636f;
        K_CONSTANTS[58]  = 32'h84c87814;
        K_CONSTANTS[59]  = 32'h8cc70208;
        K_CONSTANTS[60]  = 32'h90befffa;
        K_CONSTANTS[61]  = 32'ha4506ceb;
        K_CONSTANTS[62]  = 32'hbef9a3f7;
        K_CONSTANTS[63]  = 32'hc67178f2;
    end

endmodule