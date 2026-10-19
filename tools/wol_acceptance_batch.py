#!/usr/bin/env python3
"""Frozen §16 stationary/moving gulch sequence. No whole-game/default acceptance.

--resume continues an interrupted batch: already-collected trials are adopted
from the manifest/host receipts, a finished-or-running device trial is collected
without relaunch (wol_owned_probe --collect-only), and remaining trials run fresh.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import time

ELF='b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158'
SECTION='49bd16718ed0dc46f16599255791c7603e8aa2b5f04898784a39d6cacb9d0722'
ORDER=('accept-a1','accept-b1','accept-b2','accept-a2','accept-a3','accept-b3')
COMMON={
    'WOL_ALLOC_TRACE':'0','WOL_UPRENDER_TRACE':'0','WOL_RT_ORIGIN':'0',
    'WOL_GPU_RESIDENCY':'0','WOL_ROMFS_COW':'0','WOL_UPLOAD_SKIP':'0',
    'WOL_GUEST_RT720':'0','WOL_COPY_AUDIT':'0','WOL_BC_WRITE_TRACE':'0',
    'WOL_ROMFS_LIFETIME':'0','WOL_SAMPLE_SPLIT':'0','WOL_UPLOAD_TIMING':'0',
    'WOL_PBO_UPLOAD':'0','WOL_ASTC_POSTCOPY':'0','WOL_GPU_TIMELINE':'0',
    'WOL_UNIFORM_CACHE':'0','WOL_COPY_EQUAL':'0','WOL_COPY_GPU':'0',
    'WOL_REFRESH_DIRECT':'0','WOL_PAIR_RING':'0','T2_TRANSFER_SPARSE_COPY':'0',
}


def plan_trial(host_receipt,host_dir,device_dir):
    """Pure resume decision: skip / collect / run / fail-partial."""
    if host_receipt:return 'skip'
    if host_dir:return 'fail-partial'
    return 'collect' if device_dir else 'run'


def main():
    repo=Path(__file__).resolve().parent.parent
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=Path('evidence/accept-720'))
    ap.add_argument('--ssh-target',default='tsps')
    ap.add_argument('--resume',action='store_true')
    a=ap.parse_args();out=repo/a.out
    out.mkdir(parents=True,exist_ok=True)
    manifest=out/'batch.json'
    if a.resume:
        if not manifest.exists():raise RuntimeError('nothing to resume; no manifest')
        result:dict=json.loads(manifest.read_text())
        if result.get('elf_sha256')!=ELF or result.get('section_sha256')!=SECTION:
            raise RuntimeError('manifest identity differs from the frozen protocol')
        if result.get('complete'):raise RuntimeError('batch already complete; nothing to resume')
        result.setdefault('resumes',[]).append(dict(t_ns=time.monotonic_ns(),
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    else:
        if manifest.exists() or any((out/label).exists() for label in ORDER):
            raise RuntimeError('existing trials/manifest: refuse silent reuse (use --resume)')
        result:dict=dict(order=list(ORDER),elf_sha256=ELF,section_sha256=SECTION,
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    route_sha256=hashlib.sha256((repo/'evidence/accept-720/route-gulch.json').read_bytes()).hexdigest(),
                    trials=[],complete=False,whole_game_accepted=False)
    def record():manifest.write_text(json.dumps(result,indent=2)+'\n')
    def remote(command):
        ssh=['ssh','-o','ControlMaster=no','-o','ControlPath=none','-o','BatchMode=yes','-o','ConnectTimeout=15',a.ssh_target]
        return subprocess.run(ssh+[command],text=True,capture_output=True,check=True,timeout=80).stdout
    record();baseline_save=None;baseline_env=None
    trial_by_label={t['label']:t for t in result['trials']}
    for label in ORDER:
        host=out/label
        host_receipt=(host/'receipt.json').exists()
        device_dir=bool(remote('test -d /mnt/UDISK/roadmap-v2-%s && printf yes || true'%label).strip())
        action=plan_trial(host_receipt,host.exists(),device_dir)
        if action=='fail-partial':raise RuntimeError(label+' partial host directory without receipt; inspect manually')
        trial:dict=trial_by_label.get(label) or {}
        if not trial:
            trial=dict(label=label,env=dict(COMMON,WOL_UPRENDER_720='1' if label.startswith('accept-b') else '0'))
            result['trials'].append(trial);trial_by_label[label]=trial
        if action=='skip':
            trial.setdefault('status','collected-not-yet-scene-reviewed');record()
            print('SKIP',label,trial['status'],flush=True)
        else:
            trial.update(begin_ns=trial.get('begin_ns') or time.monotonic_ns(),status='running');record()
            print('TRIAL',label,action,flush=True)
            command=[sys.executable,str(repo/'tools/wol_owned_probe.py'),label,'--elf',ELF,
                     '--layout','/mnt/UDISK/wol-allocfix16-layout.json','--out',str(out),
                     '--env',json.dumps(trial['env']),'--ssh-target',a.ssh_target,
                     '--probe-args','--settled-watchdog 5 --route /mnt/UDISK/accept-720-route-gulch.json']
            if action=='collect':command.append('--collect-only')
            hostlog=out/(label+'-host.log')
            mode='a' if hostlog.exists() else 'x'
            with hostlog.open(mode) as log:
                if mode=='a':log.write('\n--- resumed collect ---\n')
                done=subprocess.run(command,cwd=repo,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
            trial.update(end_ns=time.monotonic_ns(),exit_code=done.returncode)
            if done.returncode:
                trial['status']='failed';record()
                raise RuntimeError(label+' failed; diagnose preserved artifacts before another trial')
        receipt=json.loads((host/'receipt.json').read_text())
        effective=json.loads((host/'effective-env.json').read_text())
        normalized={k:v for k,v in effective.items() if k not in ('WOL_UPRENDER_720','COTM_RUN_ID')}
        if baseline_save is None:baseline_save=receipt['control_save_hashes'];baseline_env=normalized
        if receipt['control_save_hashes']!=baseline_save or receipt['section_sha256']!=SECTION or normalized!=baseline_env:
            trial['status']='identity-mismatch';record()
            raise RuntimeError('save/section/non-treatment environment changed: '+label)
        trial.update(status='collected-not-yet-scene-reviewed',cleanup_verified=receipt['cleanup_verified'],
                     progress_checks=receipt['progress_checks'],identity_check='ok');record()
        print('COLLECTED',label,flush=True)
    result.update(complete=True,collected_trials=len(result['trials']),scene_and_fps_acceptance_pending=True)
    record();print('BATCH_COLLECTED',len(result['trials']),manifest,flush=True)


if __name__=='__main__':main()
