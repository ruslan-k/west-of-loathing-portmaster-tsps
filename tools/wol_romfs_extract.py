#!/usr/bin/env python3
"""Read one file out of a raw RomFS section: EXTRACT IN 'PATH=OUT'...

The section is the runtime's merged update+DLC image; the RomFS may start at 0
or behind a level header, so the magic is located by scan. Layout per
switchbrew: header 0x50, DirEntry 0x18, FileEntry 0x20.
"""
import struct
import sys
from pathlib import Path


class Romfs:
    def __init__(self, blob):
        self.b = blob
        start = next((c for c in (0, 0x100, 0x200, 0x800, 0x78000)
                      if blob[c:c + 4] == b'ROMF'), None)
        if start is None:
            raise ValueError('no ROMF magic at known offsets')
        (self.magic, self.version, self.header_size, _dh_off, _dh_len, self.dir_meta_off,
         self.dir_meta_len, _fh_off, _fh_len, self.file_meta_off, self.file_meta_len,
         self.data_off, _size) = struct.unpack_from('<4sIIIIIIIIIIQQ', blob, start)
        self.base = start
        self.data = start + self.data_off
        self.n_dirs = self.dir_meta_len // 0x18
        self.n_files = self.file_meta_len // 0x20

    def _name(self, off):
        addr = self.data + off
        return self.b[addr:self.b.index(b'\0', addr)].decode()

    def _dir(self, idx):
        off = self.base + self.dir_meta_off + idx * 0x18
        parent, sibling, child, first_file, _hash, name_off = struct.unpack_from('<IIIIII', self.b, off)
        return dict(parent=parent, sibling=sibling, child=child, file=first_file, name=self._name(name_off))

    def _file(self, idx):
        off = self.base + self.file_meta_off + idx * 0x20
        parent, sibling, nxt = struct.unpack_from('<III', self.b, off)
        data_off = struct.unpack_from('<Q', self.b, off + 0x0C)[0]
        size = struct.unpack_from('<Q', self.b, off + 0x14)[0]
        name_off = struct.unpack_from('<I', self.b, off + 0x1C)[0]
        return dict(parent=parent, sibling=sibling, next=nxt, off=data_off, size=size, name=self._name(name_off))

    def walk(self, idx=0, prefix=''):
        d = self._dir(idx)
        f = d['file']
        while f != 0xFFFFFFFF:
            e = self._file(f)
            yield prefix + '/' + e['name'], e
            f = e['next']
        sub = d['child']
        while sub != 0xFFFFFFFF:
            sd = self._dir(sub)
            yield from self.walk(sub, prefix + '/' + sd['name'])
            sub = sd['sibling']

    def find(self, path):
        want = '/' + path.strip('/').lower()
        for name, e in self.walk():
            if name.lower() == want:
                return e
        raise KeyError(path)

    def read(self, path):
        e = self.find(path)
        start = self.data + e['off']
        return self.b[start:start + e['size']]


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    r = Romfs(Path(sys.argv[1]).read_bytes())
    for spec in sys.argv[2:]:
        path, _, out = spec.partition('=')
        data = r.read(path)
        out = out or Path(path).name
        Path(out).write_bytes(data)
        print(f'{path} -> {out} {len(data)} bytes')


if __name__ == '__main__':
    main()
