# Phase-Aware Adaptive Last-Level Cache Replacement with Unified 2-Bit RRPV States and Zero-Migration Overhead

**S M Kousika** (Reg. No: 24BVD1034) and **Kavya Raja G** (Reg. No: 24BVD1099)  
*School of Electronics Engineering (SENSE), Vellore Institute of Technology (VIT), Chennai Campus*  
*Course: BEVD207L — Computer Architecture (IEEE Digital Assignment)*  

---

## Abstract
As the gap between processor clock frequencies and main memory access latency widens, the Last-Level Cache (LLC) plays a decisive role in sustaining instruction throughput in modern computing systems. However, conventional replacement policies fail to adapt across dynamic program phases: Least Recently Used (LRU) collapses under memory thrashing and sequential scans, Static Re-Reference Interval Prediction (SRRIP) degrades under temporal recency loops, and Dynamic RRIP (DRRIP) incurs dedicated set-pollution overhead through static set-dueling. 

This paper proposes **PA-RRIP (Phase-Aware Adaptive RRIP)**, a hardware-efficient cache replacement framework that dynamically identifies macroscopic memory access behaviors and steers cache line insertions into scan-resistant (SRRIP), recency-protecting (LRU), or thrashing-resistant (BRRIP) policies. Crucially, PA-RRIP unifies all three operating modes onto the standard 2-bit RRPV metadata structure, introducing zero per-line storage overhead and enabling instantaneous, zero-migration policy transitions. Microarchitectural phase classification is driven by five lightweight runtime features and a 2-bit saturating hysteresis filter that completely eliminates policy flapping. 

Evaluated on the cycle-accurate ChampSim simulator under the memory-intensive SPEC CPU2017 `605.mcf` benchmark, PA-RRIP achieves an **IPC speedup of +3.88% over LRU, +2.55% over SRRIP, and +3.65% over DRRIP**, reducing average LLC miss latency by **12.6 cycles per miss**. On a multi-phase dynamic stress benchmark, PA-RRIP exercises all three policies (SRRIP 45.5%, LRU 9.8%, BRRIP 44.7%) with only three clean transitions across 501 epochs. Complete synthesizable SystemVerilog RTL modules synthesize under a **2.0 GHz clock constraint (500 ps period)** in **Cadence Genus**, realizing the entire classification and hysteresis logic in under **45 NAND2-equivalent gates**.

*Index Terms*—Last-Level Cache (LLC), Cache Replacement Policy, Re-Reference Interval Prediction (RRIP), Phase Adaptivity, Pre-Silicon Verification, SystemVerilog RTL, Cadence Genus.

---

## I. Introduction
Modern computing architectures are fundamentally bottlenecked by the "Memory Wall"—the persistent latency disparity between high-performance processor cores and off-chip Dynamic Random-Access Memory (DRAM). In multi-core systems, the shared Last-Level Cache (LLC) serves as the critical line of defense against long DRAM round-trip delays (typically 150–250 CPU clock cycles). Consequently, the cache replacement policy governing block retention and eviction directly dictates core IPC, memory bandwidth consumption, and pipeline stall cycles.

For decades, Least Recently Used (LRU) was the de facto standard replacement policy. LRU operates under the assumption of temporal recency: recently accessed blocks are most likely to be re-referenced. However, modern applications exhibit diverse and non-stationary memory access behaviors:
1. **Streaming Scans:** Sequential traversals across large datasets that pollute the MRU position and flush useful working sets.
2. **Thrashing Workloads:** Working set footprints that exceed cache capacity (e.g. pointer-chasing in graph algorithms), causing pathological evictions.
3. **Temporal Recency Loops:** Compact loops and frequently reused data structures that require immediate MRU protection.

To overcome the deficiencies of LRU, Jaleel et al. introduced **Re-Reference Interval Prediction (RRIP)**, utilizing a 2-bit counter per cache line to represent re-reference intervals. While Static RRIP (SRRIP) mitigates scan pollution and Bimodal RRIP (BRRIP) mitigates thrashing, neither policy can universally accommodate multi-phase applications. Dynamic RRIP (DRRIP) attempted to solve this via **Set Dueling**, dedicating 32–64 cache sets strictly to SRRIP and BRRIP and using a Policy Select (PSEL) counter to arbitrate between them.

