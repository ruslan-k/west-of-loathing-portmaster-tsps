# West of Loathing — TrimUI Smart Pro S / SpruceOS

**Current port: native ARM64 Unity, packed game + Reckonin' at Gun Manor DLC, working audio confirmed by the owner.**

The **installed, user-facing** layout is [`port/`](port/README.md): one **West of Loathing.sh** launcher and one **westofloathing/** directory. It replaced the older Switch/Horizon installation. The **separate Switch v327680 Horizon/NVN→GLES candidate is still under active experimental development**, but it is **not** the current installed port; its FPS, memory and GPU measurements cannot be used to characterize the native Unity installation.

## What works and what is not yet certified

- Owned Linux Mono data runs on Unity's exact **2017.4.19f1 Android ARM64 player**, using [portmaster-unity](https://github.com/wild1walker/portmaster-unity) and its Mono bridge. Generic ARM64 Mono components come from [portmaster-cuphead](https://github.com/wild1walker/portmaster-cuphead).
- Real TSPS KMS captures verified the title, character creation, base-game interiors and Gun Manor. The DLC check remains the game's own check; the diagnostic DLC scene test used a duplicate save, not the normal quest-entry chain.
- The owner reports fast rendering and confirms audible sound after the legacy-FMOD output fix. Current-run logs corroborate nonzero PCM reaching system SDL/ALSA. Initialization logs alone were not sound acceptance.
- Shader conversion uses highp GLES; ASTC conversion keeps texture dimensions and mip counts. The eight archived StreamingAssets files are byte-identical to the earlier converted loose package.
- **No zero-swap or fixed-FPS guarantee.** A bounded DLC archive test sampled up to 710.71 MiB RSS and 173.12 MiB swap. Full-game endurance, ordinary DLC quest entry and a complete cold save/reload cycle remain open. Earlier unattended transitions also remain unexplained; do not credit them as physical-input proof.

See [current verification](docs/native-unity-port.md) for exact hashes, evidence boundaries and migration details.

**Current optimization decision (2026-10-30):** use the [§27 strategic-reset roadmap](docs/optimization-roadmap-active-native-unity-2026-10-29.md#27-strategic-reset--stop-loss-and-alternative-architectures-2026-10-30). The **installed native Unity/Mono port is the fastest path to a complete game**: owner-confirmed audio and historical pre-audio DLC samples ~32.5–32.7 FPS, but post-audio physical 30 FPS, normal DLC entry, cold save/reload and endurance still require acceptance. The **separate Horizon/NVN→GLES branch** is ~24.7 runtime presents/s in measured heavy gameplay and has severe CMA/swap headroom limits. Its previously blocking CI and image-table mismatch are **fixed**, with [GitHub Actions 41056348398 green](https://github.com/ruslan-k/west-of-loathing-portmaster-tsps/actions/runs/41056348398); [H-D1](evidence/horizon-hd1-2026-10-30/H-D1-MEASURED.md) locates ~5.644 ms/frame of DrawArrays CPU in texture selection, and [H-S0](evidence/horizon-e1c-abc-2026-10-30/H-S0-SUMMARY.md) locates ~6.774 ms/frame **wall** inside `zero_texture_refresh`. These are not verified net FPS gains. Horizon now has only one optional read-only texture-owner proof and one conditional reversible A/B before a stop-loss decision. **Do not rewrite the whole C runtime in Rust/Zig merely for FPS**: the bottleneck is GPU/texture resource behavior and the already-working native Unity port remains separate. The [old Switch/Horizon roadmap](docs/optimization-roadmap.md) is historical.

## Install / build

The repository includes the ARM64 host, generic Mono runtime components, licenses and data-free build/packing code. It **does not include the game, DLC, Unity player libraries, managed Unity assemblies, APK, saves or extracted console files**.

1. Use your own Linux game data and the exact Unity player; follow [`tools/unity/README.md`](tools/unity/README.md).
2. Assemble the owner-only payload with the [`port/`](port/README.md) layout.
3. Copy **West of Loathing.sh** and **westofloathing/** to `/mnt/SDCARD/Roms/PORTS/`, then launch from Spruce's Ports menu.

The launcher keeps progress in `westofloathing/data/external/` and port-local configuration in `westofloathing/home/`. Do not replace these directories when updating runtime files. The promoted device installation preserves them byte-for-byte.

## Data-free tests

```sh
python3 -m unittest -v test_unity_port test_bounded_run
# Current Unity audio regression, against the pinned upstream checkout:
python3 /path/to/portmaster-unity/runtime/host/test/test_audio_wiring.py
```

The audio overlay includes real SDL queue/drain/error tests. [`runtime/unity/README.md`](runtime/unity/README.md) documents the ARM64 build and target preflight. The old ARM64 instruction/IPC and asset-analysis tests are still maintained by CI, but do not qualify the current Unity port.

## Source and licensing

- Main host/converter upstream: MIT, pinned commit `913debc122b8234a3db56939a4728d9438972ce2`.
- Mono source/license provenance and all third-party notices ship in `port/westofloathing/licenses/`.
- Our repository remains GPL-3.0; the upstream MIT notices are preserved. The generic Mono bridge/runtime is distinct from Unity's proprietary `libunity.so` and `libmain.so`, which are not distributed here.
- No game data, keys, saves or raw decompilation are published.

## Historical research

The independent experimental Switch route lives in [`docs/tsps-horizon-adapter.md`](docs/tsps-horizon-adapter.md), [`docs/optimization-roadmap.md`](docs/optimization-roadmap.md), `build_horizon.sh`, the current isolated Horizon evidence and earlier historical directories. Older performance figures and acceptance statements apply only to the exact artifacts they name. The shipped Switch runtime and its menu launcher are no longer part of `port/`, even though development on the isolated Horizon candidate continues.
