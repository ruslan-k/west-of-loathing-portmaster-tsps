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
        launch.wait(timeout=150)
        if launch.returncode:raise RuntimeError('session start failed')
        receipt['runtime_sha256']=hashlib.sha256((root/'wol-horizon').read_bytes()).hexdigest()
        receipt['section_sha256']=hashlib.sha256((root/'wol-romfs.section').read_bytes()).hexdigest()
        raw=(Path('/proc')/str(ps[0])/'environ').read_bytes().split(b'\0')
        if a.present_watchdog and b'MOMO_FRAME_CLOCK=1' not in raw:
            raise RuntimeError('watchdog cannot infer progress without enabled frame clock')
        (out/'effective-env.json').write_text(json.dumps({x.split(b'=',1)[0].decode():x.split(b'=',1)[1].decode(errors='replace') for x in raw if b'=' in x and x.split(b'=',1)[0].startswith((b'WOL_',b'COTM_',b'T2_',b'MOMO_'))},indent=2)+'\n')
        stage('menu');pause(20)
        if a.ordinary_title:return
        stage('continue-load');cmd('press','0x1','0','12','world','180')
        stage('game-idle');pause(30)
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
    finally:
        warnings=[]
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
