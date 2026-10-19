#!/usr/bin/env python3
"""Owner-device smoke collector using the established /mnt/UDISK/session.py principal helper.
Refuses a preexisting game; preserves the active save; every injected hold <=2000ms.
"""
from pathlib import Path
import argparse
import hashlib
import json
import gzip
import os
import shutil
import subprocess
import sys
from wol_memory_benchmark import stop_owned
from wol_memory_profile import stat_identity
from wol_present_watchdog import PresentationStall, require_progress
import time
import struct
import zlib
import re


BLOCK_MIN_BYTES=4*1024*1024
BLOCK_MAX_BYTES=1024*1024*1024
BLOCK_SAMPLE_LIMIT=2048
BLOCK_DETAIL_LIMIT=512
CALLER_LIMIT=40


def alloc_event(line,live):
    """Apply one WOL_ALLOC log line to the live-block map: ptr -> (bytes, caller)."""
    row=dict(re.findall(r'([\w-]+)=([^\s]+)',line))
    if 'ptr' not in row or 'bytes' not in row:
        return
    try:
        ptr=int(row['ptr'],0);n=int(row['bytes'],0)
    except ValueError:
        return
    if row.get('event')=='free':
        live.pop(ptr,None)
    elif row.get('event') in ('alloc','realloc'):
        live[ptr]=(n,row.get('caller'))


def block_list(live,min_bytes,max_bytes):
    return sorted(((p,n,c) for p,(n,c) in live.items() if min_bytes<=n<=max_bytes),key=lambda x:-x[1])


def live_blocks(text,min_bytes=BLOCK_MIN_BYTES,max_bytes=BLOCK_MAX_BYTES):
    live={}
    for line in text.splitlines():
        if line.startswith('WOL_ALLOC '):
            alloc_event(line,live)
    return block_list(live,min_bytes,max_bytes)


def trace_threshold(text,default=BLOCK_MIN_BYTES):
    """Adopt the WOL_ALLOC_TRACE header's own threshold so the census matches what was logged."""
    for line in text.splitlines():
        if line.startswith('WOL_ALLOC_TRACE enabled=1'):
            match=re.search(r'threshold=(\d+)',line)
            if match:
                value=int(match.group(1))
                return value if 16384<=value<=BLOCK_MAX_BYTES else default
    return default


def scan_log(path,max_bytes=BLOCK_MAX_BYTES):
    """Single streaming pass over the runtime log: (live blocks, trace threshold).

    The streaming form keeps the device-side memory cost bounded and applies the log's
    own threshold; a missing/invalid header falls back to the >=4 MiB read-only default.
    """
    live={};threshold=None
    with Path(path).open('r',errors='replace') as f:
        for line in f:
            if line.startswith('WOL_ALLOC_TRACE enabled=1'):
                match=re.search(r'threshold=(\d+)',line)
                if match:
                    threshold=int(match.group(1))
            elif line.startswith('WOL_ALLOC '):
                alloc_event(line,live)
    if threshold is None or not 16384<=threshold<=max_bytes:
        threshold=BLOCK_MIN_BYTES
    return block_list(live,threshold,max_bytes),threshold


def aggregate_callers(samples):
    """Group sampled live blocks by their WOL_ALLOC caller site, biggest swap first."""
    by={}
    for sample in samples:
        if 'present_kib' not in sample:
            continue
        caller=sample.get('caller') or '[unattributed]'
        row=by.setdefault(caller,dict(caller=caller,blocks=0,requested_kib=0,present_kib=0,swapped_kib=0))
        row['blocks']+=1
        row['requested_kib']+=sample['requested_kib']
        row['present_kib']+=sample['present_kib']
        row['swapped_kib']+=sample['swapped_kib']
    return sorted(by.values(),key=lambda row:(-row['swapped_kib'],-row['requested_kib']))[:CALLER_LIMIT]