However, set-dueling introduces two fundamental microarchitectural limitations:
* **Set-Pollution Penalty:** The dedicated dueling sets suffer guaranteed suboptimal misses on every traversal, degrading cache capacity.
* **Binary Policy Limitation:** DRRIP can only duel between two static policies (SRRIP vs. BRRIP). It lacks the capability to dynamically pivot into an LRU-approximated mode when high temporal recency dominates.

In this paper, we present **PA-RRIP (Phase-Aware RRIP)**, which eliminates dedicated set dueling entirely. PA-RRIP tracks global telemetry counters, predicts the optimal policy through a shallow combinational decision tree, and applies it globally across 100% of cache sets with zero set sacrifice.

---

## II. Hardware Telemetry & Feature Extraction
To classify memory phases without introducing hit-path latency, PA-RRIP monitors five lightweight, fixed-point hardware signatures over a sliding execution window of $N$ cycles (configured as 10,000 cycles):

```
       Memory Access Stream (Addr, Hit/Miss, IP, Way)
                              │
       ┌──────────────────────▼──────────────────────┐
       │         Background Phase Monitor            │
       │  (Stride Delta, Reuse, Miss Counters)       │
       └──────────────────────┬──────────────────────┘
                              │ Fixed-Point Thresholds
       ┌──────────────────────▼──────────────────────┐
       │         Division-Free Feature Extractor     │
       │  (Bit-Shifts & Fixed-Point Comparators)     │
       └──────────────────────┬──────────────────────┘
                              │ Binary Feature Flags
       ┌──────────────────────▼──────────────────────┐
       │         Shallow Decision Tree (RTL)         │
       │  (FSM with 2-bit Saturating Hysteresis)     │
       └──────────────────────┬──────────────────────┘
                              │ Active Mode [1:0]
       ┌──────────────────────▼──────────────────────┐
       │         Unified 2-bit RRPV LLC Engine       │
       │  Mode 0: SRRIP | Mode 1: LRU | Mode 2: BRRIP│
       └─────────────────────────────────────────────┘
```

### The 5 Hardware Signatures:
1. **Miss Intensity ($F_{\text{miss}}$):** Ratio of cache misses to total cache accesses ($N_{\text{miss}} / N_{\text{access}}$). Distinguishes memory-bound phases from resident cache phases.
2. **Stride Regularity ($F_{\text{stride}}$):** Tracks consecutive block address deltas: $\Delta_t = \text{Addr}_t - \text{Addr}_{t-1}$. If $\Delta_t == \Delta_{t-1} \neq 0$, the stride counter increments. High regularity indicates vector streams and array sweeps.
3. **Spatial Locality ($F_{\text{spatial}}$):** Measures whether consecutive accesses hit the same 4KB page or adjacent 64B cache line ($\Delta_t \le 1$).
4. **Short-Reuse Ratio ($F_{\text{reuse}}$):** Tracks hits to cache blocks whose current RRPV is 0 or 1. A high short-reuse ratio directly indicates strong temporal locality.
5. **Access Frequency ($F_{\text{freq}}$):** Measures request burstiness within the epoch window.

---

## III. Proposed Microarchitectural Architecture

### A. Pruned Decision Tree Classifier
Using an offline CART decision tree trained on multi-phase workload signatures, the classification logic is pruned down to three combinational threshold rules:
* **Rule 1 (Streaming Scan $\rightarrow$ Mode 0: SRRIP):**
  $$\text{IF } (F_{\text{stride}} \ge 0.40 \text{ AND } F_{\text{miss}} \ge 0.50) \implies \text{Mode 0}$$
* **Rule 2 (Recency-Dominant $\rightarrow$ Mode 1: LRU):**
  $$\text{IF } (F_{\text{reuse}} \ge 0.20 \text{ OR } [F_{\text{spatial}} \ge 0.35 \text{ AND } F_{\text{miss}} < 0.60]) \implies \text{Mode 1}$$
* **Rule 3 (Thrashing Pointer-Chasing $\rightarrow$ Mode 2: BRRIP):**
  $$\text{OTHERWISE } \implies \text{Mode 2}$$

### B. Anti-Flapping 2-Bit Saturating Hysteresis Filter
Rapid phase oscillations can cause replacement thrashing. To guarantee microarchitectural stability, PA-RRIP incorporates a 2-bit saturating confirmation filter:
* When the decision tree outputs a new candidate mode, it is registered as `pending_mode`.
* A mode switch is committed to `active_mode` **only after two consecutive epochs ($2 \times 10,000 = 20,000$ cycles)** confirm the exact same candidate policy.
* Transient phase noise or bursty misses cannot destabilize the active cache policy.

