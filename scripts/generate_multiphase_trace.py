#!/usr/bin/env python3
import struct, os, random, sys

def generate_trace(output_path, total_instructions=4000000):
    fmt = '<QBB2B4B2Q4Q'
    
    # Phase 1: Instructions 0 - 1M: Recency Loop (Working set ~ 1.2 MB = 18750 cache lines of 64B)
    working_set_lines = 18000
    base_addr_recency = 0x20000000
    
    # Phase 2: Instructions 1M - 2.5M: Streaming Scan (Sequentially streaming across 16MB array)
    base_addr_stream = 0x50000000
    stream_lines = 250000
    
    # Phase 3: Instructions 2.5M - 4M: Thrashing Pointer Chase (Pseudo-random traversal over 32MB)
    base_addr_thrash = 0x80000000
    thrash_lines = 500000
    step_prime = 104729
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'wb') as f:
        stream_idx = 0
        thrash_idx = 0
        recency_idx = 0
        
        for i in range(total_instructions):
            ip = 0x400000 + ((i % 1000) * 4)
            is_branch = 1 if (i % 10 == 0) else 0
            branch_taken = 1 if (is_branch and i % 20 == 0) else 0
            dest_regs = (1, 0)
            src_regs = (2, 3, 0, 0)
            dest_mem = (0, 0)
            
            if i % 2 == 0:
                if i < 1000000:
                    addr = base_addr_recency + ((recency_idx % working_set_lines) << 6)
                    recency_idx += 1
                elif i < 2500000:
                    addr = base_addr_stream + ((stream_idx % stream_lines) << 6)
                    stream_idx += 1
                else:
                    thrash_idx = (thrash_idx + step_prime) % thrash_lines
                    addr = base_addr_thrash + (thrash_idx << 6)
                src_mem = (addr, 0, 0, 0)
            else:
                src_mem = (0, 0, 0, 0)
                
            rec = struct.pack(fmt, ip, is_branch, branch_taken, *dest_regs, *src_regs, *dest_mem, *src_mem)
            f.write(rec)
            
    print(f'Generated {total_instructions} instructions at {output_path} ({os.path.getsize(output_path)/(1024*1024):.1f} MB)')

if __name__ == '__main__':
    out_file = sys.argv[1] if len(sys.argv) > 1 else '/home/kousika/traces/multiphase_workload.champsimtrace'
    num_inst = int(sys.argv[2]) if len(sys.argv) > 2 else 4000000
    generate_trace(out_file, num_inst)
