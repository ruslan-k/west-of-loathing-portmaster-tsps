#!/usr/bin/env python3
"""VMA diff between two phase snapshots (roadmap section 5: which mappings grow / stabilise /
shrink). Reads the `start`/`end` snapshot objects of two phase JSONs produced by the m1m5
harness (they embed /proc/<pid>/smaps rows). Usage:
  analyze_vma_diff.py menu.json game.json [--label-a menu --label-b game]"""
import json, sys
from collections import defaultdict


def load(path, which):
    d = json.load(open(path))
    snap = d[which] if which in d else d
    return d.get("phase", "?"), snap.get("mappings", []), snap.get("pagemap", {}), snap.get("rollup", {})


def category(row):
    p = row.get("path")
    if not p:
        return "[anon]"
    return p


def agg(rows):
    out = defaultdict(lambda: dict(n=0, size=0, rss=0, pss=0))
    for r in rows:
        c = out[category(r)]
        c["n"] += 1
        c["size"] += r.get("Size", 0)
        c["rss"] += r.get("Rss", 0)
        c["pss"] += r.get("Pss", 0)
    return out


args = sys.argv[1:]
label_a, label_b = "A", "B"
if "--label-a" in args:
    i = args.index("--label-a"); label_a = args[i + 1]; del args[i:i + 2]
if "--label-b" in args:
    i = args.index("--label-b"); label_b = args[i + 1]; del args[i:i + 2]
which = "end"
if "--start" in args:
    which = "start"; args.remove("--start")
f1, f2 = args[0], args[1]
ph_a, rows_a, pg_a, ro_a = load(f1, which)
ph_b, rows_b, pg_b, ro_b = load(f2, which)

A, B = agg(rows_a), agg(rows_b)
cats = sorted(set(A) | set(B), key=lambda c: -abs(B.get(c, {}).get("pss", 0) - A.get(c, {}).get("pss", 0)))
rows = []
for c in cats[:18]:
    a, b = A.get(c, {}), B.get(c, {})
    rows.append(dict(category=c, pss_a=a.get("pss", 0), pss_b=b.get("pss", 0),
                     dpss=b.get("pss", 0) - a.get("pss", 0),
                     rss_a=a.get("rss", 0), rss_b=b.get("rss", 0), n_a=a.get("n", 0), n_b=b.get("n", 0)))

# largest individual mappings in B, with Pss
big = sorted(rows_b, key=lambda r: -r.get("Pss", 0))[:12]
detail = [dict(start=hex(r["start"]), end=hex(r["end"]), size_kb=r.get("Size"), pss_kb=r.get("Pss"),
               rss_kb=r.get("Rss"), path=(r.get("path") or "[anon]")) for r in big]

print(json.dumps(dict(
    phase_a=(ph_a, label_a), phase_b=(ph_b, label_b), which=which,
    rollup_a={k: ro_a.get(k) for k in ("Pss", "Pss_Anon", "Pss_File", "SwapPss")},
    rollup_b={k: ro_b.get(k) for k in ("Pss", "Pss_Anon", "Pss_File", "SwapPss")},
    pagemap_a=pg_a.get("counts"), pagemap_b=pg_b.get("counts"),
    category_deltas=rows, largest_b=detail), indent=1))
