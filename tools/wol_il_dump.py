#!/usr/bin/env python3
"""Dump IL of named methods with resolved tokens, for pixel-consumer judgement.

Owner-local: reads a game assembly and prints code, so the output is never
published. The point is to classify each consumer as either
  (a) normalized/ratio-only (immune to a rect rescale), or
  (b) mixing an authored pixel-space value with a Sprite rect dimension.
"""
from pathlib import Path
import argparse
import json
import sys

import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBase
from dncil.cil.error import MethodBodyFormatError


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


def member_name(pe, token):
    try:
        if token.table == 0x0A:
            row = pe.net.mdtables.MemberRef.rows[token.rid - 1]
            parent = row.Class.row
            cls = getattr(parent, 'TypeName', None) or getattr(parent, 'Name', '')
            ns = getattr(parent, 'TypeNamespace', '')
            return f'{ns}.{cls}::{row.Name}' if ns else f'{cls}::{row.Name}'
        if token.table == 0x06:
            row = pe.net.mdtables.MethodDef.rows[token.rid - 1]
            return 'def:' + str(row.Name)
        if token.table == 0x04:
            return 'field:' + str(pe.net.mdtables.Field.rows[token.rid - 1].Name)
        if token.table == 0x01:
            return 'type:' + str(pe.net.mdtables.TypeRef.rows[token.rid - 1].TypeName)
        if token.table == 0x02:
            return 'type:' + str(pe.net.mdtables.TypeDef.rows[token.rid - 1].TypeName)
    except Exception:
        return 'token:0x%08x' % token.value
    return 'token:0x%08x' % token.value


def dump(pe, type_name, method_name, limit):
    for t in pe.net.mdtables.TypeDef.rows:
        if str(t.TypeName) != type_name:
            continue
        for m in t.MethodList:
            m = getattr(m, 'row', m)
            if str(m.Name) != method_name:
                continue
            rva = m.Rva
            if not rva:
                print(f'{type_name}::{method_name}: no body')
                return
            body = CilMethodBody(Reader(pe, rva))
            print(f'--- {type_name}::{method_name} code_size={body.code_size} max_stack={body.max_stack}')
            for i, ins in enumerate(body.instructions):
                if i >= limit:
                    print('   ...')
                    break
                operand = ''
                if ins.operand is not None:
                    if hasattr(ins.operand, 'value'):
                        operand = member_name(pe, ins.operand)
                    else:
                        operand = str(ins.operand)
                print(f'{ins.offset:6d} {ins.opcode.name:12s} {operand}')
            return
    print(f'{type_name}::{method_name}: NOT FOUND')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('assembly')
    parser.add_argument('methods', nargs='+', help='Type::Method')
    parser.add_argument('--limit', type=int, default=200)
    args = parser.parse_args()
    pe = dnfile.dnPE(args.assembly)
    for spec in args.methods:
        type_name, method_name = spec.split('::')
        dump(pe, type_name, method_name, args.limit)


if __name__ == '__main__':
    main()
