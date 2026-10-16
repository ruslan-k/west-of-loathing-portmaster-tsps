# West of Loathing — experimental Switch-to-Linux ARM64 port

**Status: experimental native runtime with real menu/gameplay frames; not a validated PortMaster release.**

Latest device evidence: [gfx265](evidence/gfx265/README.md). Skinned PC/Cactus Bill bodies and the WANTED portrait mask are restored. The map paper-size repair is installed, but marker/title overlap remains open. Code, tests, hashes, physical captures and a measured resource baseline are recorded together. [Next resource-optimization tests](docs/resource-optimization.md) are candidates, not claimed gains.

This project explores executing the owner's Nintendo Switch ARM64/IL2CPP build on Linux ARM64, rather than repeating the previous x64/Box64 path. No game code, assets, keys, saves, NSP/NSZ or third-party runtime binaries are distributed here.

## Independent minimal-probe frontier (historical baseline)

- Base Switch release inspected: Unity **5.6.5p1**, AArch64, IL2CPP; four NSO modules.
- Local data-stage mapping: 49.613 MiB; 215,921 relocations applied and read back by the independent Python preflight.
- The experimental C runtime enters the **original guest rtld**, without manually relocating that execution image.
- Under local `qemu-aarch64-static`, real guest code reaches Nintendo SDK startup, connects to `sm:` and completes CMIF SM Initialize.
- Native-probe/QEMU bounded stop: `UNIMPLEMENTED_SERVICE`, requested service **lm**, `sdk+0xa9d94`, 42 SVC calls after segment-permission hardening. See `evidence/native-run-12.log` (the earlier run is retained separately).
- The full local suite passes **22 tests** with owner inputs present: 15 native tests, two preparation integration tests and five parser/preflight tests. Without owner inputs, 17 pass and five integration tests skip explicitly.

These minimal-probe tests do not prove application rendering or performance. The recovered adapter below has progressed further; QEMU is not a handheld-performance benchmark.

## Native TSPS adapter — current verified scope

A separate, recovered-GPL Horizon adapter executes the original WoL modules **on TSPS**, through the Spruce principal launcher flow. It presents the actual menu and Boring Springs scene through Mali/EGL/KMSDRM. The owner-bundle mip repack is paired with repaired Sprite metadata and matching launcher UV defaults; an old bundle and new defaults are not interchangeable.

The current overlay honors multi-stream mesh attributes, samples mesh UV x/y with the material transform, keeps mesh/display-composite identities separate, and replays the game's portrait stencil. Focused regression checks and 22 existing tests pass. Physical captures verify restored bodies, portrait clipping and return to Spruce; this is not full-game, physical-control, scene-transition or endurance certification.

Current runtime SHA-256: `c25640beebcfb86000545438725a52c4bf5d8a1a440f22aab43218154969b5b7`. Owner payload and launcher read-back receipts are in [gfx265/deployment.json](evidence/gfx265/deployment.json); proprietary bundle/binary data is not committed. The own diagnostic session was stopped, CPU mask restored to `4-7`, and the real Spruce PORTS screen checked. Historical development notes: [docs/tsps-horizon-adapter.md](docs/tsps-horizon-adapter.md).

## Build and test without game data

On a Debian/Ubuntu development machine, install an AArch64 compiler and QEMU user-mode emulator. Then:

```sh
./build.sh
python3 -m unittest -v test_native
```

The self-tests execute deliberately small synthetic ARM64 instruction fixtures. They are not presented as game execution. The runtime uses an alternate signal stack, patches SVC/TLS instructions in anonymous mappings only, and stops on unsupported operations. Diagnostic signal logging is prototype-only and is not production async-signal-safe.

For the development container used in the recorded local tests:

```sh
docker run --rm --security-opt label=disable -v "$PWD:/work" \
  --entrypoint /bin/sh pmjs-arm64-spruce-local:20261002-gcc10 \
  -c 'cd /work && ./build.sh'
```

That image is a local build environment, not a public dependency or a distributed runtime.

## Owner-input preparation and bounded execution

Install Python `lz4`. Supply a locally extracted, lawfully owned base ExeFS containing `rtld`, `main`, `subsdk0`, `sdk`:

```sh
python3 prepare_image.py /path/to/owner/exefs owner-image
# Output includes owner game bytes; never commit/share it.
timeout 25s qemu-aarch64-static ./wol-native-probe \
  owner-image/segments owner-image/native-layout.txt
```

The native probe also arms a 20-second wall watchdog. A controlled unsupported-operation stop is expected, not a success code. Do not deploy this diagnostic as a working handheld launcher.

For broader offline analysis, supply an owner tree with `exefs/` and `romfs/`:

