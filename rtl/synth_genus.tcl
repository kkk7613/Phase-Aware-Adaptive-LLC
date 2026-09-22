# Cadence Genus Synthesis Script for Phase-Aware Adaptive LLC Controller
# Course: BEVD207L, VIT Chennai

set_db / .init_lib_search_path { . /cadence/libraries/lib }
set_db / .script_search_path  { . }

# Set target standard cell library (e.g. 45nm / 28nm)
# set_db library { slow_vdd1v0_basicCells.lib }

# Read SystemVerilog RTL files
read_hdl -language sv {
    phase_monitor.sv
    feature_extractor.sv
    rule_classifier.sv
    unified_llc_engine.sv
}

# Elaborate top-level design
elaborate unified_llc_engine

# Define 2.0 GHz Target Clock (500 ps period)
create_clock -name clk -period 0.5 [get_ports clk]
set_clock_uncertainty 0.05 [get_clocks clk]

# Constrain inputs and outputs
set_input_delay 0.1 -clock clk [all_inputs -no_clocks]
set_output_delay 0.1 -clock clk [all_outputs]

# Compile / Synthesize to target gates
syn_generic
syn_map
syn_opt

# Generate Area, Power, and Timing Reports
report_area   > reports/genus_area.rpt
report_power  > reports/genus_power.rpt
report_timing > reports/genus_timing.rpt
report_gates  > reports/genus_gates.rpt

puts "Cadence Genus Synthesis Completed Successfully!"\n