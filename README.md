# West of Loathing — experimental Switch-to-Linux ARM64 port

**Status: early native-runtime bring-up, not a playable PortMaster release.**

This project explores executing the owner's Nintendo Switch ARM64/IL2CPP build on Linux ARM64, rather than repeating the previous x64/Box64 path. No game code, assets, keys, saves, NSP/NSZ or third-party runtime binaries are distributed here.

## Proven frontier

- Base Switch release inspected: Unity **5.6.5p1**, AArch64, IL2CPP; four NSO modules.
- Local data-stage mapping: 49.613 MiB; 215,921 relocations applied and read back by the independent Python preflight.
- The experimental C runtime enters the **original guest rtld**, without manually relocating that execution image.
- Under local `qemu-aarch64-static`, real guest code reaches Nintendo SDK startup, connects to `sm:` and completes CMIF SM Initialize.
- Native-probe/QEMU bounded stop: `UNIMPLEMENTED_SERVICE`, requested service **lm**, `sdk+0xa9d94`, 42 SVC calls after segment-permission hardening. See `evidence/native-run-12.log` (the earlier run is retained separately).
- The full local suite passes **22 tests** with owner inputs present: 15 native tests, two preparation integration tests and five parser/preflight tests. Without owner inputs, 17 pass and five integration tests skip explicitly.

**Not proven:** completed Unity application startup, visible NVN rendering, audio, controls, scene-transition memory usage or gameplay. QEMU execution is a bring-up test, not a handheld-performance benchmark.

## Native TSPS adapter milestone

A separate, recovered-GPL Horizon adapter now executes the original WoL modules **on TSPS**, through the Spruce principal launcher flow. Five bounded device launches progressed from queue-builder ABI failure to the first native shader request. The queue, memory-pool and buffer builder device offsets are +0 in this SDK, not the inherited +8; each is verified against the original SDK store instruction.

The adapter creates a real **Mali-G57 EGL / OpenGL ES 3.2 8×8 pbuffer**, initializes the queue, binds GPU memory pools and maps a buffer. This is **not a game window or presented frame**. Latest controlled stop: `WOL_SHADER_TRANSLATION_REQUIRED`, `main+0xafe4c8`, exit 20. The first old-format 2120-byte control section and a 512-byte GPU-code prefix were captured privately. No WoL shader translation exists yet.

Menu recovery is proven by `/proc` and a physical DRM `kmsgrab` screenshot after the last launch. The diagnostic binary stays installed; its first predecessor is backed up. Evidence and exact reproduction commands: [docs/tsps-horizon-adapter.md](docs/tsps-horizon-adapter.md).

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

1. Parse and translate the old WoL NVN shader packages, including the currently blocking first program; preserve exact native code/control identities.
2. Complete the WoL-specific NVN texture/window/command path, rejecting unknown layouts instead of borrowing another title’s offsets.
3. Establish real resource-loading/live-set behavior and a physical game frame.
4. Require controls/audio, scene transition and clean menu return before claiming a working port.
5. Keep the independent minimal probe’s LM/service frontier separate from the recovered adapter’s progress.

## Status (latest measured run)

| Subsystem | State |
|-----------|-------|
| ARM64 / IL2CPP guest | runs on the device |
| Horizon SVC / IPC | game runtime reached |
| Mali-G57 / EGL context | created and used |
| NVN command record + replay | works; 146-147 consecutive presents |
| Command arenas | **unused-tail overlap solved with evidence** (see below) |
| GLSL ES translation | 1 of 3 pairs translated + draw hook now keyed by code/control SHA-256 identity (review 2026-10-13); the other 2 pairs draw a clearly-marked TEST diagnostic colour; all draws execute with zero GL errors |
| Render targets | real GPU blit 1920x1080 -> 1280x720 |
| Present | route proven (run 106: the WOL_PRESENT_TEST marker written into the presenting texture appears as nonblack=4096 in every present readback; window textures are ids 30/31/32); the title's own content is still dark while loading is unfinished (run 100: 254/254 samples; textures 33 -> 108, terminated by the time governor); 763 translated + 1016 TEST diagnostic draws execute |
| Current state | run 104 (device-81): 924 presented frames with the quiet hot path (same 1800s budget; diagnostics were throttling the title); stopped at HID `SetNpadHandheldActivationMode` (cmd 128) - the family 123-129 is now implemented; a leftover dump-file leak (14.7k files, one ENOSPC stop) was cleaned and captures are gated behind `WOL_DUMP=1`. Run 100 (device-78): **no stop** - the time governor terminated it while the load was still advancing; the earlier `NVN_TEXTURE_SWIZZLE_REQUIRED` gate (format 0x39, swizzle B,G,R,A) was measured and fixed (gate + decode). Previous stops: `T2_MEMORY_FLOOR` (diagnostic; runs 91/95) and `NVN_GUEST_POINTER` (this runtime's own callback probe; fixed in runs 90-91) |

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