```sh
python3 inspect_nso.py /path/to/owner/tree --output wol-analysis.json
```

The Python `map_preflight.py` is a separate RW-only, non-executing relocation experiment. It does not implement Horizon OS. Owner-dependent tests are distinct from the data-free native self-tests.

## Important memory gate

The Switch `core` UnityFS bundle is 191.085 MiB on disk, but its block metadata describes 2063.993 MiB uncompressed. This is not peak RSS or proof of all-at-once loading. Native ARM64 eliminates x64 translation only if the compatibility layer succeeds; it does not automatically solve the previous device OOM.

## Reference sources

- The supplied CotM 1.0.7 package establishes the architecture, but its native source companion was not included and was not found in the accessible NextOs-Ports public repositories/releases.
- The owner's legacy_runtime 1.0.16 package **does include complete runtime source** in `runtime-source.patch` and `nxgl-source.patch`. Both were reconstructed locally; all 435 entries in its source manifest match SHA-256.
- Its IPC/TLS/loader code is a compatibility reference, not proof that its game-specific addresses/shaders/NVN layouts support WoL. Source provenance and licensing are recorded in `docs/upstream-source.md`.

This repository is GPL-3.0. Third-party reference packages remain local; the repository contains our diagnostic code, tests, reports and logs, not game-derived binaries.

## Next gates

1. Finish map marker/title placement against a reference; paper size alone is not a complete map fix.
2. Run the isolated logging/readback/memory/CPU-placement experiments in [resource-optimization.md](docs/resource-optimization.md), preserving the verified visual baseline.
3. Measure startup and scene-transition live memory and active swap I/O, not only stationary-scene RSS.
4. Require physical controls/audio, scene transitions, save/load and sustained gameplay before claiming a release.
5. Keep the independent minimal probe’s LM/service frontier separate from the recovered adapter’s progress.

## Historical status snapshot (gfx252; superseded by gfx265 above)

| Subsystem | State |
|-----------|-------|
| ARM64 / IL2CPP guest | runs on the device |
| Horizon SVC / IPC | game runtime reached |
| Mali-G57 / EGL context | created and used |
| NVN command record + replay | works; 146-147 consecutive presents |
| Command arenas | **unused-tail overlap solved with evidence** (see below) |
| GLSL ES translation | shader catalogue keyed by code/control SHA-256; the TOP pair (menu/world sprites), top2, f191 and f268 are live; the f191 tiled-uv fold (fract) restored the WANTED-poster figure and the control-box button icons (gfx251/252, build-227) |
| Render targets | real GPU blit 1920x1080 -> 1280x720 |
| Present | **rasterized geometry reaching the presented frame (run 115: the real pair draw turns all 193 present readbacks green - nonblack=460800 = half of 1280x720; the VBO upload fixed the stale GL_ARRAY_BUFFER binding that had silenced every pair fragment)**; drawn content is still the TEST green fragment. Route proven earlier (run 106: the WOL_PRESENT_TEST marker written into the presenting texture appears as nonblack=4096 in every present readback; window textures are ids 30/31/32); the title's own content is still dark while loading is unfinished (run 100: 254/254 samples; textures 33 -> 108, terminated by the time governor); 763 translated + 1016 TEST diagnostic draws execute |
| Current state | gfx252 (build-227, sha d776be3d...): the main menu renders with its WANTED poster figure + name, the MOVE/AIM/FIRE control box with button glyphs, the hanging sign and planks - production defaults, no env overrides; the f191 family's out-of-range uv are the page/tiled convention and the draft fragment folds them with `fract(v9)`; the probe tool no longer ships shader selectors in its base env (`WOL_F191_UV=''` = the true draft; experiments go through `--set`). Earlier: run 104 (device-81) 924 presented frames with the quiet hot path; the swizzle gate (format 0x39) measured and fixed; `T2_MEMORY_FLOOR` stops (runs 91/95) |

### Command arena: what was measured

```
WOL_ARENA_OVERLAP owner=0x1000a7f010 pool=... old=0x107595c000 old_size=2097152 old_used=2097088
                 limit=2097152 new=0x1075b5bfc0 new_size=2083008 overlap=64 current=0 recording=1
                 generation=2 safe_end=0x1075b5bfc0 classification=UNUSED_TAIL
WOL_COMMAND_ARENA_RETIRE ... action=RETIRED_TAIL
```

The previous arena's `used` cursor ends exactly where the new arena begins, and no retained range or live
list reaches into the overlap, so the tail is retired and the new arena is registered. Everything else stays
fail-closed with the original `NVN_COMMAND_ARENA_OVERLAP`.
