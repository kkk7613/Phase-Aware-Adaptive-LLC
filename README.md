# Phase-Aware Adaptive Last-Level Cache (LLC) Replacement Framework
  
- **S M Kousika** 

---

## 1. Overview & Key Contributions

Modern memory workloads exhibit dynamic phase shifts between **streaming scans**, **temporal recency loops**, and **thrashing pointer-chasing**. Static cache replacement policies (LRU, SRRIP) and set-dueling policies (DRRIP) suffer from either single-policy rigidity, set-pollution overhead, or slow reaction lag.

This repository implements a **Phase-Aware Adaptive LLC Replacement (PA-RRIP)** framework comprising:
1. **Background Phase Monitor:** Continuously tracks 5 hardware-friendly runtime signatures (Miss Intensity, Stride Regularity, Spatial Locality, Short-Reuse Ratio, and Access Frequency) across epoch windows.
2. **Unified 2-bit RRPV Engine:** Dynamically steers cache insertions into one of three operating modes without any per-line storage overhead:
   - **Mode 0 (SRRIP):** Scan/Streaming resistance (=2$).
   - **Mode 1 (LRU-Approximated):** Recency protection (=0$).
   - **Mode 2 (BRRIP):** Thrashing resistance (=3$ with /32$ probability of =2$).
3. **Anti-Flapping Hysteresis Filter:** Employs a 2-bit saturating counter requiring 2 consecutive confirming epochs before triggering a policy switch, completely eliminating ping-pong instability.
4. **Zero-Migration Switching:** Mode transitions take effect immediately on subsequent fills without flushing or invalidating existing cache lines.
5. **Synthesizable SystemVerilog RTL:** Complete, verified RTL suite (
tl/) with Cadence Genus synthesis script constrained at 2.0 GHz ($<45$ NAND2 equivalent gates).

---

## 2. Experimental Results

### Workload A: Single-Phase Thrashing (SPEC CPU2017 605.mcf_s-472B)
*Configuration: 2MB 16-Way Shared LLC, 1-core OOO CPU @ 4.0 GHz, DRAM 3200 MT/s, 1M Warmup + 2M Sim*

| Replacement Policy | IPC | LLC Hit Rate (%) | LLC MPKI | Avg Miss Latency (cyc) | Speedup vs LRU (%) | Dominant Mode |
|---|---|---|---|---|---|---|
| **LRU (Static Baseline)** | 0.2707 | 10.06% | 38.04 | 205.9 | — | N/A (Fixed) |
| **SRRIP (Static Baseline)** | 0.2742 | 6.36% | 39.60 | 193.8 | +1.29% | N/A (Fixed) |
| **DRRIP (Set-Dueling Baseline)**| 0.2713 | 9.59% | 38.24 | 203.9 | +0.22% | N/A (Fixed) |
| **PA-RRIP (Epoch = 5,000 cyc)** | 0.2808 | 7.60% | 39.08 | 193.5 | +3.73% | BRRIP (97.9%) |
| **PA-RRIP (Epoch = 10,000 cyc)**| **0.2812** | **7.62%** | **39.07** | **193.3** | **+3.88%** | **BRRIP (95.8%)** |
| **PA-RRIP (Epoch = 20,000 cyc)**| 0.2810 | 7.60% | 39.08 | 193.4 | +3.80% | BRRIP (91.7%) |

> **Key Finding:** On sustained thrashing, PA-RRIP outperforms DRRIP by **+3.65%** (.2812$ vs .2713$) because PA-RRIP operates across 100% of cache sets without dedicated set-dueling pollution.

---

### Workload B: Multi-Phase Dynamic Transition Benchmark
*Stress-test alternating across Phase 1 (1.2MB Recency Loop) $
ightarrow$ Phase 2 (16MB Streaming Scan) $
ightarrow$ Phase 3 (32MB Pointer Chase).*

| Policy | Epoch Length | IPC | LLC Hit Rate (%) | LLC Hits | LLC MPKI | Switches | Mode Breakdown |
|---|---|---|---|---|---|---|---|
| **LRU (Static Baseline)** | — | 0.1510 | 21.52% | 414,158 | 397.34 | 0 | Fixed (Mode 1) |
| **SRRIP (Static Baseline)** | — | 0.1515 | 22.14% | 425,975 | 394.30 | 0 | Fixed (Mode 0) |
| **PA-RRIP (Epoch 2.5k)** | 2,500 cyc | 0.1518 | 21.88% | 421,005 | 395.48 | 3 | SRRIP 45.3% / LRU 9.6% / BRRIP 45.2% |
| **PA-RRIP (Epoch 10k)** | 10,000 cyc | 0.1526 | 22.34% | 429,856 | 393.32 | 3 | SRRIP 45.5% / LRU 9.8% / BRRIP 44.7% |
| **DRRIP (Set-Dueling)** | Continuous | **0.1529** | **23.07%** | **444,065** | **389.59** | Continuous | Dynamic Duel |

> **Architectural Trade-Off Finding:**  
> - Continuous set-dueling (DRRIP) excels at abrupt cliff-edge phase boundaries due to cycle-by-cycle PSEL feedback.  
> - Periodic classification (PA-RRIP) avoids set-pollution penalties on steady-state phases and covers three policies (including LRU for working sets), with 	ext{k}$ cycles identified as the optimal balance between sampling stability and phase responsiveness.

---

## 3. Directory Structure



---

## 4. How to Build & Run

### 1. Build ChampSim with PA-RRIP


### 2. Run Single-Phase MCF Benchmark Sweep


### 3. Generate & Run Dynamic Multi-Phase Benchmark


### 4. Train & Extract Decision Tree Rules

