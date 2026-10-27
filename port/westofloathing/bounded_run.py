#!/usr/bin/env python3
"""Target-side diagnostic deadline; owns and signals only its Popen child."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def run(executable, root, seconds):
    seconds = int(seconds)
    if not 1 <= seconds <= 1800:
        raise ValueError('diagnostic seconds must be 1..1800')
    run_id = os.environ.get('WOL_RUN_ID', 'latest')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('invalid diagnostic run id')
    proc = subprocess.Popen([str(executable), str(root)])
    reason = 'exited'
    started = time.monotonic()
    try:
        pp = Path('/proc') / str(proc.pid)
        stat = (pp / 'stat').read_text().rsplit(')', 1)[1].split()
        digest = hashlib.sha256()
        with open(executable, 'rb') as binary:
            for block in iter(lambda: binary.read(1048576), b''):
                digest.update(block)
        identity = {'pid': proc.pid, 'start_ticks': int(stat[19]),
                    'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    'exe': os.readlink(pp / 'exe'), 'sha256': digest.hexdigest()}
        if not os.path.samefile(pp / 'exe', executable):
            raise RuntimeError('diagnostic child executable identity mismatch')
        print('WOL_CHILD ' + json.dumps(identity), flush=True)
        (Path(root) / 'logs' / (run_id + '.process.json')).write_text(json.dumps(identity))
        sample = 0
        while proc.poll() is None:
            elapsed = time.monotonic() - started
            mem = {k: int(v.split()[0]) for k, v in (s.split(':', 1) for s in Path('/proc/meminfo').read_text().splitlines())}
            if elapsed >= seconds:
                reason = 'deadline'
                break
            if mem['MemAvailable'] < 65536:
                reason = 'memory_floor_64MiB'
                break
            if elapsed >= sample:
                try:
                    status = dict(s.split(':', 1) for s in (pp / 'status').read_text().splitlines())
                    print('WOL_SAMPLE ' + json.dumps({'seconds': round(elapsed, 2),
                        **{k: mem.get(k) for k in ('MemAvailable', 'CmaFree', 'SwapFree')},
                        **{k: status.get(k, '').strip() for k in ('VmRSS', 'VmSwap')} }), flush=True)
                except FileNotFoundError:
                    break
                sample += 5
            time.sleep(0.5)
    except (FileNotFoundError, ProcessLookupError):
        if proc.poll() is None:
            raise
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        rc = proc.wait()
        print('WOL_CHILD_EXIT ' + json.dumps({'pid': proc.pid, 'rc': rc, 'reason': reason,
              'seconds': round(time.monotonic() - started, 2)}), flush=True)
    return rc


if __name__ == '__main__':
    raise SystemExit(run(*sys.argv[1:]))
