#!/usr/bin/env python3
"""Summarize UpRender runs without generic ASTC analyzer arm misclassification."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from wol_roadmap_analyze import records, summarize


def compare_runs(runs):
    arms=Counter()
    environments=set()
    identities=set()
    for r in runs:
        e=r['effective_env']
        flag=e.get('WOL_UPRENDER_720')
        if flag not in ('0','1'):
            raise ValueError('explicit UpRender treatment flag required')
        arms['uprender720' if flag=='1' else 'control']+=1
        environments.add(json.dumps({k:v for k,v in e.items() if k not in {'WOL_UPRENDER_720','COTM_RUN_ID'}},sort_keys=True))
        identities.add((r['runtime_sha256'],r['section_sha256'],json.dumps(r['control_save_hashes'],sort_keys=True)))
    return dict(treatment='WOL_UPRENDER_720',arm_counts=dict(arms),matched_identity=len(identities)==1,
                matched_other_env=len(environments)==1,full_acceptance=False,
                caveat='Exploratory unless repeated, scene/graph verified, physical gates passed; swap remains separately measured.')


def census(root):
    text=gzip.decompress((root/'runtime.log.gz').read_bytes()).decode(errors='replace')
    up=records(text,'WOL_UPRENDER ')
    origins=records(text,'WOL_RT_ORIGIN ')
    creates=[r for r in origins if r.get('event')=='initialize']
    real=records(text,'NVN_TEXTURE_REAL ')
    classified=[r for r in creates if all(k in r for k in ('width','height','format','samples'))]
    hist=Counter((int(r['width'],0),int(r['height'],0),r['format'],r['samples']) for r in classified)
    gl=Counter((r.get('size','unknown'),r.get('format','unknown'),r.get('depth','unknown')) for r in real)
    return dict(label=root.name,component_events=up,
                constructor_dimensions=[[int(r['width'],0),int(r['height'],0)] for r in up if r.get('event')=='construct'],
                origin_event_count=len(origins),origin_cap_reached=len(origins)>=512,
                unclassified_initialize_events=len(creates)-len(classified),
                request_creation_histogram=[dict(width=k[0],height=k[1],format=k[2],samples=k[3],events=v) for k,v in sorted(hist.items())],
                real_GL_creation_histogram=[dict(size=k[0],format=k[1],depth=k[2],events=v) for k,v in sorted(gl.items())],
                caveat='Creation-event counts, NOT live peak or physical RAM. Origin traces truncate; no complete queue identity/consumer join is claimed.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',type=Path,nargs='+');p.add_argument('--out-dir',type=Path,required=True)
    a=p.parse_args();runs=[summarize(r) for r in a.runs]
    result=dict(runs=runs,comparison=compare_runs(runs))
    a.out_dir.mkdir(parents=True,exist_ok=True)
    (a.out_dir/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (a.out_dir/'target-census.json').write_text(json.dumps([census(r) for r in a.runs],indent=2)+'\n')
    print(json.dumps(result['comparison']))


if __name__=='__main__':main()
