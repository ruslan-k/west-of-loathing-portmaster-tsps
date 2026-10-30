# West of Loathing — TrimUI Smart Pro S / SpruceOS

**Installed runtime:** native ARM64 Unity/Mono with audio and packaged Reckonin' at Gun Manor assets. **Release qualification is NOT complete:** requested update/version equivalence, ordinary DLC quest entry, real moving-gameplay FPS and cold save/reload are unverified.

The **installed, user-facing** layout is [`port/`](port/README.md): one **West of Loathing.sh** launcher and one **westofloathing/** directory. It replaced the older Switch/Horizon installation. The **separate Switch v327680 Horizon/NVN→GLES candidate is still under active experimental development**, but it is **not** the current installed port; its FPS, memory and GPU measurements cannot be used to characterize the native Unity installation.

## What works and what is not yet certified

- Owned Linux Mono data runs on Unity's exact **2017.4.19f1 Android ARM64 player**, using [portmaster-unity](https://github.com/wild1walker/portmaster-unity) and its Mono bridge. Generic ARM64 Mono components come from [portmaster-cuphead](https://github.com/wild1walker/portmaster-cuphead).
- Real TSPS KMS captures verified the title, character creation, base-game interiors and Gun Manor. The DLC check remains the game's own check; the diagnostic DLC scene test used a duplicate save, not the normal quest-entry chain.
- The owner reports fast rendering and confirms audible sound after the legacy-FMOD output fix. Current-run logs corroborate nonzero PCM reaching system SDL/ALSA. Initialization logs alone were not sound acceptance.
- Shader conversion uses highp GLES; ASTC conversion keeps texture dimensions and mip counts. The eight archived StreamingAssets files are byte-identical to the earlier converted loose package.
- **No zero-swap or fixed-FPS guarantee.** A bounded DLC archive test sampled up to 710.71 MiB RSS and 173.12 MiB swap. Full-game endurance, ordinary DLC quest entry and a complete cold save/reload cycle remain open. Earlier unattended transitions also remain unexplained; do not credit them as physical-input proof.

See [current verification](docs/native-unity-port.md) for exact hashes, evidence boundaries and migration details.

**Mandatory update+DLC release policy (2026-10-30):** see the [authoritative §28 roadmap](docs/optimization-roadmap-active-native-unity-2026-10-29.md#28-mandatory-update-and-dlc--architecture-and-optimization-reset-2026-10-30) and [owner content/functional acceptance gate](docs/release-gate-update-dlc-2026-10-30.md). No candidate may be called finished without **both** the required Switch update `v327680` (or an explicitly accepted and evidenced updated-PC content equivalent) **and** the **Reckonin' at Gun Manor** DLC, including normal entry, state/save reload, verified audio/controls and real ≥30 FPS in representative gameplay. The installed Unity branch has [41.4–41.6 host FPS with sound and 0 VmSwap in a 90s principal-flow test](evidence/unity-trackA-2026-10-30/README.md), **but no moving gameplay/DLC-entry or original Linux content-update provenance**. Thus it is **NOT** a verified substitute for v327680. The experimental Switch/Horizon branch has [AOC + separate DLC RomFS source/tests](tools/test_wol_memory_aoc_storage.py) and an updated v327680 image table, but normal DLC game flow and 30 FPS remain unproved. Latest [H2 diagnostics](evidence/horizon-h2-2026-10-30/README.md) attribute a per-frame full 1280×720 `source 2→destination 82` CPU copy/GL upload: suppressing refresh improves its own benchmark from 42.90 to 37.37 ms **with stale pixels**, still only ~26.8 FPS and therefore invalid. Do **not** suggest base-only/old Linux or DLC-incomplete Unity as a faster shipping route; do **not** spend weeks rewriting C into Rust/Zig before validating content and GPU dataflow. Latest [CI 41080886647](https://github.com/ruslan-k/west-of-loathing-portmaster-tsps/actions/runs/41080886647) passed but is data-free and cannot certify user-owned update/DLC.

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
