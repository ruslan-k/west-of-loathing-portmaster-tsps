#!/usr/bin/env python3
"""Generate an m5 layout JSON for a built wol-horizon ELF by re-deriving the
symbol offsets with nm and keeping the fixed struct layouts from a reference
layout. Usage: gen_layout.py <build-dir-name> """
import hashlib, json, subprocess, sys
from pathlib import Path

spike = Path("/mnt/external/Hermes/spikes/wol-switch")
name = sys.argv[1]  # e.g. wol-horizon-build-dtime1
elf = spike / name / "wol-horizon"
ref = json.loads((spike / "prof-round/m5-layout-resaudit1.json").read_text())
out = spike / "prof-round" / ("m5-layout-" + name.replace("wol-horizon-build-", "") + ".json")

nm = subprocess.run(["nm", "-S", "--defined-only", str(elf)], capture_output=True, text=True).stdout
syms = {}
for line in nm.splitlines():
    parts = line.split()
    if len(parts) >= 4 and parts[3] in ("heap_size", "nregions", "nvn_pools", "nvn_textures", "nvn_textures_high", "regions"):
        syms[parts[3]] = {"offset": int(parts[0], 16), "size": int(parts[1], 16)}
missing = [k for k in ref["symbols"] if k not in syms]
assert not missing, f"symbols missing in {name}: {missing}"

src = Path("/mnt/external/Hermes/spikes/wol-switch/wol-horizon-source/native")
source_sha = {}
for f, _ in ref["source_sha256"].items():
    p = src / f
    source_sha[f] = hashlib.sha256(p.read_bytes()).hexdigest()

doc = dict(ref)
doc["elf_sha256"] = hashlib.sha256(elf.read_bytes()).hexdigest()
doc["symbols"] = syms
doc["source_sha256"] = source_sha
out.write_text(json.dumps(doc, indent=2) + "\n")
print("WROTE", out)
print("elf_sha256", doc["elf_sha256"])
for k, v in syms.items():
    print(f"  {k}: offset=0x{v['offset']:x} size=0x{v['size']:x}")
