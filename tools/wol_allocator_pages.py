#!/usr/bin/env python3
"""Bounded read-only page-union census; allocator history is NOT free ownership.

Classifies guest VMA pages by live SDK request, historical request without a tracked
live owner, or unseen by this trace. Never reads guest contents or modifies pages.
The historical class can contain allocator metadata or sub-threshold reuse and is NOT
safe to discard. Pagemap is sampled after the log snapshot, not atomically with guest.
"""
import re
import struct


class AllocationCoverage:
    def __init__(self,start,end,page_size=4096):
        if start<0 or end<=start or start%page_size or end%page_size or end-start>2**31:
            raise ValueError('bounded aligned arena required')
        self.start=start;self.end=end;self.page_size=page_size
        self.ever=bytearray((end-start)//page_size)
        self.live={};self.incomplete=False;self.last_seq=0;self.last_ns=None;self.events=0
        self.max_live=8192

    def indices(self,ptr,size):
        if size<0 or ptr<0 or size>2**32:return (0,0)
        lo=max(self.start,ptr);hi=min(self.end,ptr+size)
        if hi<=lo:return (0,0)
        return ((lo-self.start)//self.page_size,(hi-self.start+self.page_size-1)//self.page_size)

    def feed(self,line):
        if line.startswith('WOL_ALLOC_OVERFLOW '):self.incomplete=True;return
        if not line.startswith('WOL_ALLOC '):return
        fields=dict(re.findall(r'([\w-]+)=([^\s]+)',line))
        try:
            seq=int(fields['seq'],0);ptr=int(fields['ptr'],0);size=int(fields['bytes'],0)
            self.incomplete |= bool(int(fields.get('incomplete','0'),0))
            if seq!=self.last_seq+1:self.incomplete=True
            self.last_seq=seq;self.events+=1
            if 'ns' in fields:self.last_ns=int(fields['ns'],0)
        except (KeyError,ValueError):self.incomplete=True;return
        if fields.get('event') in ('alloc','realloc'):
            if ptr in self.live and fields['event']!='realloc':self.incomplete=True
            if len(self.live)>=self.max_live:self.incomplete=True;return
            self.live[ptr]=size
            lo,hi=self.indices(ptr,size)
            self.ever[lo:hi]=b'\1'*(hi-lo)
        elif fields.get('event')=='free':
            old=self.live.pop(ptr,None)
            if old!=size:self.incomplete=True
        else:self.incomplete=True

    def live_mask(self):
        mask=bytearray(len(self.ever))
        for ptr,size in self.live.items():
            lo,hi=self.indices(ptr,size);mask[lo:hi]=b'\1'*(hi-lo)
        return mask


def classify_pages(coverage,entries):
    """`entries` starts at the arena's pagemap offset; read in chunks <=64 KiB."""
    live=coverage.live_mask()
    classes={k:dict(pages=0,present=0,swapped=0) for k in ('live','historical_not_live','unseen')}
    for off in range(0,len(live),8192):
        n=min(8192,len(live)-off)
        data=entries.read(n*8)
        if len(data)!=n*8:raise ValueError('short pagemap read')
        for j,(entry,) in enumerate(struct.iter_unpack('<Q',data)):
            i=off+j
            name='live' if live[i] else ('historical_not_live' if coverage.ever[i] else 'unseen')
            c=classes[name];c['pages']+=1;c['present']+=(entry>>63)&1;c['swapped']+=(entry>>62)&1
    return dict(start=hex(coverage.start),end=hex(coverage.end),page_size=coverage.page_size,
                classes=classes,trace_incomplete=coverage.incomplete,events=coverage.events,
                last_seq=coverage.last_seq,last_event_ns=coverage.last_ns,live_allocations=len(coverage.live),
                reclaim_safe=False,caveat='Historical-only is not allocator-free: metadata/sub-threshold reuse/aliases remain unknown; log and pagemap are sequential, not atomic.')
