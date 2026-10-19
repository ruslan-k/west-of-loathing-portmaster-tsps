#!/usr/bin/env bash
# One iteration: regenerate the WoL overlay, build, deploy atomically, run the
# bounded principal-flow test on TSPS, collect logs + menu capture into evidence.
# Usage: device_cycle.sh <build-dir-name> <evidence-dir-name>
set -euo pipefail
BUILD=${1:?build dir name}
EVID=${2:?evidence dir name}
REPO=/mnt/external/Hermes/west-of-loathing-portmaster-tsps
SPIKE=/mnt/external/Hermes/spikes/wol-switch
IMAGE=$SPIKE/wol-horizon-image
BASE=$SPIKE/upstream-source
SRC=$SPIKE/wol-horizon-source
OUT=$SPIKE/$BUILD
cd "$REPO"

# 1. Overlay patch = our modifications against the verified recovered baseline.
python3 - "$BASE" "$SRC" "$REPO/runtime/wol-adapter.patch" <<'EOF'
import pathlib,sys,difflib
base,src,out=map(pathlib.Path,sys.argv[1:4])
chunks=[]
for p in sorted((base/'native').iterdir()):
    q=src/'native'/p.name
    if p.is_file() and q.is_file() and p.read_bytes()!=q.read_bytes():
        chunks.extend(difflib.unified_diff(p.read_text().splitlines(True),q.read_text().splitlines(True),
                                           fromfile='a/native/'+p.name,tofile='b/native/'+p.name))
out.write_text(''.join(chunks))
print('overlay bytes',out.stat().st_size)
EOF

# 2. Build in the pinned local cross environment; the recipe itself re-verifies
#    the 435-file baseline and refuses an existing output directory.
docker run --rm --security-opt label=disable \
  -v "$SPIKE:/workspace" -v "$REPO:/work" --entrypoint /bin/sh \
  pmjs-arm64-spruce-local:20261002-gcc10 \
  -c "cd /work && bash build_horizon.sh /workspace/upstream-source /workspace/wol-horizon-image /workspace/$BUILD" \
  > "$SPIKE/$BUILD.log" 2>&1
echo "build ok: $OUT/wol-horizon"

# 3. Deploy the exact bytes and record the receipt.
scp -O "$OUT/wol-horizon" root@192.168.50.135:/mnt/SDCARD/Roms/PORTS/wol-switch/wol-horizon.next
SHA=$(sha256sum "$OUT/wol-horizon" | cut -d ' ' -f 1)
ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=none root@192.168.50.135 \
  python3 - "$SHA" < "$SPIKE/device_activate.py"

# 3b. Keep the device launcher byte-identical to the repository copy (single source of truth;
#     the harness passes the diagnostic floor explicitly, the launcher default is conservative).
ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=none root@192.168.50.135 \
  "cat > '/mnt/SDCARD/Roms/PORTS/West of Loathing.sh' && chmod a+x '/mnt/SDCARD/Roms/PORTS/West of Loathing.sh' && sha256sum '/mnt/SDCARD/Roms/PORTS/West of Loathing.sh'" \
  < "$REPO/West of Loathing.sh"

# 4. Bounded device run through the real Spruce principal flow.
ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=none root@192.168.50.135 \
  python3 - < "$SPIKE/device_principal_test.py" > "$SPIKE/$BUILD.run.txt" 2>&1 || true

# 5. Evidence.
mkdir -p "$REPO/evidence/$EVID"
scp -O root@192.168.50.135:/mnt/SDCARD/Roms/PORTS/wol-switch/logs/latest.log "$REPO/evidence/$EVID/runtime.log"
scp -O root@192.168.50.135:/mnt/SDCARD/Roms/PORTS/wol-switch/logs/after-menu.png "$REPO/evidence/$EVID/after-menu.png"
python3 - "$REPO/evidence/$EVID/runtime.log" <<'EOF'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text().splitlines()
keep=[l for l in s if l.startswith(('WOL_','STOP ','NVN_GLES2_DEVICE_REAL','VmRSS:','WOL_RUNTIME','NVN_SAMPLER','AW_SAMPLER','NVN_TEXTURE')) 
      or 'PROGRAM_INVENTORY' in l or 'PROGRAM_BOUND' in l]
print('\n'.join(keep[-50:]))
EOF
echo "run tail: $(tail -1 "$SPIKE/$BUILD.run.txt")"
