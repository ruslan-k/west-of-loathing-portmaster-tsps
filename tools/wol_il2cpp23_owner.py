#!/usr/bin/env python3
"""Read-only metadata-v23 -> native PC/field-offset join; emits metadata, never code.

Schema reference: Perfare/Il2CppDumper, MetadataClass.cs / Il2CppClass.cs.
Only v23 and 64-bit, module-relative unrelocated main segments are supported.
Ambiguous registrations, invalid indexes/ranges and unmapped pointers refuse.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


class OwnerMap:
    def __init__(self, metadata, text, rodata, data, ro_va, data_va):
        self.metadata = metadata
        self.text = text
        self.data = data
        self.data_va = data_va
        self.segments = [(0, text), (ro_va, rodata), (data_va, data)]
        if len(metadata) < 264:
            raise ValueError('short metadata header')
        h = struct.unpack_from('<66I', metadata)
        if h[:2] != (0xFAB11BAF, 23):
            raise ValueError('only canonical metadata v23 supported')
        def table(pair, size):
            off, n = h[pair:pair+2]
            if off < 264 or off > len(metadata) or n > len(metadata)-off or n % size:
                raise ValueError('invalid metadata table')
            return metadata[off:off+n]
        self.strings = table(6, 1)
        self.methods = list(struct.iter_unpack('<12i4H', table(12, 56)))
        self.types = list(struct.iter_unpack('<20i8H2I', table(40, 104)))
        self.fields = list(struct.iter_unpack('<4i', table(24, 16)))
        indices = [m[6] for m in self.methods if m[6] >= 0]
        if not indices or sorted(indices) != list(range(len(indices))):
            raise ValueError('method indexes are not a unique contiguous v23 table')
        n = len(indices)
        candidates = []
        for at in range(0, len(data)-16+1, 8):
            count, pointer = struct.unpack_from('<QQ', data, at)
            if count != n:
                continue
            try:
                pointers = self.words(pointer, count)
            except ValueError:
                continue
            if all(not p or (p % 4 == 0 and p+4 <= len(text)) for p in pointers):
                candidates.append((data_va+at, pointers))
        if len(candidates) != 1:
            raise ValueError('code registration missing or ambiguous')
        self.code_registration, self.pointers = candidates[0]
        candidates = []
        for at in range(0, len(data)-32+1, 8):
            n1, p1, n2, p2 = struct.unpack_from('<4Q', data, at)
            if n1 != len(self.types) or n2 != n1:
                continue
            try:
                a = self.words(p1, n1)
                self.words(p2, n2)
                for typ, ptr in zip(self.types, a):
                    if typ[22]:
                        self.read(ptr, typ[22]*4)
            except ValueError:
                continue
            candidates.append((data_va+at, a))
        if len(candidates) != 1:
            raise ValueError('field-offset registration missing or ambiguous')
        self.field_registration, self.offset_arrays = candidates[0]

    def read(self, address, length):
        if address < 0 or length < 0:
            raise ValueError('negative range')
        for base, data in self.segments:
            if base <= address <= base+len(data) and length <= base+len(data)-address:
                return data[address-base:address-base+length]
        raise ValueError('unmapped segment range')

    def words(self, address, count):
        if count > 1000000:
            raise ValueError('unbounded array')
        return struct.unpack('<'+'Q'*count, self.read(address, count*8))

    def name(self, index):
        if index < 0 or index >= len(self.strings):
            raise ValueError('invalid string index')
        end = self.strings.find(b'\0', index)
        if end < 0:
            raise ValueError('unterminated metadata name')
        return self.strings[index:end].decode('utf-8', errors='strict')

    def type_report(self, name):
        matches = [(i, t) for i, t in enumerate(self.types) if self.name(t[0]) == name]
        if len(matches) != 1:
            raise ValueError('type missing or ambiguous')
        i, t = matches[0]
        fs, ms, nf, nm = t[12], t[13], t[22], t[20]
        if (nf and (fs < 0 or fs+nf > len(self.fields))) or (nm and (ms < 0 or ms+nm > len(self.methods))):
            raise ValueError('invalid type member span')
        offsets = struct.unpack('<'+'i'*nf, self.read(self.offset_arrays[i], nf*4)) if nf else ()
        methods = []
        for row in self.methods[ms:ms+nm]:
            if row[1] != i:
                raise ValueError('method declaring-type mismatch')
            methods.append(dict(name=self.name(row[0]), method_index=row[6],
                                native_offset=self.pointers[row[6]] if row[6] >= 0 else None))
        return dict(type=name, type_index=i, code_registration=self.code_registration,
                    field_registration=self.field_registration,
                    methods=methods, fields=[dict(name=self.name(f[0]), offset=o)
                    for f, o in zip(self.fields[fs:fs+nf], offsets)])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--metadata', type=Path, required=True)
    ap.add_argument('--image', type=Path, required=True)
    ap.add_argument('--ro-va', type=lambda x:int(x,0), required=True)
    ap.add_argument('--data-va', type=lambda x:int(x,0), required=True)
    ap.add_argument('--type', default='UpRender')
    a = ap.parse_args()
    paths = [a.metadata] + [a.image/('main.'+k+'.seg') for k in ('text','rodata','data')]
    contents = [p.read_bytes() for p in paths]
    m = OwnerMap(contents[0], contents[1], contents[2], contents[3], a.ro_va, a.data_va)
    report: dict = m.type_report(a.type)
    report['input_sha256'] = {p.name:hashlib.sha256(b).hexdigest() for p,b in zip(paths,contents)}
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
