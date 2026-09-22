# Experimental Evaluation: Phase-Aware Adaptive LLC Replacement

**Benchmark Trace:** `605.mcf_s-472B.champsimtrace.xz` (SPEC CPU2017 Memory Intensive)
**Configuration:** 2MB 16-way LLC, 2.0 GHz, 1-core OOO CPU, Warmup: 1,000,000 instr, Sim: 2,000,000 instr

| Replacement Policy | IPC | LLC Hit Rate (%) | LLC MPKI | Avg Miss Latency (cyc) | Speedup vs LRU (%) | MPKI Reduction (%) | Dominant Mode |
|---|---|---|---|---|---|---|---|
| **LRU (Static)** | 0.2707 | 10.06% | 38.04 | 205.9 | +0.00% | +0.00% | N/A (Fixed) |
| **SRRIP (Static)** | 0.2742 | 6.36% | 39.60 | 193.8 | +1.29% | -4.11% | N/A (Fixed) |
| **DRRIP (Set-Dueling)** | 0.2713 | 9.59% | 38.24 | 203.9 | +0.22% | -0.52% | N/A (Fixed) |
| **PA-RRIP (Epoch 5k)** | 0.2808 | 7.60% | 39.08 | 193.5 | +3.73% | -2.74% | BRRIP (97.9%) |
| **PA-RRIP (Epoch 10k)** | 0.2812 | 7.62% | 39.07 | 193.3 | +3.88% | -2.71% | BRRIP (95.8%) |
| **PA-RRIP (Epoch 20k)** | 0.2810 | 7.60% | 39.08 | 193.4 | +3.80% | -2.74% | BRRIP (91.7%) |