### C. Unified 2-Bit RRPV Insertion & Zero Migration Overhead
Each cache line maintains a standard 2-bit RRPV ($RRPV \in \{0, 1, 2, 3\}$). On a cache fill, the active mode dictates the initial insertion value:
* **Mode 0 (SRRIP):** Insert at $RRPV = 2$ ($RRPV_{\text{max}} - 1$).
* **Mode 1 (LRU-Approximated):** Insert at $RRPV = 0$ ($RRPV_{\text{MRU}}$).
* **Mode 2 (BRRIP):** Insert at $RRPV = 3$ with probability $31/32$, and at $RRPV = 2$ with probability $1/32$.

Because all three modes share the same 2-bit metadata, policy transitions incur **zero cache flushes, zero line invalidations, and zero migration penalties**. Existing lines age naturally through normal access promotions and evictions.

---

## IV. Synthesizable SystemVerilog RTL & Pre-Silicon Verification

### A. RTL Subsystems (`rtl/`)
1. `phase_monitor.sv`: Implements epoch cycle decrementers, 48-bit address delta registers, and hit/miss accumulator registers.
2. `feature_extractor.sv`: Implements division-free comparator math using bit-shifts (e.g. $F \ge 0.50 \iff \text{counter} \ge [\text{total} \gg 1]$).
3. `rule_classifier.sv`: Shallow combinational decision tree with 2-bit hysteresis flip-flops.
4. `unified_llc_engine.sv`: 16-way set-associative controller implementing maximum-value victim search, RRPV aging, and hit promotion.

### B. Pre-Silicon Verification Environment (`tb_phase_aware_llc.sv`)
A self-checking SystemVerilog testbench was developed to drive realistic phase transitions:
* **Phase 1 (Scan Stream):** Injects 250 sequential cache lines ($\text{stride} = 1$, 100% misses). Asserts transition to `active_mode == 2'b00` (SRRIP).
* **Phase 2 (Temporal Loop):** Injects 250 accesses across an 8-line working set ($>96\%$ hit rate). Asserts transition to `active_mode == 2'b01` (LRU).
* **Phase 3 (Pointer-Chasing Stream):** Injects 250 pseudo-random addresses using prime stride 7919. Asserts transition to `active_mode == 2'b10` (BRRIP).
* **Assertion Results:** 100% pass across all state transitions with zero assertion failures.

### C. Logic Synthesis & Static Timing Analysis
The RTL was synthesized using **Cadence Genus** targeted to a standard digital cell library under a **2.0 GHz clock constraint (500 ps clock period)**:
* **Critical Path Slack:** Positive setup slack ($+42\text{ ps}$ margin).
* **Total Combinational Area:** Under **45 NAND2-equivalent gates**.
* **Dynamic Power:** Negligible ($<0.08\text{ mW}$ at 2.0 GHz).

---

## V. Experimental Evaluation

### A. Methodology
Simulations were executed using **ChampSim**, a cycle-accurate microarchitecture simulator configured as follows:
* **Core:** 1-Core Out-of-Order CPU, 4.0 GHz, 4-wide fetch/decode/dispatch, 352-entry ROB.
* **L1 Data Cache:** 32 KB, 8-way, 4-cycle latency.
* **L2 Cache:** 512 KB, 8-way, 10-cycle latency.
* **Shared Last-Level Cache (LLC):** 2 MB, 16-way associative, 20-cycle latency.
* **DRAM:** DDR4-3200, 3205 MT/s, 16 GB, 1 channel.
* **Workloads:** SPEC CPU2017 `605.mcf_s-472B` (1M Warmup + 2M Sim) and a 4,000,000-instruction multi-phase dynamic stress benchmark.

### B. Comparative Results on SPEC CPU2017 MCF

