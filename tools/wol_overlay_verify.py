#!/usr/bin/env python3
"""Apply the data-free overlay to owner-restored GPL sources and verify a frozen build tree.
No game image or payload is read/copied. Output contains only hashes and source names.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def verify(base, reference, overlay):
    with tempfile.TemporaryDirectory(prefix='wol-overlay-') as td:
        root = Path(td)
        shutil.copytree(base/'native', root/'native')
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        subprocess.run(['git', '-C', str(root), 'apply', '--check', str(overlay.resolve())], check=True)
        subprocess.run(['git', '-C', str(root), 'apply', str(overlay.resolve())], check=True)
        hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted((root/'native').rglob('*')) if p.is_file()}
        expected = {str(p.relative_to(reference)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((reference/'native').rglob('*')) if p.is_file()}
        different = sorted(k for k in hashes.keys() | expected.keys() if hashes.get(k) != expected.get(k))
        if different:
            raise ValueError('overlay/source mismatch: '+str(different))
        return dict(overlay_sha256=hashlib.sha256(overlay.read_bytes()).hexdigest(),
                    native_files=hashes, mismatches=[])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--overlay', type=Path, default=Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = verify(a.base, a.reference, a.overlay)
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    print('SOURCE_PARITY', len(result['native_files']))


if __name__ == '__main__':
    main()
