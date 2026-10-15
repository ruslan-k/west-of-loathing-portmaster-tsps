#!/usr/bin/env python3
"""M1/M5: bounded benchmark + read-only page/descriptor snapshots.

run: use existing principal-flow session harness, protect the CURRENT owner save,
monitor startup before launcher entry, measure menu then CONTINUE, always clean up.
collect: attach to an owned runtime for one explicitly named phase.
Neither mode changes clocks, VM settings or allocator state. --cold explicitly
requests drop_caches (run only). Owner payloads/saves must never be published.
"""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time

from wol_memory_profile import Observer, lifecycle, require_elf, sha256, stat_identity


def pids(comm):
    out = []
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():
            continue
        try:
            if (p/'comm').read_text().strip() == comm:
                out.append(int(p.name))
        except OSError:
            pass
    return out


def frame_rate(text):
    frames = [tuple(map(int, m)) for m in re.findall(r'MOMO_FRAME frame=(\d+) ns=(\d+)', text)]
    if len(frames) < 2 or frames[-1][1] <= frames[0][1]:
        return None
    return (frames[-1][0] - frames[0][0]) * 1e9 / (frames[-1][1] - frames[0][1])


def summarize(samples, hz=None, page=None):
    hz = hz or os.sysconf('SC_CLK_TCK')
    page = page or os.sysconf('SC_PAGE_SIZE')
    a, b = samples[0], samples[-1]
    dt = b['t'] - a['t']
    def maximum(group, field):
        return max(r[group].get(field, 0) for r in samples)
    return dict(seconds=dt, samples=len(samples),
        mean_status_RSS_KiB=statistics.mean(r['status'].get('VmRSS', 0) for r in samples),
        mean_status_swap_KiB=statistics.mean(r['status'].get('VmSwap', 0) for r in samples),
        peak_status_VmHWM_KiB=maximum('status', 'VmHWM'),
        sampled_peak_PSS_plus_SwapPSS_KiB=max(r['rollup'].get('Pss',0)+r['rollup'].get('SwapPss',0) for r in samples),
        end_PSS_plus_SwapPSS_KiB=b['rollup'].get('Pss',0)+b['rollup'].get('SwapPss',0),
        min_MemAvailable_KiB=min(r['meminfo'].get('MemAvailable', 0) for r in samples),
        min_CmaFree_KiB=min(r['meminfo'].get('CmaFree', 0) for r in samples),
        cpu_percent=(b['process']['cpu_ticks']-a['process']['cpu_ticks'])/hz/dt*100 if dt else None,
        major_faults_per_s=(b['process']['majflt']-a['process']['majflt'])/dt if dt else None,
        system_swapin_KiB_per_s=(b['vmstat'].get('pswpin',0)-a['vmstat'].get('pswpin',0))*page/1024/dt if dt else None,
        system_swapout_KiB_per_s=(b['vmstat'].get('pswpout',0)-a['vmstat'].get('pswpout',0))*page/1024/dt if dt else None)


def collect(pid, seconds, phase, out, layout, log):
    observer = Observer(pid, layout)
    start = observer.snapshot(phase+'-start')
    log_start = log.stat().st_size
    samples = [observer.sample()]
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        time.sleep(min(2, max(0, end-time.monotonic())))
        samples.append(observer.sample())
    finish = observer.snapshot(phase+'-end')
    with log.open('rb') as f:
        f.seek(log_start)
        chunk = f.read()
    summary = summarize(samples)
    summary['presents_per_s'] = frame_rate(chunk.decode(errors='replace'))
    result = dict(schema=1, phase=phase, scene_verified=False, summary=summary,
                  start=start, end=finish, samples=samples,
                  lifecycle=lifecycle(start['descriptors'], finish['descriptors']))
    out.mkdir(parents=True, exist_ok=True)
    (out/(phase+'.json')).write_text(json.dumps(result, indent=2)+'\n')
    (out/(phase+'.interval.log')).write_bytes(chunk)
    print(phase, json.dumps(summary), flush=True)
    return result


