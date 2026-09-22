`timescale 1ns/1ps

module feature_extractor #(
    parameter ACC_WIDTH = 16
)(
    input  logic [ACC_WIDTH-1:0] reg_accesses,
    input  logic [ACC_WIDTH-1:0] reg_misses,
    input  logic [ACC_WIDTH-1:0] reg_short_reuse,
    input  logic [ACC_WIDTH-1:0] reg_spatial_hits,
    input  logic [ACC_WIDTH-1:0] reg_stride_matches,

    output logic                 stride_regular_high, // Stride match >= 40%
    output logic                 miss_intensity_high, // Miss intensity >= 50%
    output logic                 short_reuse_high,    // Short reuse >= 20%
    output logic                 spatial_locality_high// Spatial hits >= 35%
);

    // Multiplications by small constants to implement fixed-point comparator thresholds:
    // (stride * 5 >= acc * 2)  <=> stride/acc >= 0.40
    // (miss * 2 >= acc * 1)    <=> miss/acc >= 0.50
    // (reuse * 5 >= acc * 1)   <=> reuse/acc >= 0.20
    // (spatial * 20 >= acc * 7)<=> spatial/acc >= 0.35

    logic [ACC_WIDTH+3:0] stride_x5;
    logic [ACC_WIDTH+3:0] acc_x2;

    logic [ACC_WIDTH+3:0] miss_x2;
    logic [ACC_WIDTH+3:0] acc_x1;

    logic [ACC_WIDTH+3:0] reuse_x5;

    logic [ACC_WIDTH+5:0] spatial_x20;
    logic [ACC_WIDTH+5:0] acc_x7;

    always_comb begin
        stride_x5   = (reg_stride_matches << 2) + reg_stride_matches;
        acc_x2      = (reg_accesses << 1);

        miss_x2     = (reg_misses << 1);
        acc_x1      = reg_accesses;

        reuse_x5    = (reg_short_reuse << 2) + reg_short_reuse;

        spatial_x20 = (reg_spatial_hits << 4) + (reg_spatial_hits << 2);
        acc_x7      = (reg_accesses << 3) - reg_accesses;

        stride_regular_high   = (reg_accesses >= 16'd10) && (stride_x5 >= acc_x2);
        miss_intensity_high   = (reg_accesses >= 16'd10) && (miss_x2 >= acc_x1);
        short_reuse_high      = (reg_accesses >= 16'd10) && (reuse_x5 >= acc_x1);
        spatial_locality_high = (reg_accesses >= 16'd10) && (spatial_x20 >= acc_x7);
    end

endmodule\n