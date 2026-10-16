#!/usr/bin/env python3
"""Patch the owner romfs section in place: replace the StreamingAssets/core bundle
and (optionally) shrink its RomFS FileEntry size, so the guest reads and buffers
only the real bundle bytes instead of the zero padding.

Owner data ops tool. Measured contract for this title (docs/tsps-horizon-adapter.md):

* section size 217,743,360 (the runtime verifies the section by SIZE only);
* the UnityFS bundle lives at section offset 0x4DB0D0 = romfs offset 0x78000
  + data_off 0x200 + FileEntry offset 0x462ED0;
* the FileEntry size field (u64) sits at section offset 0xCFA7E08 and currently
  declares 200,367,356 bytes while the real bundles are smaller (the M1 baseline
  padded to that size; the M2 strip bundle ends earlier). Entries are validated
  on location (offset field 0x462ED0 directly before, name 'core' after) before
  anything is written.

Usage:
  wol_romfs_section_patch.py SECTION_IN CORE_BUNDLE OUT [--entry-size N|auto|keep]

--entry-size auto (default) sets the entry to the real bundle length; keep
leaves the declared size untouched (content padded with zeros to it); N sets an
explicit value. Prints the output sha256 for the deploy manifest.
"""
import argparse
import hashlib
import pathlib
import struct
import sys

SECTION_SIZE = 217743360
CORE_OFF = 0x4DB0D0
ENTRY_OFF_FIELD = 0x462ED0
ENTRY_SIZE_OFF = 0xCFA7E08
DECLARED_SIZE = 200367356


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("section_in", type=pathlib.Path)
    ap.add_argument("core_bundle", type=pathlib.Path)
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--entry-size", default="auto")
    a = ap.parse_args()

    data = bytearray(a.section_in.read_bytes())
    if len(data) != SECTION_SIZE:
        raise SystemExit(f"unexpected section size {len(data)}")
    core = a.core_bundle.read_bytes()

    # Validate the size field location before writing anything. The declared
    # size may already be smaller than the historical maximum (a previous
    # shrink); the location and file name must still match.
    stored_off, stored_size = struct.unpack_from("<QQ", data, ENTRY_SIZE_OFF - 8)
    name = bytes(data[ENTRY_SIZE_OFF + 8 + 8:ENTRY_SIZE_OFF + 8 + 8 + 4])
    if stored_off != ENTRY_OFF_FIELD or name != b"core" or not 0 < stored_size <= DECLARED_SIZE:
        raise SystemExit(f"FileEntry no longer matches the documented contract: "
                         f"off={stored_off:#x} size={stored_size} name={name!r}")
    if len(core) > DECLARED_SIZE:
        raise SystemExit("bundle larger than the declared entry size")

    data[CORE_OFF:CORE_OFF + len(core)] = core
    data[CORE_OFF + len(core):CORE_OFF + DECLARED_SIZE] = b"\0" * (DECLARED_SIZE - len(core))

    if a.entry_size == "keep":
        new_size = stored_size
    elif a.entry_size == "auto":
        new_size = len(core)
    else:
        new_size = int(a.entry_size, 0)
        if not 0 < new_size <= DECLARED_SIZE:
            raise SystemExit("entry size out of range")
    struct.pack_into("<Q", data, ENTRY_SIZE_OFF, new_size)

    a.out.write_bytes(bytes(data))
    digest = hashlib.sha256(data).hexdigest()
    print(f"section {a.out} bytes={len(data)} sha256={digest}")
    print(f"core bytes={len(core)} entry_declared={new_size} padding={DECLARED_SIZE - len(core)}")
    # Read back and re-verify.
    check = bytearray(a.out.read_bytes())
    off, size = struct.unpack_from("<QQ", check, ENTRY_SIZE_OFF - 8)
    assert off == ENTRY_OFF_FIELD and size == new_size
    assert check[CORE_OFF:CORE_OFF + len(core)] == core
    assert not any(check[CORE_OFF + len(core):CORE_OFF + DECLARED_SIZE])
    print("READBACK_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
