#!/usr/bin/env python3
"""Bounded read-only owner-process prefix observation; never read bundle payload.
Only the nonce-labelled, hash-pinned runtime is eligible. Metadata/native API
flow supplies the byte[] hypothesis; a header alone proves no GC reachability,
release, pin lifetime or reclaimable pages. No ptrace, mutation or page discard.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time


def decode_header(prefix, read_bytes) -> dict:
    if len(prefix)!=32 or read_bytes<0:
        raise ValueError('exact 32-byte prefix and nonnegative read size required')
    klass,monitor,bounds,length=struct.unpack('<4Q',prefix)
    return dict(klass=hex(klass),monitor=hex(monitor),bounds=hex(bounds),length=length,
                expected_read_bytes=read_bytes,length_matches_read=length==read_bytes,
                hypothesis='Il2CppArray prefix, not GC liveness/free proof')


def readable_range(text,address,size):
    if not 0<=address<2**64 or not 0<size<=64 or size>2**64-address:return False
    for line in text.splitlines():
        words=line.split()
        if len(words)<2 or 'r' not in words[1]:continue
        a,b=(int(x,16) for x in words[0].split('-'))
        if a<=address and address+size<=b:return True
    return False


def identity(proc):
    return (proc/'stat').read_text().rsplit(')',1)[1].split()[19]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--label',required=True);ap.add_argument('--elf-sha256',required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if not a.label.replace('-','').isalnum() or not re.fullmatch('[0-9a-f]{64}',a.elf_sha256):ap.error('exact label/hash required')
    deadline=time.monotonic()+150;proc=None;start=None;text='';nonce=('WOL_BUNDLE_HEADER_RUN='+a.label).encode()
    while time.monotonic()<deadline and proc is None:
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                if (p/'comm').read_text().strip()=='wol-horizon' and nonce in (p/'environ').read_bytes().split(b'\0'):
                    if hashlib.sha256((p/'exe').read_bytes()).hexdigest()!=a.elf_sha256:raise RuntimeError('wrong runtime')
                    candidate_start=identity(p);proc=p;start=candidate_start;break
            except (OSError,ProcessLookupError):pass
        if proc is None:time.sleep(.2)
    if proc is None or start is None:raise RuntimeError('eligible owned process not found within deadline')
    result: dict = dict(label=a.label,pid=int(proc.name),start_ticks=start,elf_sha256=a.elf_sha256,samples=[],
                scope='read-only mapped prefix/name strings, <=64 bytes/read; no payload, writes, roots or frees inferred')
    def save():a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    save();log=Path('/mnt/SDCARD/Roms/PORTS/wol-switch/logs/latest.log');read=None
    while time.monotonic()<deadline:
        if identity(proc)!=start:raise RuntimeError('owned process identity changed')
        text=log.read_text(errors='replace')
        for line in text.splitlines():
            if not line.startswith('WOL_ROMFS_BUFFER '):continue
            row=dict(re.findall(r'([\w-]+)=([^\s]+)',line))
            if 100000000<int(row.get('bytes','0'),0)<=1073741824:
                read=row;break
        if read:break
        time.sleep(.2)
    if not read:raise RuntimeError('no large source-read observation within deadline')
    data=int(read['address'],0);size=int(read['bytes'],0)
    if data<32:raise RuntimeError('invalid prefix address')
    result['romfs_read']=read;result['SDK_containing_allocations']=[]
    for line in text.splitlines():
        if not line.startswith('WOL_ALLOC event=alloc '):continue
        row=dict(re.findall(r'([\w-]+)=([^\s]+)',line));p=int(row['ptr'],0);n=int(row['bytes'],0)
        if p<=data and size<=p+n-data:result['SDK_containing_allocations'].append(row)
    fd=os.open(str(proc/'mem'),os.O_RDONLY)
    def mem(address,n):
        if not readable_range((proc/'maps').read_text(),address,n):raise ValueError('unreadable mapped range')
        b=os.pread(fd,n,address)
        if len(b)!=n:raise ValueError('short prefix read')
        return b
    def string(address):
        raw=mem(address,64);end=raw.find(b'\0')
        if end<0:raise ValueError('no bounded string')
        return raw[:end].decode('utf-8',errors='strict')
    observed=time.monotonic()
    try:
        for delay in (0,10,60):
            while time.monotonic()<observed+delay:
                if time.monotonic()>=deadline:raise RuntimeError('sample deadline')
                time.sleep(.2)
            if identity(proc)!=start:raise RuntimeError('owned process identity changed')
            sample: dict = dict(monotonic_ns=time.monotonic_ns(),seconds_since_read_observed=delay)
            try:
                header=decode_header(mem(data-32,32),size);sample['prefix']=header
                nameptr,nsptr=struct.unpack('<2Q',mem(int(header['klass'],0)+16,16))
                name,namespace=string(nameptr),string(nsptr)
                sample['class_name']=name if name in ('Byte[]','Byte') else 'other/unresolved'
                sample['class_namespace']=namespace if namespace in ('System','') else 'other/unresolved'
                sample['byte_array_header_consistent']=header['length_matches_read'] and name=='Byte[]' and namespace=='System'
            except (OSError,ValueError) as e:sample['unavailable']=str(e)
            result['samples'].append(sample);save()
        result['complete']=True;save()
    finally:os.close(fd)
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
