#ifndef REPLACEMENT_PA_RRIP_H
#define REPLACEMENT_PA_RRIP_H

#include <vector>
#include <cstdint>
#include <string>
#include <fstream>
#include <iostream>
#include <cstdlib>
#include <memory>

#include "cache.h"
#include "modules.h"

enum class PAMode : uint8_t {
  SRRIP = 0, // Mode 0: Scan / Streaming resistance (RRPV=2)
  LRU   = 1, // Mode 1: Recency / Temporal locality protection (RRPV=0)
  BRRIP = 2  // Mode 2: Thrashing / Pointer-chasing resistance (RRPV=3 mostly)
};

struct PerCoreMonitor {
  uint64_t epoch_accesses = 0;
  uint64_t epoch_misses = 0;
  uint64_t epoch_short_reuse_hits = 0;
  uint64_t epoch_spatial_hits = 0;
  uint64_t epoch_stride_matches = 0;

  uint64_t last_block_addr = 0;
  int64_t last_stride = 0;

  PAMode active_mode = PAMode::SRRIP;
  PAMode pending_mode = PAMode::SRRIP;
  uint32_t consecutive_epochs = 0;

  // Cumulative statistics across all epochs
  uint64_t total_epochs = 0;
  uint64_t epochs_srrip = 0;
  uint64_t epochs_lru = 0;
  uint64_t epochs_brrip = 0;
  uint64_t mode_switches = 0;

  uint64_t sum_accesses = 0;
  uint64_t sum_misses = 0;
  uint64_t sum_short_reuse = 0;
  uint64_t sum_spatial = 0;
  uint64_t sum_stride_matches = 0;
};

struct pa_rrip : public champsim::modules::replacement {
  static constexpr unsigned maxRRPV = 3;
  static constexpr unsigned BRRIP_MAX = 32;

  long NUM_SET;
  long NUM_WAY;
  unsigned brrip_counter = 0;
  uint64_t global_cycle = 0;

  std::vector<unsigned> rrpv;

  // Configurable epoch size (in cycles/accesses)
  uint64_t epoch_length = 10000;
  uint64_t last_epoch_cycle = 0;

  // Per-core phase monitors for multi-core awareness
  std::vector<PerCoreMonitor> core_monitors;

  // Optional CSV logging for offline ML training
  bool logging_enabled = false;
  std::shared_ptr<std::ofstream> log_file;

  explicit pa_rrip(CACHE* cache);
  pa_rrip(CACHE* cache, long sets, long ways);

  pa_rrip(const pa_rrip&) = default;
  pa_rrip& operator=(const pa_rrip&) = default;
  pa_rrip(pa_rrip&&) = default;
  pa_rrip& operator=(pa_rrip&&) = default;

  unsigned& get_rrpv(long set, long way);

  void check_epoch_boundary(uint32_t cpu);
  PAMode classify_phase(const PerCoreMonitor& mon);

  long find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set,
                   champsim::address ip, champsim::address full_addr, access_type type);
  void replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr,
                              champsim::address ip, champsim::address victim_addr, access_type type);
  void update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr,
                                champsim::address ip, champsim::address victim_addr, access_type type, uint8_t hit);
  void replacement_final_stats();
};

#endif
