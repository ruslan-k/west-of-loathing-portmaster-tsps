#!/usr/bin/env python3
"""WOL_OP_V3 ledger parser and invariant checker.

The emitter is C inside runtime/wol-adapter.patch (nvn_replay.h). These checks
validate the emitted contract: one row per (frame, tid, class), frames
increasing per (tid, class), and mean = sum / n within print rounding. The
terminal partial bucket is not flushed by the emitter, so a missing last frame
is expected, not a failure.
"""
import argparse
import json
import re
import statistics as st
import sys
from pathlib import Path

WIN = re.compile(r"NVN_PROFILE frame=(\d+) count=(\d+) elapsed-ms=([\d.]+) replay-ms=([\d.]+) present-ms=([\d.]+)")
V3 = re.compile(
    r"WOL_OP_V3 frame=(\d+) tid=(\d+) cls=(\w+) n=(\d+) "
    r"sum_wall_ms=([\d.]+) sum_cpu_ms=([\d.]+) mean_wall_ms=([\d.]+) mean_cpu_ms=([\d.]+)")
ROUNDING = 0.01  # operands print 3 decimals; n*mean can differ by up to n*0.0005


def parse(lines):
    wins, rows = [], []
    for line in lines:
        m = WIN.search(line)
        if m:
            wins.append(dict(frame=int(m[1]), count=int(m[2]), elapsed=float(m[3]), replay=float(m[4])))
            continue
        m = V3.search(line)
        if m:
            rows.append(dict(frame=int(m[1]), tid=int(m[2]), cls=m[3], n=int(m[4]),
                             sum_wall=float(m[5]), sum_cpu=float(m[6]),
                             mean_wall=float(m[7]), mean_cpu=float(m[8])))
    return wins, rows


def validate(rows):
    problems, seen, last = [], set(), {}
    for r in rows:
        key = (r["frame"], r["tid"], r["cls"])
        if key in seen:
            problems.append("duplicate row %s" % (key,))
        seen.add(key)
        prev = last.get((r["tid"], r["cls"]))
        if prev is not None and r["frame"] <= prev:
            problems.append("frame %d after %d for %s" % (r["frame"], prev, r["cls"]))
        last[(r["tid"], r["cls"])] = r["frame"]
        if r["n"] <= 0:
            problems.append("non-positive n %s" % (key,))
        for kind in ("wall", "cpu"):
            if r["n"] and abs(r["mean_" + kind] * r["n"] - r["sum_" + kind]) > ROUNDING:
                problems.append("mean*n != sum for %s %s" % (key, kind))
    return problems


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarize(wins, rows):
    out = {"windows": len(wins), "v3_rows": len(rows),
           "tids": sorted({r["tid"] for r in rows}), "problems": validate(rows)}
    if wins:
        e = [w["elapsed"] for w in wins]
        out["frame_ms"] = {"n": len(e), "p50": round(st.median(e), 3),
                           "p95": round(q(e, 0.95), 3), "min": round(min(e), 3), "max": round(max(e), 3),
                           "replay_median": round(st.median([w["replay"] for w in wins]), 3)}
    if rows:
        per_frame = {}
        for r in rows:
            per_frame.setdefault(r["frame"], {})[r["cls"]] = r
        totals = [sum(v["sum_wall"] for v in f.values()) for f in per_frame.values()]
        out["v3"] = {"frames": len(per_frame)}
        for c in sorted({r["cls"] for r in rows}):
            out["v3"][c] = {
                "n_median": st.median([r["n"] for r in rows if r["cls"] == c]),
                "sum_wall_median": round(st.median([r["sum_wall"] for r in rows if r["cls"] == c]), 3),
                "sum_cpu_median": round(st.median([r["sum_cpu"] for r in rows if r["cls"] == c]), 3),
            }
        out["v3"]["accounted_ms_median"] = round(st.median(totals), 3)
        if wins:
            out["v3"]["accounted_pct_of_frame"] = round(100 * st.median(totals) / st.median([w["elapsed"] for w in wins]), 2)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--from-frame", type=int, default=0)
    a = ap.parse_args(argv)
    results, bad = [], False
    for name in a.logs:
        wins, rows = parse(Path(name).read_text(errors="replace").splitlines())
        wins = [w for w in wins if w["frame"] - w["count"] + 1 >= a.from_frame]
        rows = [r for r in rows if r["frame"] >= a.from_frame]
        s = summarize(wins, rows)
        s["log"] = Path(name).name
        bad |= bool(s["problems"])
        results.append(s)
    print(json.dumps(results, indent=2))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
