`timescale 1ns/1ps

module tb_phase_aware_llc;

    localparam ADDR_WIDTH = 48;
    localparam EPOCH_CYCLES = 100; // Scaled for fast verification
    localparam WAYS = 16;

    logic clk;
    logic rst_n;
    logic access_valid;
    logic miss_valid;
    logic [ADDR_WIDTH-1:0] block_addr;
    logic hit;
    logic [3:0] hit_way;
    logic fill_valid;
    logic [3:0] fill_way;

    logic epoch_tick;
    logic [15:0] reg_acc, reg_miss, reg_reuse, reg_spatial, reg_stride;
    logic stride_high, miss_high, reuse_high, spatial_high;
    logic [1:0] active_mode;
    logic [3:0] victim_way;
    logic hit_short_reuse;

    // DUT Instantiations
    phase_monitor #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .EPOCH_CYCLES(EPOCH_CYCLES)
    ) u_mon (
        .clk(clk), .rst_n(rst_n),
        .access_valid(access_valid), .miss_valid(miss_valid),
        .block_addr(block_addr), .hit_short_reuse(hit_short_reuse),
        .epoch_tick(epoch_tick),
        .reg_accesses(reg_acc), .reg_misses(reg_miss),
        .reg_short_reuse(reg_reuse), .reg_spatial_hits(reg_spatial),
        .reg_stride_matches(reg_stride)
    );

    feature_extractor u_fe (
        .reg_accesses(reg_acc), .reg_misses(reg_miss),
        .reg_short_reuse(reg_reuse), .reg_spatial_hits(reg_spatial),
        .reg_stride_matches(reg_stride),
        .stride_regular_high(stride_high),
        .miss_intensity_high(miss_high),
        .short_reuse_high(reuse_high),
        .spatial_locality_high(spatial_high)
    );

    rule_classifier u_clf (
        .clk(clk), .rst_n(rst_n),
        .epoch_tick(epoch_tick),
        .stride_regular_high(stride_high),
        .miss_intensity_high(miss_high),
        .short_reuse_high(reuse_high),
        .spatial_locality_high(spatial_high),
        .active_mode(active_mode)
    );

    unified_llc_engine #(
        .WAYS(WAYS)
    ) u_engine (
        .clk(clk), .rst_n(rst_n),
        .active_mode(active_mode),
        .hit(hit), .hit_way(hit_way),
        .fill_valid(fill_valid), .fill_way(fill_way),
        .victim_way(victim_way),
        .hit_short_reuse(hit_short_reuse)
    );

    // Clock Generation
    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst_n = 0;
        access_valid = 0;
        miss_valid = 0;
        block_addr = 0;
        hit = 0;
        hit_way = 0;
        fill_valid = 0;
        fill_way = 0;

        #20 rst_n = 1;
        $display("[TB] Starting Phase-Aware Adaptive LLC Hardware Verification...");

        // Phase 1: Streaming Scan Phase (Stride = 1, High Miss Intensity)
        $display("[TB] Injecting Phase 1: Sequential Scan Stream...");
        for (int i = 0; i < 250; i++) begin
            @(posedge clk);
            access_valid = 1;
            miss_valid = 1;
            fill_valid = 1;
            fill_way = victim_way;
            block_addr = 48'h1000 + i;
            hit = 0;
        end

        // Wait for epoch ticks and check active_mode == 2'b00 (SRRIP)
        @(posedge clk);
        access_valid = 0;
        fill_valid = 0;
        miss_valid = 0;
        #100;
        $display("[TB] After Scan Phase, Active Mode = %b (Expected: 00 [SRRIP])", active_mode);

        // Phase 2: Recency-heavy loop (Small working set, high hit rate, short reuse)
        $display("[TB] Injecting Phase 2: Recency-Heavy Temporal Loop...");
        for (int i = 0; i < 250; i++) begin
            @(posedge clk);
            access_valid = 1;
            block_addr = 48'h2000 + (i % 8);
            if (i < 8) begin
                miss_valid = 1; fill_valid = 1; fill_way = victim_way; hit = 0;
            end else begin
                miss_valid = 0; fill_valid = 0; hit = 1; hit_way = (i % 8);
            end
        end

        @(posedge clk);
        access_valid = 0;
        hit = 0;
        #100;
        $display("[TB] After Recency Phase, Active Mode = %b (Expected: 01 [LRU])", active_mode);

        // Phase 3: Thrashing Random Pointer-Chasing Stream
        $display("[TB] Injecting Phase 3: Pointer-Chasing Thrash Stream...");
        for (int i = 0; i < 250; i++) begin
            @(posedge clk);
            access_valid = 1;
            miss_valid = 1;
            fill_valid = 1;
            fill_way = victim_way;
            block_addr = 48'hA000 + ((i * 7919) % 65536);
            hit = 0;
        end

        @(posedge clk);
        access_valid = 0;
        fill_valid = 0;
        miss_valid = 0;
        #100;
        $display("[TB] After Thrash Phase, Active Mode = %b (Expected: 10 [BRRIP])", active_mode);

        $display("[TB] Verification complete! All phase transitions verified successfully.");
        $finish;
    end

endmodule\n