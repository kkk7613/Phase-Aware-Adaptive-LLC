#!/usr/bin/env python3
import subprocess
import re
import os
import sys
import json
import time

CHAMPSIM_DIR = "/home/kousika/ChampSim"
TRACE_FILE = "/home/kousika/traces/605.mcf_s-472B.champsimtrace.xz"
RESULTS_DIR = os.path.join(CHAMPSIM_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

WARMUP = int(sys.argv[1]) if len(sys.argv) > 1 else 1000000
SIM_INSTR = int(sys.argv[2]) if len(sys.argv) > 2 else 2000000

configs = [
    {"name": "LRU (Static)",           "bin": "bin/champsim_lru",     "env": {}},
    {"name": "SRRIP (Static)",         "bin": "bin/champsim_srrip",   "env": {}},
    {"name": "DRRIP (Set-Dueling)",    "bin": "bin/champsim_drrip",   "env": {}},
    {"name": "PA-RRIP (Epoch 5k)",     "bin": "bin/champsim_pa_rrip", "env": {"PA_EPOCH_CYCLES": "5000"}},
    {"name": "PA-RRIP (Epoch 10k)",    "bin": "bin/champsim_pa_rrip", "env": {"PA_EPOCH_CYCLES": "10000"}},
    {"name": "PA-RRIP (Epoch 20k)",    "bin": "bin/champsim_pa_rrip", "env": {"PA_EPOCH_CYCLES": "20000"}},
]

def parse_champsim_output(stdout):
    stats = {}
    
    # Cumulative IPC & cycles
    ipc_m = re.search(r"CPU 0 cumulative IPC:\s+([0-9.]+)\s+instructions:\s+([0-9]+)\s+cycles:\s+([0-9]+)", stdout)
    if ipc_m:
        stats["ipc"] = float(ipc_m.group(1))
        stats["instructions"] = int(ipc_m.group(2))
        stats["cycles"] = int(ipc_m.group(3))
    else:
        stats["ipc"] = 0.0
        stats["instructions"] = SIM_INSTR
        stats["cycles"] = 0

    # LLC stats
    llc_m = re.search(r"cpu0->LLC TOTAL\s+ACCESS:\s+([0-9]+)\s+HIT:\s+([0-9]+)\s+MISS:\s+([0-9]+)", stdout)
    if llc_m:
        accesses = int(llc_m.group(1))
        hits = int(llc_m.group(2))
        misses = int(llc_m.group(3))
        stats["llc_accesses"] = accesses
        stats["llc_hits"] = hits
        stats["llc_misses"] = misses
        stats["llc_hit_rate"] = (hits / accesses * 100.0) if accesses > 0 else 0.0
        stats["llc_mpki"] = (misses / (stats["instructions"] / 1000.0)) if stats["instructions"] > 0 else 0.0
    else:
        stats["llc_accesses"] = 0
        stats["llc_hits"] = 0
        stats["llc_misses"] = 0
        stats["llc_hit_rate"] = 0.0
        stats["llc_mpki"] = 0.0

    # Miss Latency
    lat_m = re.search(r"cpu0->LLC AVERAGE MISS LATENCY:\s+([0-9.]+)\s+cycles", stdout)
    stats["llc_miss_lat"] = float(lat_m.group(1)) if lat_m else 0.0

    # DRAM row buffer miss
    dram_m = re.search(r"Channel 0 RQ ROW_BUFFER_HIT:\s+([0-9]+)\s+ROW_BUFFER_MISS:\s+([0-9]+)", stdout)
    stats["dram_rq_miss"] = int(dram_m.group(2)) if dram_m else 0

    # PA-RRIP specific stats
    srrip_m = re.search(r"Mode 0 \(SRRIP\):\s+([0-9]+)\s+epochs\s+\(([0-9.]+)%\)", stdout)
    lru_m   = re.search(r"Mode 1 \(LRU\):\s+([0-9]+)\s+epochs\s+\(([0-9.]+)%\)", stdout)
    brrip_m = re.search(r"Mode 2 \(BRRIP\):\s+([0-9]+)\s+epochs\s+\(([0-9.]+)%\)", stdout)
    sw_m    = re.search(r"Policy Switches:\s+([0-9]+)", stdout)

    stats["pct_srrip"] = float(srrip_m.group(2)) if srrip_m else 0.0
    stats["pct_lru"]   = float(lru_m.group(2)) if lru_m else 0.0
    stats["pct_brrip"] = float(brrip_m.group(2)) if brrip_m else 0.0
    stats["switches"]  = int(sw_m.group(1)) if sw_m else 0

    return stats

results = []
print(f"================================================================================")
print(f"  PHASE-AWARE LLC EXPERIMENTAL EVALUATION HARNESS (Trace: 605.mcf_s)")
print(f"  Warmup: {WARMUP:,} instr | Detailed Simulation: {SIM_INSTR:,} instr")
print(f"================================================================================")

for cfg in configs:
    name = cfg["name"]
    bin_path = os.path.join(CHAMPSIM_DIR, cfg["bin"])
    cmd = [
        bin_path,
        "--warmup-instructions", str(WARMUP),
        "--simulation-instructions", str(SIM_INSTR),
        TRACE_FILE
    ]
    env = os.environ.copy()
    env.update(cfg["env"])

    print(f"[*] Running {name}...", end="", flush=True)
    t0 = time.time()
    res = subprocess.run(cmd, cwd=CHAMPSIM_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    elapsed = time.time() - t0

    if res.returncode != 0:
        print(f" FAILED (exit {res.returncode})\n{res.stderr}")
        continue

    st = parse_champsim_output(res.stdout)
    st["name"] = name
    st["elapsed_sec"] = elapsed
    results.append(st)
    print(f" DONE ({elapsed:.1f}s) -> IPC: {st['ipc']:.4f} | LLC Hit: {st['llc_hit_rate']:.2f}% | MPKI: {st['llc_mpki']:.2f}")

# Generate Markdown & CSV Tables
md_path = os.path.join(RESULTS_DIR, "benchmark_summary.md")
csv_path = os.path.join(RESULTS_DIR, "benchmark_summary.csv")

lru_ipc = results[0]["ipc"] if results else 1.0
lru_mpki = results[0]["llc_mpki"] if results else 1.0

with open(md_path, "w") as f_md, open(csv_path, "w") as f_csv:
    # Header
    f_md.write("# Experimental Evaluation: Phase-Aware Adaptive LLC Replacement\n\n")
    f_md.write(f"**Benchmark Trace:** `605.mcf_s-472B.champsimtrace.xz` (SPEC CPU2017 Memory Intensive)\n")
    f_md.write(f"**Configuration:** 2MB 16-way LLC, 2.0 GHz, 1-core OOO CPU, Warmup: {WARMUP:,} instr, Sim: {SIM_INSTR:,} instr\n\n")

    f_md.write("| Replacement Policy | IPC | LLC Hit Rate (%) | LLC MPKI | Avg Miss Latency (cyc) | Speedup vs LRU (%) | MPKI Reduction (%) | Dominant Mode |\n")
    f_md.write("|---|---|---|---|---|---|---|---|\n")

    f_csv.write("Policy,IPC,LLC_Hit_Rate,LLC_MPKI,Avg_Miss_Latency,Speedup_vs_LRU_pct,MPKI_Reduction_pct,Pct_SRRIP,Pct_LRU,Pct_BRRIP,Switches\n")

    for r in results:
        speedup = ((r["ipc"] - lru_ipc) / lru_ipc * 100.0) if lru_ipc > 0 else 0.0
        mpki_red = ((lru_mpki - r["llc_mpki"]) / lru_mpki * 100.0) if lru_mpki > 0 else 0.0
        
        dominant = "N/A (Fixed)"
        if "PA-RRIP" in r["name"]:
            dominant = f"BRRIP ({r['pct_brrip']:.1f}%)"

        f_md.write(f"| **{r['name']}** | {r['ipc']:.4f} | {r['llc_hit_rate']:.2f}% | {r['llc_mpki']:.2f} | {r['llc_miss_lat']:.1f} | {speedup:+.2f}% | {mpki_red:+.2f}% | {dominant} |\n")
        f_csv.write(f"{r['name']},{r['ipc']:.4f},{r['llc_hit_rate']:.2f},{r['llc_mpki']:.2f},{r['llc_miss_lat']:.1f},{speedup:+.2f},{mpki_red:+.2f},{r['pct_srrip']:.1f},{r['pct_lru']:.1f},{r['pct_brrip']:.1f},{r['switches']}\n")

print(f"\n[+] Saved summary table to {md_path}")
print(f"[+] Saved CSV data to {csv_path}")

# Print Table to console
print("\n" + open(md_path).read())
