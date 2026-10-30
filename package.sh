#!/bin/bash
# Copies a built port to the handheld. Env: OUT (build output), DEVICE (ssh host), DEST.
set -euo pipefail
OUT=${OUT:-$PWD/out}
DEVICE=${DEVICE:-tsps}
DEST=${DEST:-/mnt/SDCARD/Roms/PORTS/westofloathing}

tar -C "$OUT/pack/zip" -cf - . | ssh "$DEVICE" "tar -xf - -C $DEST"
scp -q "$OUT/il2cpp/lib/arm64-v8a/libil2cpp.so" "$DEVICE:$DEST/lib/libil2cpp.so"
scp -q port/West\ of\ Loathing.sh "$DEVICE:/mnt/SDCARD/Roms/PORTS/West of Loathing.sh"
ssh "$DEVICE" "sha256sum $DEST/WestofLoathing.apk $DEST/lib/libil2cpp.so | cut -c1-16"
