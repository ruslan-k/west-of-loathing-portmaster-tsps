#!/usr/bin/env python3
"""Find managed code that names a given sprite at runtime.

A sprite assigned by name (not serialized in a prefab) can still be consumed by
a component that mixes authored pixel units with a rect dimension. This tool
intersects a sprite-name list with every string literal in the assembly, so the
caller sites are found by evidence instead of guessed.
"""
from pathlib import Path
import argparse
import collections
import json

import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBase


class Reader(CilMethodBodyReaderBase):
    def __init__(self, pe, rva):
        self.pe = pe
        self.offset = self.pe.get_offset_from_rva(rva)

    def read(self, n):
        data = self.pe.get_data(self.pe.get_rva_from_offset(self.offset), n)
        self.offset += n
        return data

    def tell(self):
        return self.offset

    def seek(self, offset):
        self.offset = offset
        return self.offset


def user_string(pe, offset):
    try:
        entry = pe.net.user_strings.get(offset)
    except Exception:
        return None
    if entry is None:
        return None
    return str(getattr(entry, 'value', entry))


def walk(pe, names, limit_per_call):
    hits = collections.defaultdict(list)
    for t in pe.net.mdtables.TypeDef.rows:
        type_name = str(t.TypeName)
        for m in t.MethodList:
            m = getattr(m, 'row', m)
            if not m.Rva:
                continue
            try:
                body = CilMethodBody(Reader(pe, m.Rva))
            except Exception:
                continue
            for ins in body.instructions:
                if ins.opcode.name != 'ldstr':
                    continue
                token = ins.operand.value if hasattr(ins.operand, 'value') else int(ins.operand)
                text = user_string(pe, token & 0x00FFFFFF)  # ldstr operand is a #US heap token
                if not text or text not in names:
                    continue
                bucket = hits[text]
                if len(bucket) < limit_per_call:
                    bucket.append({'type': type_name, 'method': str(m.Name)})
    return hits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('assembly')
    parser.add_argument('names_json', type=Path, help='JSON with a rescaled_sprites list')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--limit', type=int, default=12)
    args = parser.parse_args()
    entries = json.loads(args.names_json.read_text())['rescaled_sprites']
    names = {e['name'] for e in entries if e['name']}
    pe = dnfile.dnPE(args.assembly)
    hits = walk(pe, names, args.limit)
    report = {
        'schema': 1,
        'rescaled_names': len(names),
        'named_in_code': len(hits),
        'site_refs': {k: v for k, v in sorted(hits.items())},
        'unreferenced_by_literal': sorted(names - set(hits)),
        'caveat': ('A literal match proves the name is used in code, not that the consumer mixes '
                   'pixel units. Names reached through tables/indirection show up as unreferenced.'),
    }
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'site_refs'}, indent=2))
    for name, sites in sorted(hits.items()):
        print(name, '->', '; '.join(f"{s['type']}::{s['method']}" for s in sites))


if __name__ == '__main__':
    main()
