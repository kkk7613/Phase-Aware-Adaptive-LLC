import subprocess, os, re

CHAMPSIM = '/home/kousika/ChampSim'
TRACE = '/home/kousika/traces/multiphase_workload.champsimtrace'

epochs = [2500, 5000, 10000, 20000]
print('=== MULTI-PHASE EPOCH SENSITIVITY SWEEP ===')

for ep in epochs:
    env = os.environ.copy()
    env['PA_EPOCH_CYCLES'] = str(ep)
    cmd = [
        os.path.join(CHAMPSIM, 'bin/champsim_pa_rrip'),
        '--warmup-instructions', '200000',
        '--simulation-instructions', '3800000',
        TRACE
    ]
    print(f'[*] Running Epoch = {ep}...', flush=True)
    res = subprocess.run(cmd, cwd=CHAMPSIM, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = res.stdout
    ipc_m = re.search(r'CPU 0 cumulative IPC:\s+([0-9.]+)', out)
    llc_m = re.search(r'cpu0->LLC TOTAL\s+ACCESS:\s+([0-9]+)\s+HIT:\s+([0-9]+)\s+MISS:\s+([0-9]+)', out)
    sw_m = re.search(r'Policy Switches:\s+([0-9]+)', out)
    srrip_m = re.search(r'Mode 0 \(SRRIP\):\s+([0-9]+)\s+epochs\s+\(([0-9.]+)%\)', out)
    lru_m = re.search(r'Mode 1 \(LRU\):\s+([0-9]+)\s+epochs\s+\(([0-9.]+)%\)', out)
    brrip_m = re.search(r'Mode 2 \(BRRIP\):\s+([0-9]+)\s+epochs\s+\(([0-9.]+)%\)', out)
    
    ipc = ipc_m.group(1) if ipc_m else '0'
    hit = llc_m.group(2) if llc_m else '0'
    sw = sw_m.group(1) if sw_m else '0'
    s_pct = srrip_m.group(2) if srrip_m else '0'
    l_pct = lru_m.group(2) if lru_m else '0'
    b_pct = brrip_m.group(2) if brrip_m else '0'
    print(f'--> Epoch {ep}: IPC={ipc}, Hits={hit}, Switches={sw} | SRRIP {s_pct}% / LRU {l_pct}% / BRRIP {b_pct}%')
