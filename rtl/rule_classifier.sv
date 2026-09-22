`timescale 1ns/1ps

module rule_classifier (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       epoch_tick,
    input  logic       stride_regular_high,
    input  logic       miss_intensity_high,
    input  logic       short_reuse_high,
    input  logic       spatial_locality_high,

    output logic [1:0] active_mode // 2'b00: SRRIP, 2'b01: LRU, 2'b10: BRRIP
);

    localparam MODE_SRRIP = 2'b00;
    localparam MODE_LRU   = 2'b01;
    localparam MODE_BRRIP = 2'b10;

    logic [1:0] candidate_mode;
    logic [1:0] pending_mode;
    logic [1:0] consec_cnt;

    // Combinational Decision Tree
    always_comb begin
        if (stride_regular_high && miss_intensity_high) begin
            candidate_mode = MODE_SRRIP; // Scan/Streaming
        end else if (short_reuse_high || (spatial_locality_high && !miss_intensity_high)) begin
            candidate_mode = MODE_LRU;   // Recency-heavy
        end else begin
            candidate_mode = MODE_BRRIP; // Thrashing / Pointer-chasing
        end
    end

    // 2-bit Saturating Hysteresis Filter
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active_mode  <= MODE_SRRIP;
            pending_mode <= MODE_SRRIP;
            consec_cnt   <= 2'd0;
        end else if (epoch_tick) begin
            if (candidate_mode == pending_mode) begin
                if (consec_cnt < 2'd3) begin
                    consec_cnt <= consec_cnt + 1'b1;
                end
                // Switch mode if stable for >= 2 epochs
                if (consec_cnt >= 2'd1) begin
                    active_mode <= candidate_mode;
                end
            end else begin
                pending_mode <= candidate_mode;
                consec_cnt   <= 2'd0;
            end
        end
    end

endmodule\n