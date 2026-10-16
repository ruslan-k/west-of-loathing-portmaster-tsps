#!/usr/bin/env python3
"""Host-side alternating ASTC post-copy A/B. Each owned device run verifies cleanup.
Only receipts, metrics, compressed logs and KMS screenshots are fetched; never owner saves.
"""
import argparse
import json
import shlex
import subprocess
from pathlib import Path

SSH=['ssh','-o','ControlMaster=no','-o','ControlPath=none','-o','BatchMode=yes','-o','ConnectTimeout=15','tsps']


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prefix',required=True)
    ap.add_argument('--elf-sha256',required=True)
    ap.add_argument('--layout',required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--pairs',type=int,default=3)
    ap.add_argument('--texture-id',default='469',help='explicit runtime identity; use all only after single-texture acceptance')
    ap.add_argument('--feature',choices=('astc','pbo'),default='astc')
    ap.add_argument('--control-save',default='/mnt/UDISK/wol-goal-20261015/user-after-goblin-attack')
    a=ap.parse_args()
    if not 1<=a.pairs<=3:ap.error('1..3 pairs per round')
    a.out.mkdir(parents=True,exist_ok=False)
    runs=[]
    variants=('control','postcopy') if a.feature=='astc' else ('control','direct','pbo')
    for i in range(1,a.pairs+1):
        for variant in variants:
            label=f'{a.prefix}-{variant}-{i}'
            out=a.out/label;out.mkdir()
            got=subprocess.run(SSH+['sha256sum /mnt/SDCARD/Roms/PORTS/wol-switch/wol-horizon'],capture_output=True,text=True,check=True).stdout.split()[0]
            if got!=a.elf_sha256:raise RuntimeError('device runtime changed; stop batch')
            flags=['WOL_COPY_AUDIT=0','WOL_ALLOC_TRACE=0','WOL_BC_WRITE_TRACE=0','WOL_ROMFS_LIFETIME=0',
                   'WOL_UPLOAD_TIMING=0','WOL_PBO_UPLOAD='+('1' if variant=='pbo' else '0'),
                   'WOL_REFRESH_DIRECT='+('1' if variant=='direct' else '0'),
                   'WOL_ASTC_POSTCOPY='+('1' if variant=='postcopy' else '0'),
                   'WOL_ASTC_POSTCOPY_ID='+a.texture_id,
                   'WOL_ASTC_CACHE='+('/mnt/UDISK/wol-astc-cache-wide.bin' if variant=='postcopy' else '')]
            argv=['env',*flags,'python3','/mnt/UDISK/wol_roadmap_probe.py','--label',label,'--layout',a.layout,'--control-save',a.control_save]
            command='cd /mnt/UDISK && '+shlex.join(argv)
            print('START',label,flush=True)
            with (out/'host-run.log').open('w') as f:
                result=subprocess.run(SSH+[command],stdout=f,stderr=subprocess.STDOUT)
            for name in ['receipt.json','effective-env.json','ledger.jsonl','runtime.log.gz','restored-menu.png']:
                subprocess.run(['scp','-O','-q',f'root@192.168.50.135:/mnt/UDISK/roadmap-v2-{label}/{name}',str(out/name)],check=True)
            for name in ['title','world','right','left','map','return','pause','unpause']:
                subprocess.run(['scp','-O','-q',f'root@192.168.50.135:/mnt/UDISK/wol-goal-20261015/{label}-{name}.png',str(out/(name+'.png'))],check=True)
            receipt=json.loads((out/'receipt.json').read_text())
            if result.returncode or not receipt['cleanup_verified'] or receipt['runtime_sha256']!=a.elf_sha256:
                raise RuntimeError(f'{label} failed; dependent arms refused')
            runs.append(dict(label=label,variant=variant,pair=i,path=str(out),runtime_sha256=receipt['runtime_sha256']))
            (a.out/'runs.json').write_text(json.dumps(runs,indent=2)+'\n')
            print('DONE',label,flush=True)
    assert len(runs)==len(variants)*a.pairs
    print('BATCH_VERIFIED',len(runs),flush=True)


if __name__=='__main__':
    main()
