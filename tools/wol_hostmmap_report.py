#!/usr/bin/env python3
"""Aggregate a WOL host-allocation shim log: who requests what, at or above the threshold."""
import re
import sys
from collections import Counter
from pathlib import Path

LINE = re.compile(
    r"^HOSTMMAP ts=(?P<ts>\d+) op=(?P<op>\w+) pid=(?P<pid>\d+) size=(?P<size>\d+)"
    r"(?P<extra>.*?) ret=(?P<ret>\S+) frames=(?P<frames>.*);$")


class Request:
    __slots__ = ("op", "size", "count", "pids", "first", "last")

    def __init__(self, op, size):
        self.op = op
        self.size = size
        self.count = 0
        self.pids = set()
        self.first = None
        self.last = None


def parse(text):
    records = []
    for line in text.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        records.append(dict(ts=int(m.group("ts")), op=m.group("op"), pid=int(m.group("pid")),
                            size=int(m.group("size")), extra=m.group("extra"),
                            ret=m.group("ret"), frames=[f for f in m.group("frames").split(";") if f]))
    return records


def aggregate(records, pid=None):
    requests = {}
    for r in records:
        if pid is not None and r["pid"] != pid:
            continue
        key = (r["op"], r["size"])
        entry = requests.get(key)
        if entry is None:
            entry = Request(r["op"], r["size"])
            requests[key] = entry
        entry.count += 1
        entry.pids.add(r["pid"])
        if entry.first is None:
            entry.first = r
        entry.last = r
    out = []
    for entry in sorted(requests.values(), key=lambda e: (-e.size, e.op)):
        out.append(dict(op=entry.op, size=entry.size, count=entry.count, pids=sorted(entry.pids),
                        first_ts=entry.first["ts"], first_ret=entry.first["ret"],
                        first_frames=entry.first["frames"],
                        first_extra=entry.first["extra"].strip(),
                        last_ts=entry.last["ts"]))
    return out


def totals(records, pid=None):
    rows = [r for r in records if pid is None or r["pid"] == pid]
    return dict(requests=len(rows), by_op=dict(Counter(r["op"] for r in rows)),
                pids=sorted({r["pid"] for r in rows}))


def main(argv):
    path = Path(argv[1])
    records = parse(path.read_text())
    pid = int(argv[2]) if len(argv) > 2 else None
    print("TOTALS", totals(records, pid))
    for row in aggregate(records, pid):
        print(f"{row['size']:>12} {row['op']:<9} x{row['count']:<3} pid={row['pids']} "
              f"frames={' | '.join(row['first_frames'][:4])} {row['first_extra']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
