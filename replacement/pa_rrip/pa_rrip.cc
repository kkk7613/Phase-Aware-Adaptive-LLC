#include "pa_rrip.h"

#include <algorithm>
#include <cassert>
#include <iomanip>

pa_rrip::pa_rrip(CACHE* cache) : pa_rrip(cache, cache->NUM_SET, cache->NUM_WAY) {}

pa_rrip::pa_rrip(CACHE* cache, long sets, long ways)
    : replacement(cache),
      NUM_SET(sets),
      NUM_WAY(ways),
      rrpv(static_cast<std::size_t>(sets * ways), maxRRPV),
      core_monitors(NUM_CPUS)
{
  // Check for environment variable to customize epoch length
  const char* epoch_env = std::getenv("PA_EPOCH_CYCLES");
  if (epoch_env) {
    epoch_length = std::strtoull(epoch_env, nullptr, 10);
  }

  // Check for CSV feature logging
  const char* log_env = std::getenv("PA_LOG_EPOCHS");
  if (log_env && std::string(log_env) == "1") {
    logging_enabled = true;
    log_file = std::make_shared<std::ofstream>("pa_epoch_features.csv", std::ios::out);
    if (log_file && log_file->is_open()) {
      *log_file << "epoch,cpu,accesses,misses,miss_intensity,short_reuse_ratio,spatial_ratio,stride_regularity,selected_mode\n";
    }
  }
}

unsigned& pa_rrip::get_rrpv(long set, long way) {
  return rrpv.at(static_cast<std::size_t>(set * NUM_WAY + way));
}

PAMode pa_rrip::classify_phase(const PerCoreMonitor& mon) {
  if (mon.epoch_accesses < 10) {
    return mon.active_mode; // Not enough samples, keep current mode
  }

  double total = static_cast<double>(mon.epoch_accesses);
  double miss_intensity = static_cast<double>(mon.epoch_misses) / total;
  double reuse_ratio    = static_cast<double>(mon.epoch_short_reuse_hits) / total;
  double spatial_ratio  = static_cast<double>(mon.epoch_spatial_hits) / total;
  double stride_ratio   = static_cast<double>(mon.epoch_stride_matches) / total;

  // Decision Tree Classifier (pruned shallow rules for hardware implementation):
  // Rule 1: High stride regularity and high miss intensity -> Scan / Streaming pattern
  if (stride_ratio >= 0.40 && miss_intensity >= 0.50) {
    return PAMode::SRRIP; // Mode 0
  }

  // Rule 2: High short-term reuse or high spatial locality with moderate miss intensity -> Recency-dominant
  if (reuse_ratio >= 0.20 || (spatial_ratio >= 0.35 && miss_intensity < 0.60)) {
    return PAMode::LRU; // Mode 1
  }

  // Rule 3: Irregular stride, low reuse, high miss intensity -> Thrashing / Pointer-chasing
  return PAMode::BRRIP; // Mode 2
}