def decode_pagemap(data):
    if len(data)%8:
        raise ValueError('pagemap read is not a whole number of entries')
    counts=dict(present=0,swapped=0,file_or_shared=0,exclusive=0)
    for i in range(0,len(data),8):
        e=int.from_bytes(data[i:i+8],'little')
        counts['present']+=(e>>63)&1
        counts['swapped']+=(e>>62)&1
        counts['file_or_shared']+=(e>>61)&1
        counts['exclusive']+=(e>>60)&1
    return dict(pages=len(data)//8,**counts)


def parse_smaps(text):
    rows=[];cur=None
    for line in text.splitlines():
        if re.match(r'^[0-9a-f]+-[0-9a-f]+ ',line):
            parts=line.split(None,5)
            fields=parts[0].split('-')
            cur=dict(start=int(fields[0],16),end=int(fields[1],16),perms=parts[1],
                     path=(parts[5] if len(parts)>5 else ''),
                     size_kib=(int(fields[1],16)-int(fields[0],16))//1024,
                     rss_kib=0,pss_kib=0,swap_kib=0)
            rows.append(cur);continue
        if cur is None:continue
        if line.startswith('Rss:'):cur['rss_kib']=int(line.split()[1])
        elif line.startswith('Pss:'):cur['pss_kib']=int(line.split()[1])
        elif line.startswith('SwapPss:'):cur['swap_kib']=int(line.split()[1])
    return rows


def kms_rgb_signal(path):
    """Reject the transient all-black RGB8 scanout emitted during MainUI startup.

    This is only a signal gate; the final KMS frame still needs scene review.
    For non-interlaced RGB8, a black image has zero residuals for every PNG filter.
    """
    data=path.read_bytes()
    if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data)>16*1024*1024:return False
    pos=8;parts=[];shape=None
    while pos+12<=len(data):
        n=struct.unpack_from('>I',data,pos)[0]
        if n>len(data)-pos-12:return False
        kind=data[pos+4:pos+8];body=data[pos+8:pos+8+n];pos+=12+n
        if kind==b'IHDR':
            if len(body)!=13:return False
            shape=struct.unpack('>IIBBBBB',body)
        if kind==b'IDAT':parts.append(body)
    if not shape:return False
    w,h,b,c,compression,filtering,interlace=shape
    if not (0<w<=4096 and 0<h<=4096 and (b,c,compression,filtering,interlace)==(8,2,0,0,0)):return False
    stride=3*w+1;expected=stride*h
    decoder=zlib.decompressobj();raw=decoder.decompress(b''.join(parts),expected+1)
    if len(raw)!=expected or not decoder.eof:return False
    if any(raw[y*stride]>4 for y in range(h)):return False
    return any(any(raw[y*stride+1:(y+1)*stride]) for y in range(h))


def pids(name):
    out=[]
    for p in Path('/proc').iterdir():
        try:
            if p.name.isdecimal() and (p/'comm').read_text().strip()==name:
                out.append(int(p.name))
        except OSError:
            pass
    return out


