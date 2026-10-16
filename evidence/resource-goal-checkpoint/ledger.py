#!/usr/bin/env python3
"""Read only runtime descriptor BSS; never guest texture bytes or live assets.
Layout is compiled from the exact native struct declarations and tied to ELF symbols.
Best-effort unlocked snapshot: exclude texture identities changing between reads.
GPU byte counts are estimates of explicit host image extents, NOT driver allocation.
"""
from pathlib import Path
import collections,hashlib,json,os,struct,sys,time
pid=int(sys.argv[1]);out=Path(sys.argv[2]);layout=json.loads(Path(sys.argv[3]).read_text())
p=Path('/proc')/str(pid)
def identity():return (p/'stat').read_text().rsplit(')',1)[1].split()[19]
start=identity();exe=os.readlink(p/'exe');maps=(p/'maps').read_text().splitlines()
base=next(int(l.split()[0].split('-')[0],16)-int(l.split()[2],16) for l in maps if l.split()[-1]==exe and int(l.split()[2],16)==0)
fd=os.open(p/'mem',os.O_RDONLY)
def read(address,size):
 b=os.pread(fd,size,address);assert len(b)==size,(hex(address),size,len(b));return b
def field(raw,kind,name):
 o,s=layout[kind][name];return int.from_bytes(raw[o:o+s],'little')
syms=layout['symbols'];high=int.from_bytes(read(base+syms['nvn_textures_high']['offset'],4),'little');assert 0<high<=4096
size=layout['texture_size'];address=base+syms['nvn_textures']['offset'];raw=read(address,size*high)
rows=[];changed=0
for i in range(high):
 b=raw[i*size:(i+1)*size]
 if not field(b,'texture','live'):continue
 b2=read(address+i*size,size)
 if any(field(b,'texture',k)!=field(b2,'texture',k) for k in ('id','object','live')):changed+=1;continue
 r={k:field(b,'texture',k) for k in layout['texture']};r['slot']=i
 assert 0<r['b.width']<=16384 and 0<r['b.height']<=16384 and 0<r['b.levels']<=14,r
 r['guest_span']=[r['b.pool'],r['b.offset'],r['size']]
 # Default backend materializes color/BC images as RGBA; special float formats use 8/16 bytes.
 fmt=r['b.format'];bpp=2 if r['host_upload_type'] in (0x8033,0x8034) else 8 if fmt in (5,0x11,0x29) else 16 if fmt in (0xa,0x16,0x2e,0x12,0x2a) else 4
 w=r['host_width'] if r['host_scaled'] else r['b.width'];h=r['host_height'] if r['host_scaled'] else r['b.height'];estimated=0
 for level in range(r['b.levels']):estimated+=max(1,w>>level)*max(1,h>>level)*bpp
 if r['b.target']==8:estimated*=6
 r['host_uncompressed_estimate_bytes']=estimated if (r['name'] or r['depth_buffer']) and not r['zero_backend_deferred'] else 0
 rows.append(r)
ps=layout['pool_size'];rawp=read(base+syms['nvn_pools']['offset'],ps*256);pools=[]
for i in range(256):
 b=rawp[i*ps:(i+1)*ps];r={k:field(b,'pool',k) for k in layout['pool']}
 if r['live'] or r['references']:pools.append(r)
os.close(fd);assert identity()==start
# Deduplicate host resources by GL texture/renderbuffer name; do not add CPU aliases twice.
unique={}
for r in rows:
 key=('tex',r['name']) if r['name'] else ('depth',r['depth_buffer'])
 if any(key[1:]):unique.setdefault(key,r)
by_format={}
for r in rows:
 k=hex(r['b.format']);f=by_format.setdefault(k,dict(objects=0,guest_view_bytes=0,host_uncompressed_estimate_bytes=0))
 f['objects']+=1;f['guest_view_bytes']+=r['size']
for r in unique.values():by_format[hex(r['b.format'])]['host_uncompressed_estimate_bytes']+=r['host_uncompressed_estimate_bytes']
result=dict(schema=1,pid=pid,start_ticks=start,sampled_monotonic=time.monotonic(),layout=layout,texture_objects=len(rows),changed_identities_excluded=changed,
 unique_host_resources=len(unique),host_uncompressed_estimate_bytes=sum(r['host_uncompressed_estimate_bytes'] for r in unique.values()),
 borrowed_pool_virtual_bytes=sum(r['size'] for r in pools if not r['owned']),owned_pool_virtual_bytes=sum(r['size'] for r in pools if r['owned']),
 formats=by_format,top_textures=sorted(rows,key=lambda r:r['host_uncompressed_estimate_bytes'],reverse=True)[:25],textures=rows,pools=pools,
 caveats=['Borrowed pools alias the guest address space; virtual bytes are not live RAM.', 'GPU estimates exclude driver tiling/padding and may overlap RSS; do not add blindly.', 'No driver GPU allocation measurement is available from this snapshot.', 'Unlocked descriptor observation; no texture pixels or guest heaps were read.'])
out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:result[k] for k in ('texture_objects','unique_host_resources','host_uncompressed_estimate_bytes','borrowed_pool_virtual_bytes','owned_pool_virtual_bytes','formats')},indent=2))
