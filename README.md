# West of Loathing — experimental Switch-to-Linux ARM64 port

**Status: early native-runtime bring-up, not a playable PortMaster release.**

This project explores executing the owner's Nintendo Switch ARM64/IL2CPP build on Linux ARM64, rather than repeating the previous x64/Box64 path. No game code, assets, keys, saves, NSP/NSZ or third-party runtime binaries are distributed here.

## Proven frontier

- Base Switch release inspected: Unity **5.6.5p1**, AArch64, IL2CPP; four NSO modules.
- Local data-stage mapping: 49.613 MiB; 215,921 relocations applied and read back by the independent Python preflight.
- The experimental C runtime enters the **original guest rtld**, without manually relocating that execution image.
- Under local `qemu-aarch64-static`, real guest code reaches Nintendo SDK startup, connects to `sm:` and completes CMIF SM Initialize.
- Current bounded stop: `UNIMPLEMENTED_SERVICE`, requested service **lm**, `sdk+0xa9d94`, 42 SVC calls after segment-permission hardening. See `evidence/native-run-12.log` (the earlier run is retained separately).
- The updated full local suite passes **21 tests** with owner inputs present: 15 native tests, one preparation integration test and five parser/preflight tests. Without owner inputs, 17 pass and four integration tests skip explicitly.

**Not proven:** Unity application startup, NVN rendering, audio, controls, scene-transition memory usage, native device execution or gameplay. QEMU execution is a bring-up test, not a handheld-performance benchmark.

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

1. Implement real LM/logging behavior, then the exact additional services requested by this SDK.
2. Add memory/thread/synchronization support with separate ABI tests; never fabricate successful service replies.
3. Establish Unity startup and resource-loading behavior before graphics adaptation.
4. Implement the WoL-specific NVN/shader path and bounded native device tests.
5. Require a real frame, controls/audio, scene transition and clean menu return before claiming a working port.
