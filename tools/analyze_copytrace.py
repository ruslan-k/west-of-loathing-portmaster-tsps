#!/usr/bin/env python3
"""Analyse WOL_COPYTRACE events: for each inter-copy interval, check the ordering of
destination samples vs source writes (the lazy-alias hazard). Usage: analyze_copytrace.py <runtime.log>"""
import json, re, sys
from collections import Counter

path = sys.argv[1]
events = []
summary = []
for line in open(path, errors="replace"):
    m = re.match(r"WOL_COPYTRACE_EVENT seq=(\d+) frame=(\d+) kind=(\d+) object=0x([0-9a-f]+)", line)
    if m:
        events.append(dict(seq=int(m.group(1)), frame=int(m.group(2)), kind=int(m.group(3)), obj=m.group(4)))
    m2 = re.match(r"WOL_COPYTRACE_SUMMARY frame=(\d+) copies=(\d+) src-id=(\d+) dst-id=(\d+) draws-src-since-copy=(\d+) samples-dst=(\d+) samples-src=(\d+)", line)
    if m2:
        summary.append(dict(frame=int(m2.group(1)), copies=int(m2.group(2)), src_id=int(m2.group(3)),
                            dst_id=int(m2.group(4)), draws_src=int(m2.group(5)),
                            samples_dst=int(m2.group(6)), samples_src=int(m2.group(7))))

intervals, cur = [], None
for e in events:
    if e["kind"] == 1:
        if cur: intervals.append(cur)
        cur = dict(frame=e["frame"], events=[])
    elif cur is not None:
        cur["events"].append(e)
if cur: intervals.append(cur)

stats = Counter()
hazards = []
for iv in intervals:
    seq = [(e["kind"], e["frame"]) for e in iv["events"]]
    k = [s[0] for s in seq]
    stats["intervals"] += 1
    if 3 in k: stats["dst_sampled"] += 1
    if 4 in k: stats["src_sampled"] += 1
    if 2 in k: stats["src_redrawn"] += 1
    # hazard: a draw-into-src happens at/after a sample of dst (the alias would change
    # what later dst samples observe), or a src sample happens after a src draw.
    drawn = False
    for kind, fr in seq:
        if kind == 2: drawn = True
        if kind == 3 and drawn:
            stats["hazard_sample_dst_after_redraw"] += 1
            hazards.append(dict(frame=iv["frame"], order=k[:20]))
        if kind == 4 and drawn:
            stats["note_src_resampled_after_redraw"] += 1

out = dict(events=len(events), intervals=len(intervals), stats=dict(stats),
           summary_last=summary[-1] if summary else None, summary_n=len(summary),
           hazard_examples=hazards[:3])
print(json.dumps(out, indent=1))