def manifest(path):
    return {str(p.relative_to(path)):sha256(p) for p in sorted(path.rglob('*')) if p.is_file()}


def stop_owned(pid, start_ticks):
    proc = Path('/proc') / str(pid)
    def same():
        try:
            return stat_identity(proc)['start_ticks'] == start_ticks and (proc/'comm').read_text().strip() == 'wol-horizon'
        except OSError:
            return False
    if same():
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic()+10
        while same() and time.monotonic()<deadline:
            time.sleep(.25)
        if same():
            os.kill(pid, signal.SIGKILL)
        deadline = time.monotonic()+10
        while same() and time.monotonic()<deadline:
            time.sleep(.25)
    if same():
        raise RuntimeError('owned runtime did not stop')


def watch(args):
    end = time.monotonic()+args.seconds
    observer = None
    samples = []
    while time.monotonic()<end and not args.stop.exists():
        ps = pids('wol-horizon')
        if observer is None and len(ps)==1:
            observer = Observer(ps[0])
        if observer:
            try:
                samples.append(observer.sample())
            except OSError:
                break
        time.sleep(1)
    result = dict(schema=1, phase='startup', samples=samples,
                  summary=summarize(samples) if samples else None,
                  caveat='1 s sampled peak; VmHWM is process lifetime. Sampling starts when comm becomes wol-horizon.')
    args.out.write_text(json.dumps(result, indent=2)+'\n')


def png_nonblack(path):
    """Minimal bounded PNG RGB/RGBA8 decoder for capture readiness, not scene ID."""
    import struct
    import zlib
    raw=Path(path).read_bytes()
    if raw[:8]!=b'\x89PNG\r\n\x1a\n':
        return False
    offset=8
    payload=bytearray()
    w=h=channels=0
    while offset+12<=len(raw):
        n=int.from_bytes(raw[offset:offset+4],'big')
        tag=raw[offset+4:offset+8]
        part=raw[offset+8:offset+8+n]
        if tag==b'IHDR':
            w,h,depth,color,comp,filt,interlace=struct.unpack('>IIBBBBB',part)
            if depth!=8 or color not in (2,6) or interlace or not 0<w*h<=4096*4096:
                return False
            channels=3 if color==2 else 4
        elif tag==b'IDAT':
            payload.extend(part)
        offset+=12+n
    if not channels:
        return False
    data=zlib.decompress(payload)
    stride=w*channels
    if len(data)!=(stride+1)*h:
        return False
    previous=bytearray(stride)
    lit=sampled=0
    for y in range(h):
        pos=y*(stride+1)
        mode=data[pos]
        row=bytearray(data[pos+1:pos+1+stride])
        if mode not in (0,1,2,3,4):
            return False
        if mode:
            for x in range(stride):
                a=row[x-channels] if x>=channels else 0
                b=previous[x]
                c=previous[x-channels] if x>=channels else 0
                if mode==1:
                    predictor=a
                elif mode==2:
                    predictor=b
                elif mode==3:
                    predictor=(a+b)//2
                else:
                    p=a+b-c
                    pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
                    predictor=a if pa<=pb and pa<=pc else b if pb<=pc else c
                row[x]=(row[x]+predictor)&255
        if y%8==0:
            for x in range(0,stride,channels*8):
                sampled+=1
                lit+=max(row[x:x+3])>16
        previous=row
    return sampled>0 and lit/sampled>.05


def capture_menu(path, attempts=6, runner=subprocess.run, sleeper=time.sleep, validator=png_nonblack):
    """MainUI existence and kmsgrab success can both precede a visible frame."""
    for attempt in range(attempts):
        result=runner(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(path)],timeout=25)
        if result.returncode==0 and validator(path):
            return
        if attempt+1<attempts:
            sleeper(2)
    raise RuntimeError('Spruce visible framebuffer unavailable after bounded retries')


