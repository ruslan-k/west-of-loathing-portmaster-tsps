#!/bin/bash
# Builds the port from a Steam install: managed patches -> IL2CPP -> Game_Data + apk.
# Env: UNITY_DATA (…/West of Loathing_Data), TOOLKIT (portmaster-unity checkout),
#      UNITY_PLAYER (Android player package, see the toolkit's README), OUT, JOBS.
set -euo pipefail

UNITY_DATA=${UNITY_DATA:?set UNITY_DATA to the game's "…_Data" directory}
TOOLKIT=${TOOLKIT:?set TOOLKIT to the portmaster-unity checkout}
OUT=${OUT:-$PWD/out}
JOBS=${JOBS:-$(nproc)}
HERE=$(cd "$(dirname "$0")" && pwd)
export PMUNITY_IL2CPP_HOME=${PMUNITY_IL2CPP_HOME:-$HOME/.cache/pmunity/il2cpp}

rm -rf "$OUT"
mkdir -p "$OUT"

echo "== convert"
(cd "$TOOLKIT/convert" && python -m pmunity convert "$UNITY_DATA" "$OUT/conv")

echo "== managed patches"
(cd "$HERE/tools/dlcpatch" && dotnet build -c Release -o out >/dev/null)
dotnet "$HERE/tools/dlcpatch/out/dlcpatch.dll" "$UNITY_DATA/Managed" "$OUT/patched"
cp -a "$UNITY_DATA" "$OUT/src"
cp "$OUT/patched"/*.dll "$OUT/src/Managed/"

echo "== Rewired + StreamingAssets paths"
dotnet "$TOOLKIT/tools/asmpatch/out/any/asmpatch.dll" --only=rewired-android,streaming-assets \
    "$OUT/src/Managed" "$OUT/asmp"
cp "$OUT/asmp"/*.dll "$OUT/src/Managed/"

echo "== Kartridge stub"
(cd "$HERE/tools/stubasm" && dotnet build -c Release -o out >/dev/null)
dotnet "$HERE/tools/stubasm/out/stubasm.dll" Kartridge "$OUT/src/Managed"

echo "== IL2CPP"
(cd "$TOOLKIT/convert" && python -m pmunity il2cpp "$OUT/src" "$OUT/il2cpp" \
    --abi arm64-v8a --pkg "$UNITY_PLAYER" --jobs "$JOBS")

echo "== pack"
(cd "$TOOLKIT/convert" && python -m pmunity android-data --src "$OUT/conv" --pkg "$UNITY_PLAYER" \
    --il2cpp "$OUT/il2cpp" --out "$OUT/pack" --name WestofLoathing \
    --package com.pmunity.wolil2cpp --streaming-assets both --pack all)

echo "done: $OUT/pack"
