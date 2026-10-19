#!/usr/bin/env python3
"""Read-only report for the lowered-threshold SDK allocator census (WOL_ALLOC_MIN).

Consumes a wol_roadmap_probe receipt with `block_samples` (pagemap residency of live
WOL_ALLOC blocks at the log's own threshold) and produces the size-band table, the
caller aggregation join and the arena attribution cross-checks. No reclaim is inferred.

Usage: wol_allocmin_report.py <receipt.json> [--out summary.json]
"""
from pathlib import Path
import argparse
import json

BANDS=[(1<<18,1<<19),(1<<19,1<<20),(1<<20,1<<22),(1<<22,1<<24),(1<<24,1<<26),(1<<26,1<<63)]


def bands(blocks):
    rows=[]
    for lo,hi in BANDS:
        sel=[b for b in blocks if 'present_kib' in b and lo<=b['requested_kib']*1024<hi]
        rows.append(dict(lo_bytes=lo,hi_bytes=hi,blocks=len(sel),
            requested_mib=round(sum(b['requested_kib'] for b in sel)/1024,1),
            present_mib=round(sum(b['present_kib'] for b in sel)/1024,1),
            swapped_mib=round(sum(b['swapped_kib'] for b in sel)/1024,1)))
    return rows


def totals(blocks):
    sel=[b for b in blocks if 'present_kib' in b]
    return dict(blocks=len(sel),errors=sum(1 for b in blocks if 'error' in b),
        requested_mib=round(sum(b['requested_kib'] for b in sel)/1024,1),
        present_mib=round(sum(b['present_kib'] for b in sel)/1024,1),
        swapped_mib=round(sum(b['swapped_kib'] for b in sel)/1024,1))


def arena_join(vma_entries,blocks):
    """Split each >=1 GiB arena VMA's swapped bytes into tracked-block vs unattributed."""
    out=[]
    for a in vma_entries:
        if a['size_mib']<1024:continue
        lo,hi=int(a['start'],16),int(a['end'],16)
        inside=[b for b in blocks if 'present_kib' in b and lo<=int(b['ptr'],16)<hi]
        swapped=sum(b['swapped_kib'] for b in inside)/1024
        out.append(dict(arena=f"{a['start']}..{a['end']}",arena_size_mib=a['size_mib'],
            arena_swap_mib=a['swap_mib'],tracked_inside=len(inside),
            tracked_inside_present_mib=round(sum(b['present_kib'] for b in inside)/1024,1),
            tracked_inside_swapped_mib=round(swapped,1),
            unattributed_swap_mib=round(a['swap_mib']-swapped,1)))
    return out


def report(receipt):
    out={}
    for tag,v in receipt.get('block_samples',{}).items():
        if 'error' in v or 'blocks' not in v:continue
        blocks=v['blocks']
        out[tag]=dict(threshold_bytes=v.get('threshold_bytes'),live_blocks=v.get('live_blocks'),
            sampled=v.get('sampled'),truncated=v.get('truncated'),
            by_caller=v.get('by_caller'),bands=bands(blocks),totals=totals(blocks))
        vma=receipt.get('vma_samples',{}).get(tag,{})
        if 'top_by_swap' in vma:
            present=sum(b['present_kib'] for b in blocks if 'present_kib' in b)/1024
            swapped=sum(b['swapped_kib'] for b in blocks if 'present_kib' in b)/1024
            out[tag]['swap_cross_check']=dict(process_swap_pss_mib=vma['totals']['swap_pss_mib'],
                tracked_swapped_mib=round(swapped,1),
                outside_tracked_swap_mib=round(vma['totals']['swap_pss_mib']-swapped,1),
                process_pss_mib=vma['totals']['pss_mib'],tracked_present_mib=round(present,1),
                arena=arena_join(vma['top_by_swap'],blocks))
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('receipt',type=Path)
    ap.add_argument('--out',type=Path)
    a=ap.parse_args()
    receipt=json.loads(a.receipt.read_text())
    doc=dict(schema=1,label=receipt.get('label'),runtime_sha256=receipt.get('runtime_sha256'),
             phases=report(receipt))
    text=json.dumps(doc,indent=2)+'\n'
    if a.out:a.out.write_text(text)
    print(text,end='')


if __name__=='__main__':main()