def run(args):
    if pids('wol-horizon') or len(pids('MainUI'))!=1:
        raise RuntimeError('device not idle; refusing to stop somebody else\'s session')
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    save = args.root/'save-laboratory'
    owner = out/'owner-save'
    original = manifest(save)
    shutil.copytree(save, owner)
    if manifest(owner)!=original:
        raise RuntimeError('owner save backup verification failed')
    log = args.root/'logs/latest.log'
    layout = json.loads(args.layout.read_text())
    require_elf(layout, sha256(args.root/'wol-horizon'))
    receipt: dict = dict(schema=1, label=args.label, owner_save_sha256=original,
        harness_sha256=sha256(args.session_tool), cold_cache_requested=args.cold,
        runtime_sha256=sha256(args.root/'wol-horizon'), section_sha256=sha256(args.root/'wol-romfs.section'))
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    pid = start_ticks = None
    watcher = None
    try:
        if not args.control_save.is_dir():
            raise RuntimeError('controlled save not found')
        shutil.rmtree(save)
        shutil.copytree(args.control_save, save)
        if manifest(save)!=manifest(args.control_save):
            raise RuntimeError('controlled save verification failed')
        os.sync()
        if args.cold:
            Path('/proc/sys/vm/drop_caches').write_text('3')
        watcher = subprocess.Popen([sys.executable, __file__, 'watch', '--seconds','180',
            '--stop',str(out/'watch.stop'),'--out',str(out/'startup.json')])
        subprocess.run([sys.executable,str(args.session_tool),'start',args.label,'0'], check=True, timeout=130)
        state = json.loads((args.session_tool.parent/'wol-goal-20261015/session.json').read_text())
        pid, start_ticks = state['pid'], int(state['identity'][1])
        proc = Path('/proc')/str(pid)
        if stat_identity(proc)['start_ticks']!=start_ticks:
            raise RuntimeError('harness PID changed')
        (out/'effective-env.json').write_text(json.dumps({k:v for k,v in (s.split('=',1) for s in (proc/'environ').read_bytes().decode().split('\0') if '=' in s) if k.startswith(('WOL_','T2_','COTM_'))},indent=2)+'\n')
        (out/'watch.stop').touch()
        watcher.wait(timeout=15)
        collect(pid,args.seconds,'menu',out,layout,log)
        subprocess.run([sys.executable,str(args.session_tool),'press','1','0','20','resume'],check=True,timeout=60)
        collect(pid,args.seconds,'game',out,layout,log)
        if args.gate:
            (out/'interaction.ready').touch()
            deadline=time.monotonic()+240
            while not (out/'interaction.done').exists():
                if time.monotonic()>deadline:
                    raise RuntimeError('interaction gate timed out')
                if stat_identity(proc)['start_ticks']!=start_ticks:
                    raise RuntimeError('runtime identity changed')
                time.sleep(1)
        shutil.copy2(log,out/'runtime.log')
    finally:
        # Evidence I/O and observer shutdown are secondary to stopping our
        # runtime and restoring the owner save. An archive ENOSPC must never
        # short-circuit the safety part of this finally block.
        cleanup_warnings=[]
        try:
            if log.exists():
                shutil.copy2(log,out/'runtime.log')
        except OSError as e:
            cleanup_warnings.append('runtime archive: '+str(e))
        try:
            (out/'watch.stop').touch()
        except OSError as e:
            cleanup_warnings.append('observer stop marker: '+str(e))
        if watcher:
            try:
                try:
                    watcher.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    watcher.terminate()
                    try:
                        watcher.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        watcher.kill()
                        watcher.wait(timeout=5)
            except Exception as e:
                cleanup_warnings.append('observer shutdown: '+str(e))
        # A failed harness may have spawned the runtime before writing its state.
        try:
            if pid is None and (out/'startup.json').exists():
                startup=json.loads((out/'startup.json').read_text())
                candidates=pids('wol-horizon')
                if startup['samples'] and len(candidates)==1:
                    candidate=candidates[0]
                    ticks=startup['samples'][0]['process']['start_ticks']
                    if stat_identity(Path('/proc')/str(candidate))['start_ticks']==ticks:
                        pid,start_ticks=candidate,ticks
        except (OSError, ValueError, KeyError, TypeError) as e:
            cleanup_warnings.append('runtime ownership recovery: '+str(e))
        if pid is not None:
            try:
                stop_owned(pid,start_ticks)
            except Exception as e:
                cleanup_warnings.append('owned runtime stop: '+str(e))
        remaining=pids('wol-horizon')
        if remaining:
            # Never overwrite files that a live or unowned game can still
            # write back. The verified owner copy is retained, not discarded.
            receipt.update(cleanup_verified=False,owner_save_restore_pending=True,
                owner_backup=str(owner),game_remaining=remaining,
                cleanup_warnings=cleanup_warnings,
                recovery_reason='Stop the remaining game safely, then restore owner_backup and verify its manifest.')
            try:
                (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
            except OSError as e:
                print('RECOVERY_RECEIPT_WRITE_FAILED',str(e),file=sys.stderr)
            print('OWNER_SAVE_RESTORE_PENDING',str(owner),file=sys.stderr)
            raise RuntimeError('runtime remains; refusing live-save overwrite; verified owner backup retained at '+str(owner))
        if save.exists():
            shutil.rmtree(save)
        shutil.copytree(owner,save)
        os.sync()
        if manifest(save)!=original:
            raise RuntimeError('owner save restore failed')
        deadline=time.monotonic()+40
        while len(pids('MainUI'))!=1 and time.monotonic()<deadline:
            time.sleep(.5)
        if len(pids('MainUI'))!=1:
            raise RuntimeError('Spruce menu did not return')
        capture_menu(out/'restored-menu.png')
        receipt.update(cleanup_verified=True,cleanup_warnings=cleanup_warnings,game_remaining=pids('wol-horizon'),menu_pids=pids('MainUI'),restored_save_sha256=manifest(save))
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('CLEANUP_VERIFIED', json.dumps(receipt),flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='mode',required=True)
    c=sub.add_parser('collect')
    c.add_argument('--pid',type=int,required=True)
    c.add_argument('--seconds',type=int,default=30)
    c.add_argument('--phase',required=True)
    c.add_argument('--out',type=Path,required=True)
    c.add_argument('--layout',type=Path,required=True)
    c.add_argument('--log',type=Path,default=Path('/mnt/SDCARD/Roms/PORTS/wol-switch/logs/latest.log'))
    w=sub.add_parser('watch')
    w.add_argument('--seconds',type=int,default=180)
    w.add_argument('--stop',type=Path,required=True)
    w.add_argument('--out',type=Path,required=True)
    r=sub.add_parser('run')
    r.add_argument('--root',type=Path,default=Path('/mnt/SDCARD/Roms/PORTS/wol-switch'))
    r.add_argument('--session-tool',type=Path,default=Path('/mnt/UDISK/session.py'))
    r.add_argument('--control-save',type=Path,required=True)
    r.add_argument('--label',required=True)
    r.add_argument('--out',type=Path,required=True)
    r.add_argument('--layout',type=Path,required=True)
    r.add_argument('--seconds',type=int,default=30)
    r.add_argument('--cold',action='store_true')
    r.add_argument('--gate',action='store_true',help='wait up to 240 s for additional scene probes')
    args=ap.parse_args()
    if hasattr(args,'phase') and not re.fullmatch(r'[a-zA-Z0-9_-]+',args.phase):
        ap.error('phase must be a safe filename token')
    if not 1<=args.seconds<=600:
        ap.error('seconds must be 1..600')
    if args.mode=='collect':
        collect(args.pid,args.seconds,args.phase,args.out,json.loads(args.layout.read_text()),args.log)
    elif args.mode=='watch':
        watch(args)
    else:
        run(args)

if __name__=='__main__':
    main()
