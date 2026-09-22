`timescale 1ns/1ps

module unified_llc_engine #(
    parameter WAYS = 16,
    parameter WAY_WIDTH = 4,
    parameter RRPV_WIDTH = 2
)(
    input  logic                   clk,
    input  logic                   rst_n,
    input  logic [1:0]             active_mode, // 00: SRRIP, 01: LRU, 10: BRRIP
    input  logic                   hit,
    input  logic [WAY_WIDTH-1:0]   hit_way,
    input  logic                   fill_valid,
    input  logic [WAY_WIDTH-1:0]   fill_way,

    output logic [WAY_WIDTH-1:0]   victim_way,
    output logic                   hit_short_reuse
);

    localparam [RRPV_WIDTH-1:0] MAX_RRPV = 2'b11; // 3

    logic [RRPV_WIDTH-1:0] rrpv [WAYS-1:0];
    logic [4:0]            bimodal_cnt;

    // Check short reuse (hit on RRPV <= 1)
    assign hit_short_reuse = hit && (rrpv[hit_way] <= 2'b01);

    // Victim Search & Priority Aging Logic
    logic [WAY_WIDTH-1:0] max_way;
    logic [RRPV_WIDTH-1:0] max_val;
    logic [RRPV_WIDTH-1:0] age_diff;

    always_comb begin
        max_way = '0;
        max_val = rrpv[0];
        for (int w = 1; w < WAYS; w++) begin
            if (rrpv[w] > max_val) begin
                max_val = rrpv[w];
                max_way = w[WAY_WIDTH-1:0];
            end
        end
        victim_way = max_way;
        age_diff = MAX_RRPV - max_val;
    end

    // Sequential Update
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int w = 0; w < WAYS; w++) begin
                rrpv[w] <= MAX_RRPV;
            end
            bimodal_cnt <= 5'd0;
        end else begin
            // Hit update: promote to MRU (0)
            if (hit) begin
                rrpv[hit_way] <= 2'b00;
            end
            // Fill update: steer insertion RRPV based on active_mode
            else if (fill_valid) begin
                // Age ways if needed to find victim
                for (int w = 0; w < WAYS; w++) begin
                    if (w == fill_way) begin
                        case (active_mode)
                            2'b00: rrpv[w] <= 2'b10; // Mode 0 (SRRIP): RRPV = 2
                            2'b01: rrpv[w] <= 2'b00; // Mode 1 (LRU): MRU insertion
                            2'b10: begin            // Mode 2 (BRRIP): Bimodal insertion
                                if (bimodal_cnt == 5'd31) begin
                                    rrpv[w] <= 2'b10; // 1/32 RRPV = 2
                                    bimodal_cnt <= 5'd0;
                                end else begin
                                    rrpv[w] <= 2'b11; // 31/32 RRPV = 3
                                    bimodal_cnt <= bimodal_cnt + 1'b1;
                                end
                            end
                            default: rrpv[w] <= 2'b10;
                        endcase
                    end else begin
                        if (rrpv[w] + age_diff <= MAX_RRPV)
                            rrpv[w] <= rrpv[w] + age_diff;
                        else
                            rrpv[w] <= MAX_RRPV;
                    end
                end
            end
        end
    end

endmodule\n