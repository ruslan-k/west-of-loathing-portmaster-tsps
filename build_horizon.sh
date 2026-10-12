#!/usr/bin/env bash
# Build recovered GPL source with owner-generated WoL contracts. No game payload is packaged.
set -euo pipefail
if [[ $# != 3 ]]; then
    printf 'Usage: %s RECOVERED_SOURCE OWNER_IMAGE NEW_OUTPUT\n' "$0" >&2
    exit 64
fi
source_root=$(realpath "$1")
image=$(realpath "$2")
output=$(realpath -m "$3")
recipe=$(cd "$(dirname "$0")" && pwd)
# Reject a modified or different recovered baseline before any build.
(cd "$source_root" && sha256sum -c "$recipe/runtime/source-manifest.sha256")
[[ ! -e "$output" ]] || { printf 'NEW_OUTPUT already exists: %s\n' "$output" >&2; exit 65; }
mkdir -p "$output/source"
cp -a "$source_root/native" "$source_root/framework" "$output/source/"
source_root="$output/source"
git -C "$source_root" init -q
git -C "$source_root" apply --check "$recipe/runtime/wol-adapter.patch"
git -C "$source_root" apply "$recipe/runtime/wol-adapter.patch"
: "${COTM_CC:=aarch64-linux-gnu-gcc}"
export COTM_CC
export COTM_NXINPUT_DIR="$source_root/framework/nxinput"
export COTM_NXCOMPAT_DIR="$source_root/framework/nxcompat"
export COTM_NXGL_DIR="$source_root/framework/nxgl"
export COTM_NXLOADER_DIR="$source_root/framework/nxloader"
export COTM_SDL_INCLUDE_DIR=/usr/include/SDL2
provider="$source_root/provider-build/nxaudio"
mkdir -p "$provider"
cp "$source_root/framework/nxaudio/include/"*.h "$provider/"
for name in nxaudio nxaudio_receipt nxaudio_runtime; do
    "$COTM_CC" -O2 -fPIC -pthread -std=c11 -D_POSIX_C_SOURCE=200809L \
        -I"$provider" -c "$source_root/framework/nxaudio/src/$name.c" -o "$provider/$name.o"
done
aarch64-linux-gnu-ar rcs "$provider/libnxaudio.a" "$provider/"*.o
export COTM_NXAUDIO_DIR="$provider"
export TMPDIR="$output/scratch"
mkdir -p "$TMPDIR"
bash "$source_root/native/build.sh" "$image" "$output/native-build"
mv "$output/native-build/legacy_runtime-nextos" "$output/wol-horizon"
