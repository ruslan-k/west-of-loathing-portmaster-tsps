#!/usr/bin/env python3
"""Phase-snapshot comparison for the M1/M5 read-only memory runs (roadmap section 5/14.2).

Reads the compressed per-phase JSON snapshots (startup/menu/game/sheriff/returned) produced by
the m1m5 harness and reports per-phase rollup/status/meminfo trends plus the launch-time
runtime excerpts (ROMFS reads, pool bounds). Usage:
  analyze_memory_phases.py <dir-with-xz-snapshots> [--excerpt runtime-memory-excerpt.json.xz]"""
import json, lzma, sys
from pathlib import Path

root = Path(sys.argv[1])
phases = ["startup", "menu", "game", "sheriff", "returned"]
rows = []
for ph in phases:
    p = root / (ph + ".json.xz")
    if not p.exists():
        continue
    d = json.loads(lzma.open(p).read())
    smp = d.get("samples") or []
    roll = smp[-1].get("rollup", {}) if smp else {}
    st = smp[-1].get("status", {}) if smp else {}
    mi = smp[-1].get("meminfo", {}) if smp else {}
    s = d.get("summary", {})
    rows.append(dict(phase=ph, samples=len(smp),
                     rss_kib=st.get("VmRSS"), swap_kib=st.get("VmSwap"), rss_anon=st.get("RssAnon"),
                     rss_file=st.get("RssFile"),
                     pss=(roll.get("Pss")), pss_anon=roll.get("Pss_Anon"), pss_file=roll.get("Pss_File"),
                     mem_avail_kib=mi.get("MemAvailable"), swap_cached=mi.get("SwapCached"),
                     summary=s))

report = dict(phases=rows)
# launch excerpt: largest ROMFS reads and pool bounds
exc = None
for cand in sys.argv[2:] if len(sys.argv) > 2 else []:
    exc = Path(cand)
if exc is None:
    exc = root / "runtime-memory-excerpt.json.xz"
if exc.exists():
    ex = json.loads(lzma.open(exc).read())
    reads = []
    pools = []
    biggest = 0
    for l in ex.get("lines", []):
        if l.startswith("ROMFS_READ"):
            kv = dict(kv.split("=") for kv in l.split()[1:])
            sz = int(kv.get("size", "0"), 16)
            reads.append((sz, kv.get("offset")))
            biggest = max(biggest, sz)
        elif l.startswith("NVN_MEMORY_POOL_BOUND"):
            pools.append(l)
    report["excerpt"] = dict(read_count=len(reads), largest_read_bytes=biggest,
                             largest_read_mib=round(biggest / 2**20, 1),
                             top_reads=[(hex(s), o) for s, o in sorted(reads, reverse=True)[:5]],
                             pool_bounds=pools[:8])
print(json.dumps(report, indent=1))
