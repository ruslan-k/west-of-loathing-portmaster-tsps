#!/usr/bin/env python3
"""Frozen §16 stationary/moving gulch sequence. No whole-game/default acceptance."""
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


def main():
    repo=Path(__file__).resolve().parent.parent
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=Path('evidence/accept-720'))
    ap.add_argument('--ssh-target',default='tsps')
    a=ap.parse_args();out=repo/a.out
    out.mkdir(parents=True,exist_ok=True)
    manifest=out/'batch.json'
    if manifest.exists() or any((out/label).exists() for label in ORDER):
        raise RuntimeError('existing trials/manifest: refuse silent reuse or replacement')
    result:dict=dict(order=list(ORDER),elf_sha256=ELF,section_sha256=SECTION,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                route_sha256=hashlib.sha256((repo/'evidence/accept-720/route-gulch.json').read_bytes()).hexdigest(),
                trials=[],complete=False,whole_game_accepted=False)
    def record():manifest.write_text(json.dumps(result,indent=2)+'\n')
    record();baseline_save=None;baseline_env=None
    for label in ORDER:
        env=dict(COMMON,WOL_UPRENDER_720='1' if label.startswith('accept-b') else '0')
        trial=dict(label=label,env=env,begin_ns=time.monotonic_ns(),status='running')
        result['trials'].append(trial);record();print('TRIAL',label,flush=True)
        command=[sys.executable,str(repo/'tools/wol_owned_probe.py'),label,'--elf',ELF,
                 '--layout','/mnt/UDISK/wol-allocfix16-layout.json','--out',str(out),
                 '--env',json.dumps(env),'--ssh-target',a.ssh_target,
                 '--probe-args','--settled-watchdog 5 --route /mnt/UDISK/accept-720-route-gulch.json']
        with (out/(label+'-host.log')).open('x') as log:
            done=subprocess.run(command,cwd=repo,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
        trial.update(end_ns=time.monotonic_ns(),exit_code=done.returncode)
        if done.returncode:
            trial['status']='failed';record()
            raise RuntimeError(label+' failed; diagnose preserved artifacts before another trial')
        receipt=json.loads((out/label/'receipt.json').read_text())
        effective=json.loads((out/label/'effective-env.json').read_text())
        normalized={k:v for k,v in effective.items() if k not in ('WOL_UPRENDER_720','COTM_RUN_ID')}
        if baseline_save is None:baseline_save=receipt['control_save_hashes'];baseline_env=normalized
        if receipt['control_save_hashes']!=baseline_save or receipt['section_sha256']!=SECTION or normalized!=baseline_env:
            trial['status']='identity-mismatch';record()
            raise RuntimeError('save/section/non-treatment environment changed: '+label)
        trial.update(status='collected-not-yet-scene-reviewed',cleanup_verified=receipt['cleanup_verified'],
                     progress_checks=receipt['progress_checks']);record();print('COLLECTED',label,flush=True)
    result.update(complete=True,collected_trials=len(result['trials']),scene_and_fps_acceptance_pending=True)
    record();print('BATCH_COLLECTED',len(result['trials']),manifest,flush=True)


if __name__=='__main__':main()
