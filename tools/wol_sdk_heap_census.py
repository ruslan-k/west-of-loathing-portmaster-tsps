#!/usr/bin/env python3
"""Read-only SDK TlsHeapCentral span walk for the pinned WoL SDK (3c5fc693...).

Offsets derive from the actual SDK WalkAllocatedPtrs_ at +0x8148c, size 500:
heap +0 page count, +8 page->Span* table; Span +0x12 sizeclass, +0x13 state,
+0x18 start, +0x20 page count. State 1 is allocated; FreePages +0x7d37c sets 2.
A state-2 snapshot is NOT proof of reclaim safety: no allocator lock, aliases or
GPU-lifetime guarantee is provided. No guest code is called and no pages mutated.
"""
import argparse
import hashlib
import json
import os
import struct
import time
from pathlib import Path
from typing import Any

PAGE=4096
HEAP_BASE=0x1000000000
MAX_HEAP=2**31
MAX_SPANS=32768


def walk_spans(read,base,max_bytes=MAX_HEAP) -> dict[str,Any]:
    header=read(base,32)
    if len(header)!=32:raise ValueError('short heap header')
    pages,table=struct.unpack_from('<QQ',header)
    if not 1<=pages<=max_bytes//PAGE:raise ValueError('heap page count out of bounds')
    end=base+pages*PAGE
    if not base<=table<=end-pages*8:raise ValueError('page table outside heap')
    entries=read(table,pages*8)
    if len(entries)!=pages*8:raise ValueError('short span table')
    spans=[];index=0
    while index<pages:
        if len(spans)>=MAX_SPANS:raise ValueError('span cap reached')
        ptr=struct.unpack_from('<Q',entries,index*8)[0]
        if not base<=ptr<=end-48:raise ValueError('span pointer outside heap')
        raw=read(ptr,48)
        if len(raw)!=48:raise ValueError('short span record')
        kind,state=raw[0x12],raw[0x13]
        address,count=struct.unpack_from('<QQ',raw,0x18)
        # Init +0x7d978 explicitly marks SDK metadata spans as state 3.
        if state not in (0,1,2,3):raise ValueError(f'unknown span state {state} at {ptr:#x}')
        if not count or address%PAGE or address<base or count>(end-address)//PAGE:
            raise ValueError('invalid span extent')
        first=(address-base)//PAGE;following=first+count
        if first!=index or not index<following<=pages:raise ValueError('nonprogressing or overlapping spans')
        if struct.unpack_from('<Q',entries,(following-1)*8)[0]!=ptr:raise ValueError('span endpoints disagree')
        spans.append(dict(descriptor=hex(ptr),address=hex(address),pages=count,sizeclass=kind,state=state))
        index=following
    return dict(heap_base=hex(base),heap_pages=pages,page_table=hex(table),spans=spans,
                header_sha256=hashlib.sha256(header).hexdigest(),reclaim_safe=False,
                caveat='Sequential read-only snapshot; no allocator lock or alias/GPU ownership proof.')


def start_ticks(pid):return int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])


def sample(pid,expected_start,expected_elf):
    begin=time.monotonic_ns()
    proc=Path('/proc')/str(pid)
    if start_ticks(pid)!=expected_start:raise RuntimeError('PID identity changed')
    if hashlib.sha256((proc/'exe').read_bytes()).hexdigest()!=expected_elf:raise RuntimeError('ELF identity mismatch')
    mem=os.open(str(proc/'mem'),os.O_RDONLY);pages_fd=os.open(str(proc/'pagemap'),os.O_RDONLY)
    try:
        def read(address,n):
            if n>8*1024*1024:raise ValueError('memory read cap')
            data=os.pread(mem,n,address)
            if len(data)!=n:raise ValueError('short process-memory read')
            return data
        result=walk_spans(read,HEAP_BASE)
        pm=os.pread(pages_fd,result['heap_pages']*8,HEAP_BASE//PAGE*8)
        if len(pm)!=result['heap_pages']*8:raise ValueError('short pagemap read')
        grouped={};changed=0
        for row in result['spans']:
            first=(int(row['address'],16)-HEAP_BASE)//PAGE;n=row['pages']
            present=swapped=0
            for (e,) in struct.iter_unpack('<Q',memoryview(pm)[first*8:(first+n)*8]):
                present+=(e>>63)&1;swapped+=(e>>62)&1
            row.update(present_pages=present,swapped_pages=swapped)
            key='free_span' if row['state']==2 else ('allocated_small' if row['state']==1 and row['sizeclass'] else ('allocated_large' if row['state']==1 else 'other'))
            g=grouped.setdefault(key,dict(spans=0,pages=0,present_pages=0,swapped_pages=0))
            for k,v in dict(spans=1,pages=n,present_pages=present,swapped_pages=swapped).items():g[k]+=v
            raw=read(int(row['descriptor'],16),48)
            addr,count=struct.unpack_from('<QQ',raw,0x18)
            if (addr,count,raw[0x12],raw[0x13])!=(int(row['address'],16),n,row['sizeclass'],row['state']):changed+=1
        result['by_state']=grouped;result['changed_descriptors']=changed
        result['header_unchanged']=hashlib.sha256(read(HEAP_BASE,32)).hexdigest()==result['header_sha256']
    finally:os.close(mem);os.close(pages_fd)
    if start_ticks(pid)!=expected_start:raise RuntimeError('PID changed during census')
    result.update(pid=pid,start_ticks=expected_start,elf_sha256=expected_elf,begin_ns=begin,end_ns=time.monotonic_ns())
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pid',type=int,required=True);ap.add_argument('--start-ticks',type=int,required=True)
    ap.add_argument('--elf-sha256',required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();doc=sample(a.pid,a.start_ticks,a.elf_sha256)
    a.out.write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps({k:v for k,v in doc.items() if k!='spans'},indent=2))

if __name__=='__main__':main()