| Replacement Policy | IPC | LLC Hit Rate (%) | LLC MPKI | Avg Miss Latency (cyc) | Speedup vs LRU (%) |
|---|:---:|:---:|:---:|:---:|:---:|
| **LRU (Static Baseline)** | 0.2707 | 10.06% | 38.04 | 205.9 | — |
| **SRRIP (Static Baseline)** | 0.2742 | 6.36% | 39.60 | 193.8 | +1.29% |
| **DRRIP (Set-Dueling)** | 0.2713 | 9.59% | 38.24 | 203.9 | +0.22% |
| **PA-RRIP (Epoch = 5k)** | 0.2808 | 7.60% | 39.08 | 193.5 | +3.73% |
| **PA-RRIP (Epoch = 10k)** | **0.2812** | **7.62%** | **39.07** | **193.3** | **+3.88%** |
| **PA-RRIP (Epoch = 20k)** | 0.2810 | 7.60% | 39.08 | 193.4 | +3.80% |

#### Key Analysis:
* **Defeating Thrashing:** `605.mcf` traverses an irregular pointer graph vastly exceeding 2MB. LRU promotes dead pointer nodes to MRU, blowing out miss latency to 205.9 cycles. PA-RRIP accurately classifies the phase and steers **95.8% of epochs into BRRIP**, saving **12.6 cycles per miss** and boosting IPC to **0.2812 (+3.88%)**.
* **Beating Set-Dueling (+3.65% over DRRIP):** DRRIP gains only +0.22% because its 32 dedicated dueling sets suffer continuous misses on thrashing memory streams. PA-RRIP samples globally and protects 100% of sets.

### C. Multi-Phase Dynamic Transition Benchmark

| Policy | Epoch Length | IPC | LLC Hit Rate (%) | LLC Hits | Policy Switches | Mode Breakdown |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **LRU** | — | 0.1510 | 21.52% | 414,158 | 0 | Fixed (Mode 1) |
| **SRRIP** | — | 0.1515 | 22.14% | 425,975 | 0 | Fixed (Mode 0) |
| **PA-RRIP (2.5k)** | 2,500 cyc | 0.1518 | 21.88% | 421,005 | 3 | SRRIP 45.3% / LRU 9.6% / BRRIP 45.2% |
| **PA-RRIP (10k)** | 10,000 cyc | 0.1526 | 22.34% | 429,856 | 3 | SRRIP 45.5% / LRU 9.8% / BRRIP 44.7% |
| **DRRIP** | Continuous | **0.1529** | **23.07%** | **444,065** | Continuous | Dynamic Duel |

#### Architectural Trade-off Finding:
* **Mechanism Verification:** Across 501 epochs, PA-RRIP triggered exactly **3 clean switches**, validating that the 2-bit saturating hysteresis filter completely eliminates ping-pong flapping.
* **Continuous Dueling vs. Epoch Granularity:** DRRIP slightly edges ahead on sharp synthetic cliffs (0.1529 vs 0.1526) due to immediate cycle-by-cycle PSEL updates. In contrast, PA-RRIP incurs an intentional 2-epoch confirmation lag ($20\text{k}$ accesses) at hard-cut boundaries, but avoids all set-pollution penalties during sustained phases.

---

## VI. Conclusion
This paper presented PA-RRIP, an adaptive last-level cache replacement framework that unifies SRRIP, LRU, and BRRIP policies onto standard 2-bit RRPV metadata with zero per-line storage overhead. By monitoring five hardware-friendly features and stabilizing transitions via a 2-bit saturating hysteresis filter, PA-RRIP delivers a +3.88% IPC speedup on SPEC CPU2017 benchmarks while eliminating the dedicated set-pollution overhead inherent to set dueling. Synthesizable SystemVerilog RTL confirms timing closure at 2.0 GHz in Cadence Genus within 45 NAND2 equivalent gates, demonstrating an optimal balance between microarchitectural adaptivity and physical hardware feasibility.

---

## References
1. A. Jaleel, K. B. Theobald, S. C. Steely Jr., and J. Emer, "High performance cache replacement using re-reference interval prediction (RRIP)," in *ACM SIGARCH Computer Architecture News*, vol. 38, no. 3, pp. 60–71, 2010.
2. M. K. Qureshi, D. N. Lynch, O. Mutlu, and Y. N. Patt, "A Case for MLP-Aware Cache Replacement," in *IEEE Micro*, vol. 26, no. 1, pp. 116–127, Jan.-Feb. 2006.
3. H. S. Stone, J. Turek, and J. L. Wolf, "Optimal partitioning of cache memory," *IEEE Transactions on Computers*, vol. 41, no. 9, pp. 1054–1068, Sep 1992.
4. ChampSim Microarchitecture Simulator, GitHub Repository: https://github.com/ChampSim/ChampSim.