void pa_rrip::check_epoch_boundary(uint32_t cpu) {
  global_cycle++;
  if (global_cycle - last_epoch_cycle >= epoch_length) {
    last_epoch_cycle = global_cycle;

    for (uint32_t c = 0; c < NUM_CPUS; ++c) {
      auto& mon = core_monitors[c];
      mon.total_epochs++;

      // Accumulate totals
      mon.sum_accesses       += mon.epoch_accesses;
      mon.sum_misses         += mon.epoch_misses;
      mon.sum_short_reuse    += mon.epoch_short_reuse_hits;
      mon.sum_spatial        += mon.epoch_spatial_hits;
      mon.sum_stride_matches += mon.epoch_stride_matches;

      // Predict next mode
      PAMode predicted = classify_phase(mon);

      // Log features if requested
      if (logging_enabled && log_file && log_file->is_open() && mon.epoch_accesses > 0) {
        double total = static_cast<double>(mon.epoch_accesses);
        *log_file << mon.total_epochs << ","
                  << c << ","
                  << mon.epoch_accesses << ","
                  << mon.epoch_misses << ","
                  << (static_cast<double>(mon.epoch_misses) / total) << ","
                  << (static_cast<double>(mon.epoch_short_reuse_hits) / total) << ","
                  << (static_cast<double>(mon.epoch_spatial_hits) / total) << ","
                  << (static_cast<double>(mon.epoch_stride_matches) / total) << ","
                  << static_cast<int>(predicted) << "\n";
      }

      // 2-bit Saturating Hysteresis Filter (Enhancement 2)
      if (predicted == mon.pending_mode) {
        mon.consecutive_epochs++;
        if (mon.consecutive_epochs >= 2 && mon.active_mode != predicted) {
          mon.active_mode = predicted;
          mon.mode_switches++;
        }
      } else {
        mon.pending_mode = predicted;
        mon.consecutive_epochs = 1;
      }

      // Track active mode residency
      if (mon.active_mode == PAMode::SRRIP) mon.epochs_srrip++;
      else if (mon.active_mode == PAMode::LRU) mon.epochs_lru++;
      else if (mon.active_mode == PAMode::BRRIP) mon.epochs_brrip++;

      // Reset epoch counters for next epoch window
      mon.epoch_accesses = 0;
      mon.epoch_misses = 0;
      mon.epoch_short_reuse_hits = 0;
      mon.epoch_spatial_hits = 0;
      mon.epoch_stride_matches = 0;
    }
  }
}

long pa_rrip::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set,
                          const champsim::cache_block* current_set,
                          champsim::address ip, champsim::address full_addr, access_type type)
{
  check_epoch_boundary(triggering_cpu);

  auto begin = std::next(std::begin(rrpv), set * NUM_WAY);
  auto end = std::next(begin, NUM_WAY);

  // Search for the first block with maximum RRPV (distant re-reference)
  auto victim = std::max_element(begin, end);
  if (auto rrpv_update = maxRRPV - *victim; rrpv_update != 0) {
    for (auto it = begin; it != end; ++it) {
      *it += rrpv_update;
    }
  }

  assert(begin <= victim);
  assert(victim < end);
  return std::distance(begin, victim);
}

void pa_rrip::replacement_cache_fill(uint32_t triggering_cpu, long set, long way,
                                     champsim::address full_addr, champsim::address ip,
                                     champsim::address victim_addr, access_type type)
{
  check_epoch_boundary(triggering_cpu);
  auto& mon = core_monitors[triggering_cpu];

  // Count cache miss (fill occurs upon miss)
  mon.epoch_misses++;
  mon.epoch_accesses++;

  // Feature Extraction: Stride Regularity & Spatial Locality
  uint64_t current_block = full_addr.to<uint64_t>() >> 6; // 64-byte cache block
  if (mon.last_block_addr != 0) {
    int64_t stride = static_cast<int64_t>(current_block) - static_cast<int64_t>(mon.last_block_addr);
    if (stride == mon.last_stride && stride != 0) {
      mon.epoch_stride_matches++;
    }
    mon.last_stride = stride;

    // Check spatial locality: same 4KB page (upper bits match) or adjacent block
    if ((current_block >> 6) == (mon.last_block_addr >> 6) || std::abs(stride) <= 1) {
      mon.epoch_spatial_hits++;
    }
  }
  mon.last_block_addr = current_block;

  // Skip state updates for writebacks
  if (access_type{type} == access_type::WRITE) {
    get_rrpv(set, way) = maxRRPV - 1;
    return;
  }

  // Steer insertion according to requesting core's active policy
  switch (mon.active_mode) {
    case PAMode::SRRIP:
      // Mode 0: SRRIP insertion for scan resistance
      get_rrpv(set, way) = maxRRPV - 1; // RRPV = 2
      break;

    case PAMode::LRU:
      // Mode 1: LRU-approximated MRU insertion for recency-sensitive phases
      get_rrpv(set, way) = 0;
      break;

    case PAMode::BRRIP:
      // Mode 2: BRRIP bimodal insertion for thrashing resistance
      get_rrpv(set, way) = maxRRPV; // 31/32 probability RRPV = 3
      brrip_counter++;
      if (brrip_counter >= BRRIP_MAX) {
        brrip_counter = 0;
        get_rrpv(set, way) = maxRRPV - 1; // 1/32 probability RRPV = 2
      }
      break;
  }
}

