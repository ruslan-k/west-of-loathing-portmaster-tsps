#!/usr/bin/env python3
"""Show the argument setup at every call site of a named member.

Used to read which pixels-per-unit a caller expects from the sprite loader: the
constant decides whether the loader rebuilds a sprite or returns the serialized
one, and therefore whether a rescaled rect reaches the consumer.
"""
from pathlib import Path
import argparse
import re

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

    def seek(self, rva_offset):
        self.offset = rva_offset
        return self.offset


def member_name(pe, token):
    try:
        if token.table == 0x0A:
            row = pe.net.mdtables.MemberRef.rows[token.rid - 1]
            parent = row.Class.row
            cls = getattr(parent, 'TypeName', None) or ''
            return f'{cls}::{row.Name}'
        if token.table == 0x06:
            return 'def:' + str(pe.net.mdtables.MethodDef.rows[token.rid - 1].Name)
    except Exception:
        pass
    return 'token:0x%08x' % token.value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('assembly')
    parser.add_argument('pattern', help='regex matched against the resolved member name')
    parser.add_argument('--context', type=int, default=10)
    args = parser.parse_args()
    rx = re.compile(args.pattern)
    pe = dnfile.dnPE(args.assembly)
    sites = 0
    for t in pe.net.mdtables.TypeDef.rows:
        for m in t.MethodList:
            m = getattr(m, 'row', m)
            if not m.Rva:
                continue
            try:
                body = CilMethodBody(Reader(pe, m.Rva))
            except Exception:
                continue
            ins = body.instructions
            for i, cur in enumerate(ins):
                if cur.opcode.name not in ('call', 'callvirt'):
                    continue
                if cur.operand is None or not hasattr(cur.operand, 'value'):
                    continue
                name = member_name(pe, cur.operand)
                if not rx.search(name):
                    continue
                sites += 1
                print(f'=== {t.TypeName}::{m.Name}  ->  {name}')
                lo = max(0, i - args.context)
                for prev in ins[lo:i]:
                    operand = getattr(prev.operand, 'value', prev.operand)
                    print(f'   {prev.offset:6d} {prev.opcode.name:12s} {operand}')
    print('SITES', sites)


if __name__ == '__main__':
    main()
