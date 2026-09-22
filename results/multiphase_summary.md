# Dynamic Multi-Phase Adaptivity Benchmark Results

**Workload:** Multi-Phase Trace (Phase 1: Recency Working Set, Phase 2: Streaming Scan, Phase 3: Thrashing Pointer Chase)
**Instructions:** 200,000 Warmup + 3,800,000 Simulation

| Policy | IPC | LLC Hit Rate (%) | LLC Hits | LLC MPKI | Avg Miss Lat (cyc) | Policy Switches | Mode Breakdown |
|---|---|---|---|---|---|---|---|
| **LRU (Static Baseline)** | 0.1510 | 21.52% | 414,158 | 397.34 | 226.4 | 0 | Fixed (Mode 1) |
| **SRRIP (Static Baseline)** | 0.1515 | 22.14% | 425,975 | 394.30 | 225.8 | 0 | Fixed (Mode 0) |
| **DRRIP (Set-Dueling Baseline)** | 0.1529 | 23.07% | 444,065 | 389.59 | 224.9 | 0 | Fixed (Dueling) |
| **PA-RRIP (Phase-Aware)** | 0.1526 | 22.34% | 429,856 | 393.32 | 225.1 | 3 | SRRIP 45.5% / LRU 9.8% / BRRIP 44.7% |
