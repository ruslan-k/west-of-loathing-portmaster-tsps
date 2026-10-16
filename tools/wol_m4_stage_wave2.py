#!/usr/bin/env python3
"""Stage (never deploy) conservative M4 wave2: world-only allowlist + UI refs.

Read M2 manifest, not M4 manifest, and union extra promotions with the exact
accepted M4 levels file. Baseline accepted IDs remain unchanged. New selections
must be world/background names; DXT alone does not identify art category.
"""
from pathlib import Path
import argparse
import csv
import json

PREFIXES=('bg_', 'bgtile', 'foreground_', 'foregroundparallax_', 'horizon_',
          'ceiling_', 'woodceiling', 'mountainside', 'mountainwall', 'frontrockwall')
EXACT={'adobeceiling','blackceiling'}
BLOCKED=('ui','map','mainmap','font','icon','sprite','controller','poster','sign','logo',
         'hud','menu','face','portrait','char','cursor','button','panel','letter','wanted')


def eligible(name, fmt, w, h, ui=False):
    if ui or fmt not in ('DXT1','DXT5') or min(w,h)<512:
        return False
    n=name.lower()
    if any(token.startswith(b) for token in n.split('_') for b in BLOCKED):
        return False
    return n in EXACT or n.startswith(PREFIXES)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--baseline-levels',type=Path,required=True)
    ap.add_argument('--reference-core',type=Path,required=True,help='M2 bundle for reference classification')
    ap.add_argument('--levels',type=Path,required=True)
    ap.add_argument('--audit',type=Path,required=True)
    a=ap.parse_args()
    import UnityPy
    env=UnityPy.load(str(a.reference_core))
    ui_sprites=set()
    sprites=[]
    for x in env.objects:
        if x.type.name=='MonoBehaviour':
            d=x.read_typetree()
            ref=d.get('m_Sprite')
            if ref and ref['m_FileID']==0:
                ui_sprites.add((id(x.assets_file),ref['m_PathID']))
        elif x.type.name=='Sprite':
            sprites.append((x,x.read_typetree()))
    ui_textures=set()
    for x,d in sprites:
        if (id(x.assets_file),x.path_id) in ui_sprites:
            ref=d['m_RD']['texture']
            if ref['m_FileID']!=0:
                raise ValueError('cannot classify external UI texture reference')
            ui_textures.add(ref['m_PathID'])
    baseline={int(l.split('\t')[0]):int(l.split('\t')[1]) for l in a.baseline_levels.read_text().splitlines() if l and not l.startswith('#')}
    if any(v!=1 for v in baseline.values()):
        raise ValueError('baseline must contain only one extra promotion per texture')
    selected=dict(baseline)
    audit=[]
    with a.manifest.open() as f:
        for r in csv.DictReader(f,delimiter='\t'):
            pid=int(r['path_id'])
            if pid in baseline or not eligible(r['name'],r['format'],int(r['width']),int(r['height']),pid in ui_textures):
                continue
            if r['action']!='strip':
                raise ValueError('candidate was not exact-layout verified by M2')
            selected[pid]=1
            audit.append(dict(path_id=pid,name=r['name'],format=r['format'],
                old_dims=[int(r['width']),int(r['height'])],
                new_dims=[int(r['width'])//2,int(r['height'])//2],
                payload_before=int(r['payload_after']),estimated_saved=int(r['payload_after'])*3//4,
                category='world-background-allowlist',direct_ui_reference=False))
    a.levels.write_text('# STAGED wave2; NOT production; baseline IDs + additional world backgrounds\n'+''.join(f'{k}\t{v}\n' for k,v in sorted(selected.items())))
    result=dict(schema=1,status='STAGED_NOT_DEPLOYED',baseline_count=len(baseline),additional_count=len(audit),
        selected_count=len(selected),estimated_payload_saving_vs_M4=sum(r['estimated_saved'] for r in audit),
        candidates=audit,caveats=['Names and direct serialized UI references are conservative filters, not a proof of visual quality.',
          'No RAM/FPS gain measured. Do not replace accepted M4 until isolated visual/device A/B.'])
    a.audit.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('candidates',)},indent=2))

if __name__=='__main__':
    main()
