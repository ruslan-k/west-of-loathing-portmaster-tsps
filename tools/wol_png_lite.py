"""Minimal stdlib PNG reader for 8-bit RGB/RGBA non-interlaced frames + analysis helpers."""
import struct, zlib
from pathlib import Path

def read_png(path):
    data = path.read_bytes()
    assert data.startswith(b'\x89PNG\r\n\x1a\n'), 'not a PNG: %s' % path
    pos = 8; parts = []; shape = None
    while pos + 12 <= len(data):
        n = struct.unpack_from('>I', data, pos)[0]
        kind = data[pos+4:pos+8]; body = data[pos+8:pos+8+n]; pos += 12 + n
        if kind == b'IHDR': shape = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT': parts.append(body)
        elif kind == b'IEND': break
    assert shape is not None, 'missing IHDR: %s' % path
    w, h, depth, color, comp, filt, inter = shape
    assert depth == 8 and inter == 0 and color in (2, 6), shape
    nch = 3 if color == 2 else 4
    raw = zlib.decompress(b''.join(parts))
    stride = w * nch
    out = bytearray(w*h*3); prev = bytearray(stride)
    p = 0
    for y in range(h):
        ftype = raw[p]; p += 1
        line = bytearray(raw[p:p+stride]); p += stride
        if ftype == 1:
            for i in range(nch, stride): line[i] = (line[i] + line[i-nch]) & 0xFF
        elif ftype == 2:
            for i in range(stride): line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                a = line[i-nch] if i >= nch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = line[i-nch] if i >= nch else 0
                b = prev[i]; c = prev[i-nch] if i >= nch else 0
                pa = abs(b - c); pb = abs(a - c); pc = abs(a + b - 2*c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        elif ftype != 0:
            raise RuntimeError('filter type %d' % ftype)
        o = y * w * 3
        if nch == 3:
            out[o:o+w*3] = line
        else:
            for x in range(w):
                out[o+x*3:o+x*3+3] = line[x*4:x*4+3]
        prev = line
    return w, h, bytes(out)

def luma_plane(w, h, rgb):
    return bytes((77*rgb[i*3] + 150*rgb[i*3+1] + 29*rgb[i*3+2]) >> 8 for i in range(w*h))

def components(w, h, mask, min_size=6):
    """8-connected components of a boolean mask (list/bytes). Returns bboxes."""
    seen = bytearray(w*h); boxes = []
    for start in range(w*h):
        if not mask[start] or seen[start]: continue
        stack = [start]; seen[start] = 1
        x0 = x1 = start % w; y0 = y1 = start // w; n = 0
        while stack:
            i = stack.pop(); n += 1
            x = i % w; y = i // w
            if x < x0: x0 = x
            if x > x1: x1 = x
            if y < y0: y0 = y
            if y > y1: y1 = y
            for dy in (-1, 0, 1):
                ny = y + dy
                if ny < 0 or ny >= h: continue
                for dx in (-1, 0, 1):
                    nx = x + dx
                    if nx < 0 or nx >= w: continue
                    j = ny*w + nx
                    if mask[j] and not seen[j]:
                        seen[j] = 1; stack.append(j)
        if n >= min_size: boxes.append(dict(n=n, x0=x0, y0=y0, x1=x1, y1=y1))
    return boxes


def write_png(path, w, h, rgb):
    """Write an 8-bit RGB non-interlaced PNG (test/fixture helper)."""
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xFFFFFFFF)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgb[y*w*3:(y+1)*w*3]
    out = [b'\x89PNG\r\n\x1a\n',
           chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)),
           chunk(b'IDAT', zlib.compress(bytes(raw), 9)),
           chunk(b'IEND', b'')]
    path = Path(path)
    path.write_bytes(b''.join(out))
    return path
