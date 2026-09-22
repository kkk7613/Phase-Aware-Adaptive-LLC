`timescale 1ns/1ps

module phase_monitor #(
    parameter ADDR_WIDTH = 48,
    parameter EPOCH_CYCLES = 10000,
    parameter ACC_WIDTH = 16
)(
    input  logic                   clk,
    input  logic                   rst_n,
    input  logic                   access_valid,
    input  logic                   miss_valid,
    input  logic [ADDR_WIDTH-1:0]  block_addr,
    input  logic                   hit_short_reuse,

    output logic                   epoch_tick,
    output logic [ACC_WIDTH-1:0]   reg_accesses,
    output logic [ACC_WIDTH-1:0]   reg_misses,
    output logic [ACC_WIDTH-1:0]   reg_short_reuse,
    output logic [ACC_WIDTH-1:0]   reg_spatial_hits,
    output logic [ACC_WIDTH-1:0]   reg_stride_matches
);

    logic [31:0] cycle_cnt;
    logic [ACC_WIDTH-1:0] acc_cnt;
    logic [ACC_WIDTH-1:0] miss_cnt;
    logic [ACC_WIDTH-1:0] reuse_cnt;
    logic [ACC_WIDTH-1:0] spatial_cnt;
    logic [ACC_WIDTH-1:0] stride_cnt;

    logic [ADDR_WIDTH-1:0] last_addr;
    logic signed [31:0]    last_stride;
    logic signed [31:0]    curr_stride;

    wire is_same_page = (block_addr[ADDR_WIDTH-1:6] == last_addr[ADDR_WIDTH-1:6]);
    wire is_adjacent  = (curr_stride == 1) || (curr_stride == -1);

    always_comb begin
        curr_stride = $signed(block_addr[31:0]) - $signed(last_addr[31:0]);
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cycle_cnt           <= 32'd0;
            acc_cnt             <= '0;
            miss_cnt            <= '0;
            reuse_cnt           <= '0;
            spatial_cnt         <= '0;
            stride_cnt          <= '0;
            last_addr           <= '0;
            last_stride         <= 32'd0;
            epoch_tick          <= 1'b0;
            reg_accesses        <= '0;
            reg_misses          <= '0;
            reg_short_reuse     <= '0;
            reg_spatial_hits    <= '0;
            reg_stride_matches  <= '0;
        end else begin
            if (cycle_cnt >= EPOCH_CYCLES - 1) begin
                cycle_cnt <= 32'd0;
                epoch_tick <= 1'b1;

                // Latch epoch statistics into registers for feature extraction
                reg_accesses       <= acc_cnt;
                reg_misses         <= miss_cnt;
                reg_short_reuse    <= reuse_cnt;
                reg_spatial_hits   <= spatial_cnt;
                reg_stride_matches <= stride_cnt;

                // Clear live counters
                acc_cnt     <= '0;
                miss_cnt    <= '0;
                reuse_cnt   <= '0;
                spatial_cnt <= '0;
                stride_cnt  <= '0;
            end else begin
                cycle_cnt <= cycle_cnt + 1'b1;
                epoch_tick <= 1'b0;

                if (access_valid) begin
                    acc_cnt <= acc_cnt + 1'b1;
                    if (miss_valid) begin
                        miss_cnt <= miss_cnt + 1'b1;
                    end
                    if (hit_short_reuse) begin
                        reuse_cnt <= reuse_cnt + 1'b1;
                    end

                    if (last_addr != '0) begin
                        if ((curr_stride == last_stride) && (curr_stride != 0)) begin
                            stride_cnt <= stride_cnt + 1'b1;
                        end
                        if (is_same_page || is_adjacent) begin
                            spatial_cnt <= spatial_cnt + 1'b1;
                        end
                    end
                    last_stride <= curr_stride;
                    last_addr   <= block_addr;
                end
            end
        end
    end

endmodule\n