def hashes(path):
    return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--label',required=True)
    ap.add_argument('--layout',type=Path,required=True)
    ap.add_argument('--control-save',type=Path)
    ap.add_argument('--route',type=Path,help='bounded data-free action list; requested actions are not observed scenes')
    ap.add_argument('--ordinary-title',action='store_true',help='unaltered launcher environment; title-only, no injected input')
    ap.add_argument('--guest-pages',action='store_true',help='heavy diagnostic pagemap snapshots; not an FPS benchmark')
    ap.add_argument('--draw-trace',action='store_true',help='per-draw tracing for one short screen (heavy log, not an FPS arm)')
    ap.add_argument('--present-watchdog',type=float,default=0,help='opt-in 5..30s present-progress budget; requires MOMO_FRAME_CLOCK=1')
    ap.add_argument('--stall-gdb',action='store_true',help='on stall only: bounded backtrace of the exact owned PID, no memory dump')
    ap.add_argument('--block-pages',action='store_true',help='read-only pagemap residency of >=4MiB live WOL_ALLOC blocks at game-idle and before cleanup')
    ap.add_argument('--vma-swap',action='store_true',help='read-only per-VMA Pss/SwapPss census at game-idle and before cleanup')
    ap.add_argument('--allocation-pages',action='store_true',help='heavy read-only page union: live/historical-not-live/unseen SDK spans; not free ownership or an FPS run')
    ap.add_argument('--sdk-heap',action='store_true',help='read-only pinned SDK heap-span census with separate allocator-free vs allocated residency; no reclaim')
    a=ap.parse_args()
    if a.present_watchdog and (not 5<=a.present_watchdog<=30 or a.ordinary_title):
        ap.error('watchdog requires diagnostic mode and a finite 5..30 second budget')
    route=json.loads(a.route.read_text()) if a.route else None
    if route is not None:
        if not isinstance(route,list) or not 1<=len(route)<=24:ap.error('route must have 1..24 actions')
        for action in route:
            if not action['label'].replace('-','').isalnum() or not 1<=action['hold_ms']<=2000 or not 1<=action['wait_s']<=30:
                ap.error('invalid route action')
            if int(action['buttons'],0)&0xc00==0xc00:ap.error('exit chord refused')
    if not a.label.replace('-','').isalnum():
        ap.error('simple label required')
    if pids('wol-horizon') or len(pids('MainUI'))!=1:
        raise RuntimeError('device is not idle; never interrupt an unowned session')
    root=Path('/mnt/SDCARD/Roms/PORTS/wol-switch')
    out=Path('/mnt/UDISK')/('roadmap-v2-'+a.label)
    out.mkdir(exist_ok=False)
    save=root/'save-laboratory'
    backup=out/'owner-save'
    shutil.copytree(save,backup)
    receipt: dict = dict(label=a.label,owner_save_hashes=hashes(backup),stages=[],cleanup_verified=False,
                 probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 session_sha256=hashlib.sha256(Path('/mnt/UDISK/session.py').read_bytes()).hexdigest(),
                 launcher_sha256=hashlib.sha256((root.parent/'West of Loathing Switch.sh').read_bytes()).hexdigest(),
                 layout_sha256=hashlib.sha256(a.layout.read_bytes()).hexdigest(),
                 ordinary_title_only=a.ordinary_title,
                 draw_trace=a.draw_trace,
                 phase_labels_are_requests_not_scene_classifications=True,
                 heavy_guest_page_sampling=a.guest_pages)
    receipt['present_watchdog_s']=a.present_watchdog
    receipt['progress_checks']=0
    ledger=None
    launch=None
    owned=None
    def stage(name):
        (out/'phase.txt').write_text(name)
        receipt['stages'].append(dict(name=name,t_ns=time.monotonic_ns()))
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def cmd(*args):
        subprocess.run([sys.executable,'/mnt/UDISK/session.py',*args],check=True)
        check_progress()
    def stall_diagnostics(error):
        receipt['failure']=dict(kind='presentation-stall',observation=error.observation)
        dest=out/'stall';dest.mkdir(exist_ok=True)
        if not owned:return
        proc=Path('/proc')/str(owned[0])
        if stat_identity(proc)['start_ticks']!=owned[1]:
            receipt['failure']['diagnostics_refused']='PID/start-time changed';return
        for name in ('maps','status','smaps_rollup'):
            try:(dest/name).write_text((proc/name).read_text())
            except OSError as e:(dest/(name+'-error')).write_text(str(e))
        tasks=[]
        for task in sorted((proc/'task').iterdir(),key=lambda p:int(p.name))[:512]:
            row: dict = {'tid':int(task.name)}
            for name in ('comm','wchan','stack','syscall'):
                try:row[name]=(task/name).read_text()[:16384]
                except OSError as e:row[name]={'unavailable':str(e)}
            tasks.append(row)
        (dest/'tasks.json').write_text(json.dumps(tasks,indent=2)+'\n')
        gdb=shutil.which('gdb')
        if a.stall_gdb and gdb:
            try:
                with (dest/'gdb.txt').open('w') as f:
                    r=subprocess.run([gdb,'-nx','-batch','-p',str(owned[0]),'-ex','set pagination off',
                        '-ex','set print frame-arguments none','-ex','info threads',
                        '-ex','thread apply all bt 12','-ex','detach'],stdout=f,stderr=subprocess.STDOUT,timeout=20)
                receipt['failure']['gdb_exit']=r.returncode
            except subprocess.TimeoutExpired:receipt['failure']['gdb_timeout']=True
        receipt['failure']['diagnostic_dir']=str(dest)
    def check_progress():
        if not a.present_watchdog or not owned:return
        log=root/'logs/latest.log'
        with log.open('rb') as f:
            f.seek(0,2);f.seek(max(0,f.tell()-262144));tail=f.read(262144).decode(errors='replace')
        try:
            receipt['last_progress_observation']=require_progress(tail,time.monotonic_ns(),a.present_watchdog)
            receipt['progress_checks']+=1
        except PresentationStall as e:
            try:stall_diagnostics(e)
            except Exception as diagnostic_error:
                receipt['failure']=dict(kind='presentation-stall',observation=e.observation,diagnostic_error=str(diagnostic_error))
            raise
    def pause(seconds):
        if not a.present_watchdog:time.sleep(seconds);return
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            check_progress();time.sleep(min(1,max(0,deadline-time.monotonic())))
    def sample_blocks(tag):
        if not a.block_pages or not owned:return
        if stat_identity(Path('/proc')/str(owned[0]))['start_ticks']!=owned[1]:
            receipt.setdefault('block_samples',{})[tag]=dict(error='PID/start-time changed');return
        try:candidates,min_bytes=scan_log(root/'logs/latest.log')
        except OSError as e:
            receipt.setdefault('block_samples',{})[tag]=dict(error=str(e));return
        truncated=len(candidates)>BLOCK_SAMPLE_LIMIT
        samples=[]
        try:
            fd=os.open('/proc/%d/pagemap'%owned[0],os.O_RDONLY)
            try:
                for ptr,n,caller in candidates[:BLOCK_SAMPLE_LIMIT]:
                    try:
                        data=os.pread(fd,(n//4096)*8,(ptr//4096)*8)
                        if len(data)!=(n//4096)*8:raise OSError('short pagemap read')
                        counts=decode_pagemap(data)
                        samples.append(dict(ptr=hex(ptr),requested_kib=n//1024,caller=caller,
                            present_kib=counts['present']*4,swapped_kib=counts['swapped']*4,
                            file_or_shared_kib=counts['file_or_shared']*4,exclusive_kib=counts['exclusive']*4))
                    except (OSError,ValueError) as e:
                        samples.append(dict(ptr=hex(ptr),requested_kib=n//1024,caller=caller,error=str(e)))
            finally:os.close(fd)
        except OSError as e:
            receipt.setdefault('block_samples',{})[tag]=dict(error=str(e));return
        receipt.setdefault('block_samples',{})[tag]=dict(
            method='pagemap present/swapped bits per 4KiB page; requested bytes are allocator requests, not physical pages; caller is the WOL_ALLOC request site; no reclaim inferred',
            threshold_bytes=min_bytes,live_blocks=len(candidates),sampled=len(samples),truncated=truncated,
            by_caller=aggregate_callers(samples),blocks=samples[:BLOCK_DETAIL_LIMIT])
    def sample_allocation_pages(tag,rows):
        if not a.allocation_pages or not owned:return
        from wol_allocator_pages import AllocationCoverage, classify_pages
        started=time.monotonic_ns()
        proc=Path('/proc')/str(owned[0])
        if stat_identity(proc)['start_ticks']!=owned[1]:raise RuntimeError('allocation-pages PID changed')
        results=[]
        # Only >=32 MiB readable guest-heap VMAs (<=64 slices in the 2 GiB heap).
        arenas=[r for r in rows if 0x1000000000<=r['start']<r['end']<=0x1080000000 and r['size_kib']>=32768 and r['perms'].startswith('rw')]
        for arena in arenas:
            coverage=AllocationCoverage(arena['start'],arena['end'])
            with (root/'logs/latest.log').open('rb') as log:
                size=os.fstat(log.fileno()).st_size
                while log.tell()<size:
                    line=log.readline(min(65536,size-log.tell()))
                    if not line:break
                    if line.startswith((b'WOL_ALLOC ',b'WOL_ALLOC_OVERFLOW ')):
                        coverage.feed(line.decode(errors='replace'))
            with (proc/'pagemap').open('rb',buffering=0) as pages:
                pages.seek((arena['start']//4096)*8)
                result=classify_pages(coverage,pages)
                result['vma_pss_kib']=arena['pss_kib'];result['vma_swap_pss_kib']=arena['swap_kib']
                results.append(result)
        if stat_identity(proc)['start_ticks']!=owned[1]:raise RuntimeError('allocation-pages PID changed after sample')
        receipt.setdefault('allocation_pages',{})[tag]=dict(begin_ns=started,end_ns=time.monotonic_ns(),arenas=results)
    def sample_vma(tag):
        if not (a.vma_swap or a.allocation_pages or a.sdk_heap) or not owned:return
        if a.sdk_heap and tag in ('game-idle','precleanup'):
            from wol_sdk_heap_census import sample as sdk_sample
            try:
                sdk=sdk_sample(owned[0],owned[1],receipt['runtime_sha256'])
                (out/('sdk-heap-'+tag+'.json')).write_text(json.dumps(sdk,indent=2)+'\n')
                receipt.setdefault('sdk_heap',{})[tag]={k:v for k,v in sdk.items() if k!='spans'}
                receipt['sdk_heap'][tag]['top_swapped_spans']=sorted(sdk['spans'],key=lambda r:-r['swapped_pages'])[:16]
            except (OSError,ValueError,RuntimeError) as error:
                receipt.setdefault('sdk_heap',{})[tag]=dict(error=str(error),reclaim_safe=False)
        if stat_identity(Path('/proc')/str(owned[0]))['start_ticks']!=owned[1]:
            receipt.setdefault('vma_samples',{})[tag]=dict(error='PID/start-time changed');return
        try:text=(Path('/proc')/str(owned[0])/'smaps').read_text(errors='replace')
        except OSError as e:
            receipt.setdefault('vma_samples',{})[tag]=dict(error=str(e));return
        rows=parse_smaps(text)
        def label(r):
            if r['path']:return r['path']
            return '[anon %s]'%r['perms']
        top=sorted(rows,key=lambda r:r['swap_kib'],reverse=True)[:20]
        def peek(address,count=64):
            try:
                fd=os.open('/proc/%d/mem'%owned[0],os.O_RDONLY)
                try:
                    data=os.pread(fd,count,address)
                finally:os.close(fd)
            except OSError as e:
                return dict(error=str(e))
            if not data:return dict(error='empty read')
            if all(b==0 for b in data):kind='all-zero'
            elif len(set(data))<=2:kind='single-byte-repeat'
            else:kind='mixed'
            return dict(kind=kind,first16=data[:16].hex(),last16=data[-16:].hex())
        for r in top:
            if r['size_kib']>=32768 and r['swap_kib']>=8192:
                r['sample_head']=peek(r['start'])
                r['sample_tail']=peek(r['end']-64)
                r['sampled_bytes']=128
        receipt.setdefault('vma_samples',{})[tag]=dict(
            method='per-VMA Pss/SwapPss from /proc/<pid>/smaps; overlaps and shared pages are not summed as physical totals',
            totals=dict(vmas=len(rows),rss_mib=round(sum(r['rss_kib'] for r in rows)/1024,1),
                        pss_mib=round(sum(r['pss_kib'] for r in rows)/1024,1),
                        swap_pss_mib=round(sum(r['swap_kib'] for r in rows)/1024,1)),
            top_by_swap=[dict(start=hex(r['start']),end=hex(r['end']),size_mib=round(r['size_kib']/1024,1),
                              perms=r['perms'],path=label(r),rss_mib=round(r['rss_kib']/1024,1),
                              pss_mib=round(r['pss_kib']/1024,1),swap_mib=round(r['swap_kib']/1024,1),
                              **{k:r[k] for k in ('sample_head','sample_tail','sampled_bytes') if k in r}) for r in top])
        sample_allocation_pages(tag,rows)
    try:
        if a.control_save:
            for p in save.iterdir():
                if not p.is_file():raise RuntimeError('unexpected save subdirectory')
                p.unlink()
            for p in a.control_save.iterdir():
                if p.is_file():shutil.copyfile(p,save/p.name)
        receipt['control_save_hashes']=hashes(save)
        stage('startup')
        launch=subprocess.Popen([sys.executable,'/mnt/UDISK/session.py','start',a.label,
                                 'normal' if a.ordinary_title else ('1' if a.draw_trace else '0')])
        deadline=time.monotonic()+120
        while not pids('wol-horizon') and time.monotonic()<deadline:
            if launch.poll() is not None:raise RuntimeError('launch ended before runtime')
            time.sleep(.1)
        ps=pids('wol-horizon')
        if len(ps)!=1:raise RuntimeError('runtime identity not found')
        owned=(ps[0],stat_identity(Path('/proc')/str(ps[0]))['start_ticks'])
        ledger_args=[sys.executable,'/mnt/UDISK/wol_memory_ledger.py','--pid',str(ps[0]),
            '--out',str(out/'ledger.jsonl'),'--seconds','600','--period','2',
            '--phase-file',str(out/'phase.txt')]
        if a.guest_pages:
            ledger_args+=['--layout',str(a.layout)]
        ledger=subprocess.Popen(ledger_args)
        # Pin artifact identities before readiness: failed startup still needs exact cleanup receipts.
        receipt['runtime_sha256']=hashlib.sha256((root/'wol-horizon').read_bytes()).hexdigest()
        receipt['section_sha256']=hashlib.sha256((root/'wol-romfs.section').read_bytes()).hexdigest()
        launch.wait(timeout=360)
        if launch.returncode:raise RuntimeError('session start failed')
        raw=(Path('/proc')/str(ps[0])/'environ').read_bytes().split(b'\0')
        if a.present_watchdog and b'MOMO_FRAME_CLOCK=1' not in raw:
            raise RuntimeError('watchdog cannot infer progress without enabled frame clock')
        (out/'effective-env.json').write_text(json.dumps({x.split(b'=',1)[0].decode():x.split(b'=',1)[1].decode(errors='replace') for x in raw if b'=' in x and x.split(b'=',1)[0].startswith((b'WOL_',b'COTM_',b'T2_',b'MOMO_'))},indent=2)+'\n')
        sample_vma('startup')
        stage('menu');pause(20)
        sample_vma('menu')
        if a.ordinary_title:return
        stage('continue-load');cmd('press','0x1','0','12','continue-request','180')
        from wol_screen_gate import gameplay_observation
        scene_deadline=time.monotonic()+180;observations=[]
        while True:
            subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(out/'world-ready.png')],check=True,timeout=25)
            observed=gameplay_observation(out/'world-ready.png')
            observations.append(dict(t_ns=time.monotonic_ns(),**observed))
            receipt['gameplay_readiness']=observations
            if observed['has_game_hud']:
                shutil.copyfile(out/'world-ready.png',Path('/mnt/UDISK/wol-goal-20261015')/(a.label+'-world.png'))
                break
            if time.monotonic()>=scene_deadline:raise RuntimeError('CONTINUE did not reach verified gameplay HUD within 180s')
            pause(5)
        receipt['observed_gameplay_hud']=True
        stage('game-idle');pause(30)
        sample_blocks('game-idle')
        sample_vma('game-idle')
        if route is not None:
            receipt['route_sha256']=hashlib.sha256(a.route.read_bytes()).hexdigest()
            for action in route:
                stage(action['label'])
                cmd('press',action['buttons'],str(action.get('stick',0)),str(action['wait_s']),action['label'],str(action['hold_ms']))
        else:
            stage('move-right');cmd('press','0x4000','0','4','right','1500')
            stage('move-left');cmd('press','0x1000','0','4','left','1500')
            stage('map');cmd('press','0x100','0','4','map','180');pause(10)
            stage('map-return');cmd('press','0x100','0','4','return','180');pause(10)
            stage('pause');cmd('press','0x400','0','4','pause','180')
            stage('pause-return');cmd('press','0x400','0','4','unpause','180');pause(10)
    except Exception as error:
        receipt.setdefault('failure',dict(kind=type(error).__name__,message=str(error)))
        raise
    finally:
        warnings=[]
        try:
            sample_blocks('precleanup')
        except Exception as e:
            warnings.append('block sample: '+str(e))
        try:
            sample_vma('precleanup')
        except Exception as e:
            warnings.append('vma sample: '+str(e))
        try:
            if launch and launch.poll() is None:
                launch.wait(timeout=150)
        except (OSError,subprocess.TimeoutExpired) as e:
            warnings.append('launch watcher: '+str(e))
        try:
            if owned:
                stop_owned(*owned)
        except (OSError,RuntimeError) as e:
            warnings.append('stop owned: '+str(e))
        if ledger:
            try:
                ledger.wait(timeout=15)
            except subprocess.TimeoutExpired:
                ledger.terminate();ledger.wait(timeout=10)
                warnings.append('ledger deadline after runtime stop')
            receipt['ledger_exit']=ledger.returncode
        log=root/'logs/latest.log'
        try:
            if log.exists():
                with log.open('rb') as src,gzip.GzipFile(filename=str(out/'runtime.log.gz'),mode='wb') as dst:
                    shutil.copyfileobj(src,dst)
        except (OSError,RuntimeError) as e:
            warnings.append('log archive: '+str(e))
        # Never restore owner data while ANY runtime (including a replacement PID) is live.
        try:
            if pids('wol-horizon'):
                raise RuntimeError('save restore pending: a runtime is live; backup preserved')
            if hashes(backup)!=receipt['owner_save_hashes']:
                raise RuntimeError('owner backup changed; restore refused')
            for p in save.iterdir():
                if not p.is_file():raise RuntimeError('unexpected live save subdirectory')
                p.unlink()
            for p in backup.iterdir():
                if p.is_file():shutil.copyfile(p,save/p.name)
            os.sync()
            receipt['restored_save_hashes']=hashes(save)
            deadline=time.monotonic()+30
            while len(pids('MainUI'))!=1 and not pids('wol-horizon') and time.monotonic()<deadline:
                time.sleep(.5)
            capture_ok=False
            if len(pids('MainUI'))==1 and not pids('wol-horizon'):
                time.sleep(3)
                for _ in range(6):
                    r=subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(out/'restored-menu.png')],timeout=25)
                    if r.returncode==0 and kms_rgb_signal(out/'restored-menu.png'):
                        capture_ok=True;break
                    time.sleep(2)
            receipt['menu_rgb_signal_verified']=capture_ok
            receipt['cleanup_verified']=(receipt['owner_save_hashes']==receipt['restored_save_hashes'] and capture_ok)
        except (OSError,RuntimeError,subprocess.TimeoutExpired) as e:
            warnings.append('save/menu cleanup: '+str(e))
        receipt['cleanup_warnings']=warnings
        receipt['menu_pids']=pids('MainUI')
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('FINAL',json.dumps(receipt),flush=True)
        if not receipt['cleanup_verified'] or warnings:raise RuntimeError('probe incomplete; inspect receipt and preserved backup')


if __name__=='__main__':
    main()
