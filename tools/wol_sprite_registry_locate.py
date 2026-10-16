#!/usr/bin/env python3
"""Locate the data table that maps a sprite name to runtime-load metadata.

The game assigns some Sprite references by name at runtime, so the names are not
present as code literals. This tool finds which object in the bundle carries them
(a TextAsset or a MonoBehaviour payload), which identifies the authoritative
runtime-name registry instead of guessing from prefab references.
"""
from pathlib import Path
import argparse
import json
import re

import UnityPy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bundle', type=Path)
    parser.add_argument('names_json', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--limit', type=int, default=8)
    args = parser.parse_args()
    wanted = [e['name'] for e in json.loads(args.names_json.read_text())['rescaled_sprites']]
    env = UnityPy.load(str(args.bundle))
    hits = []
    for obj in env.objects:
        if obj.type.name in ('Sprite', 'Texture2D'):
            continue
        try:
            raw = obj.get_raw_data()
        except Exception:
            continue
        text = raw.decode('utf-8', 'ignore') if isinstance(raw, (bytes, bytearray)) else str(raw)
        found = [n for n in wanted if len(n) > 5 and n in text]
        if not found:
            continue
        hits.append({'type': obj.type.name, 'path_id': obj.path_id,
                     'container': getattr(obj, 'container', None), 'names': found[:args.limit],
                     'name_count': len(found), 'bytes': len(raw)})
    report = {'schema': 1, 'objects_with_name_lists': len(hits), 'hits': hits,
              'covered_names': sorted({n for h in hits for n in h['names']}),
              'caveat': 'A container hit proves the object carries the names; the semantic registry owner is read from its typetree.'}
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'hits'}, indent=2))
    for h in hits:
        print(h['type'], h['path_id'], h['name_count'], h['bytes'], h['names'][:4])


if __name__ == '__main__':
    main()