void pa_rrip::update_replacement_state(uint32_t triggering_cpu, long set, long way,
                                      champsim::address full_addr, champsim::address ip,
                                      champsim::address victim_addr, access_type type, uint8_t hit)
{
  check_epoch_boundary(triggering_cpu);
  auto& mon = core_monitors[triggering_cpu];

  if (hit) {
    mon.epoch_accesses++;

    // Track short reuse: hit to a line with low RRPV (0 or 1)
    if (get_rrpv(set, way) <= 1) {
      mon.epoch_short_reuse_hits++;
    }

    // Spatial & Stride tracking on hits
    uint64_t current_block = full_addr.to<uint64_t>() >> 6;
    if (mon.last_block_addr != 0) {
      int64_t stride = static_cast<int64_t>(current_block) - static_cast<int64_t>(mon.last_block_addr);
      if (stride == mon.last_stride && stride != 0) {
        mon.epoch_stride_matches++;
      }
      mon.last_stride = stride;

      if ((current_block >> 6) == (mon.last_block_addr >> 6) || std::abs(stride) <= 1) {
        mon.epoch_spatial_hits++;
      }
    }
    mon.last_block_addr = current_block;

    // Skip writeback hit updates
    if (access_type{type} == access_type::WRITE) {
      return;
    }

    // Hit promotion: promote to MRU (RRPV = 0)
    get_rrpv(set, way) = 0;
  }
}

void pa_rrip::replacement_final_stats() {
  std::cout << "\n=======================================================\n";
  std::cout << "  PHASE-AWARE ADAPTIVE LLC REPLACEMENT (PA-RRIP) STATS \n";
  std::cout << "=======================================================\n";
  std::cout << "Configured Epoch Length: " << epoch_length << " cycles\n";

  for (uint32_t c = 0; c < NUM_CPUS; ++c) {
    const auto& mon = core_monitors[c];
    std::cout << "\n[Core " << c << " Phase Profile]\n";
    std::cout << "  Total Epochs:      " << mon.total_epochs << "\n";
    std::cout << "  Policy Switches:   " << mon.mode_switches << "\n";
    if (mon.total_epochs > 0) {
      double pct_srrip = 100.0 * mon.epochs_srrip / mon.total_epochs;
      double pct_lru   = 100.0 * mon.epochs_lru   / mon.total_epochs;
      double pct_brrip = 100.0 * mon.epochs_brrip / mon.total_epochs;
      std::cout << "  Mode 0 (SRRIP):    " << mon.epochs_srrip << " epochs (" << std::fixed << std::setprecision(1) << pct_srrip << "%)\n";
      std::cout << "  Mode 1 (LRU):      " << mon.epochs_lru   << " epochs (" << std::fixed << std::setprecision(1) << pct_lru   << "%)\n";
      std::cout << "  Mode 2 (BRRIP):    " << mon.epochs_brrip << " epochs (" << std::fixed << std::setprecision(1) << pct_brrip << "%)\n";
    }
    if (mon.sum_accesses > 0) {
      double acc = static_cast<double>(mon.sum_accesses);
      std::cout << "  Avg Miss Rate:     " << std::fixed << std::setprecision(2) << (100.0 * mon.sum_misses / acc) << "%\n";
      std::cout << "  Avg Stride Match:  " << std::fixed << std::setprecision(2) << (100.0 * mon.sum_stride_matches / acc) << "%\n";
      std::cout << "  Avg Spatial Loc:   " << std::fixed << std::setprecision(2) << (100.0 * mon.sum_spatial / acc) << "%\n";
      std::cout << "  Avg Short Reuse:   " << std::fixed << std::setprecision(2) << (100.0 * mon.sum_short_reuse / acc) << "%\n";
    }
  }
  std::cout << "=======================================================\n\n";
}
