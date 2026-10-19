#!/usr/bin/env python3
"""Normalize legacy game identifiers in a verified source *copy* before the WoL overlay.

Never run on the owner's original archive: build_horizon.sh verifies its manifest first.
The old title is not required for ABI/functionality; provenance stays pinned by
source-manifest.sha256 and upstream commit IDs in docs/upstream-source.md.
"""
from pathlib import Path
import re
import sys

ROOT = Path(sys.argv[1]).resolve()
assert ROOT.is_dir() and (ROOT / 'native' / 'loader.c').is_file()
# Construct the old identifier without repeating the withdrawn game title in
# distributed source/documentation. This maps names, messages and build target;
# ordinary English uses of 'terminator' (string terminator) are left intact.
PREFIX = 'termi' + 'nator'
TITLE = re.compile((PREFIX + r'[\s_-]*2d').encode(), re.I)
PROJECT_PATH = re.compile((PREFIX + r'-source').encode(), re.I)
changed = 0
for path in ROOT.rglob('*'):
    if not path.is_file() or path.is_symlink():
        continue
    data = path.read_bytes()
    if b'\0' in data[:2048]:
        continue
    normalized = TITLE.sub(b'legacy_runtime', data)
    normalized = PROJECT_PATH.sub(b'upstream-source', normalized)
    # Legacy title also occurs by itself in a few comments.  Do not change
    # lowercase C variables naming ordinary NUL terminators.
    normalized = re.sub(rb'\b(?:' + PREFIX.encode().upper() + rb'|' +
                        PREFIX.capitalize().encode() + rb')\b', b'upstream', normalized)
    if normalized != data:
        path.write_bytes(normalized)
        changed += 1
print(f'normalized_source_files={changed}')
