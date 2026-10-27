# Native Unity host source

Upstream: https://github.com/wild1walker/portmaster-unity at `913debc122b8234a3db56939a4728d9438972ce2`, recursive libhybris `7079712a42ea2754adf747e70c6cc75764c8596e`.

`legacy-fmod-output.patch` contains the complete local host change and its tests. It connects the optional legacy Java-FMOD PCM callback; the OpenSL path, graphics, managed code and game data are not changed. Upstream MIT notices and third-party licenses are preserved in `port/westofloathing/licenses/`.

## Build

```sh
git clone --recurse-submodules https://github.com/wild1walker/portmaster-unity /path/to/portmaster-unity
git -C /path/to/portmaster-unity checkout 913debc122b8234a3db56939a4728d9438972ce2
git -C /path/to/portmaster-unity submodule update --init --recursive
# From this repository root, on a clean pinned checkout:
git -C /path/to/portmaster-unity apply "$PWD/runtime/unity/legacy-fmod-output.patch"
(cd /path/to/portmaster-unity && ARCH=arm64 TESTS=1 runtime/build.sh)
python3 /path/to/portmaster-unity/runtime/host/test/test_audio_wiring.py
```

The ARM64 build image targets Ubuntu 20.04. The installed host's highest referenced glibc version is GLIBC_2.30; the target loader resolved it with firmware libraries. Build variation can change the full ELF hash; compare the artifact and rerun device gates before replacing the accepted binary.

## Audio behavior tests

After the runtime build created `ua-build-arm64`:

```sh
cd /path/to/portmaster-unity/runtime
docker run --rm --platform linux/arm64 -v "$PWD":/w -w /w/host ua-build-arm64 sh -c \
  'gcc -O2 -g -Wall -Wextra -Werror -o out/arm64/test_legacy_audio test/test_legacy_audio.c -lSDL2 && out/arm64/test_legacy_audio'
```

This uses SDL's real dummy backend, checks queueing/drain/backpressure, rate changes, failure pacing, stalled-output timeout and cleanup. On a target, `test_legacy_audio silent` exercises one second of zero PCM through the selected SDL backend without starting the game or emitting a test tone; use only when no other process owns playback. Audio hardware writes are still not proof of audible game output.

Generic Mono runtime provenance is recorded in `port/westofloathing/runtime-manifest.json` and `licenses/LICENSE.mono.txt`: Unity's MIT-licensed Mono fork `538d2255088694b8d0fe78b2280a71b1b7bd94c3`, bdwgc `8440aa8cdffda0b9aa324a0e63f950f05551ab27`, libatomic_ops `268c37a63b3d77803c7cec6e5b318c015a9a157c`. Those generic glibc components are not Unity's proprietary Android player.
