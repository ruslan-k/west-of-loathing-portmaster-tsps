# Quiet release build (owner request, 2026-10-19)

Ordinary play must not write diagnostic volumes. The accepted `b60057ea…` runtime printed a
per-frame line, a per-syscall trace line and a per-upload receipt; on a full SD card that is a
real hazard — measured at **~1.5 KB/frame, ~2.6–2.9 MB/min, ~160 MB/hour** (see `../log-volume/`).

**HEAD correction (f4c9b23, 2026-10-19):** the final published/deployed quiet overlay intentionally
**restores** the bounded `WOL_SPRITE_SCAN` path (up to twelve full-target `glReadPixels` operations)
because the diagnostic path currently consumes a pending `glGetError()`; removing the scan
exposed a subsequent fail-closed error in `zero_texture_refresh`. The bounded
`WOL_PAIR_PIXELS` readbacks also remain in the overlay. The paragraphs below describing
scan suppression refer to the initial, superseded quiet-build candidate, **not** to the final
`ab132760…` runtime. This is a GL error-ownership/correctness issue, not a measured
steady-state FPS opportunity; see roadmap §19.2 Q2 / §19.3 P0-3. No gameplay smoke run of the
final quiet build has been recorded here.

## What changed

**Launcher `West of Loathing.sh`** (renamed from `West of Loathing Switch.sh`):

| Setting | Was | Now | Effect |
| --- | --- | --- | --- |
| `AW_RELEASE` | unset | **1** | owner-facing release profile: no diagnostic receipts, no per-frame present line, no diagnostic files next to the game |
| `T2_READBACK_OFF` | 0 | **2** | sample until the first image proof, then explicit captures only (removes the 150–220 ms periodic readback) |
| `COTM_PRESENT_READBACK_60` | 1 | **0** | no sparse per-60-frame readback |
| `WOL_PAIR_CHECK` | 1 | **0** | one-time diagnostic GLSL check off |
| `WOL_QUIET` | 1 | 1 | unchanged (per-draw content probing already off) |

Every value keeps its `:-` override, so diagnostics still run with
`AW_RELEASE=0 T2_READBACK_OFF=0 COTM_PRESENT_READBACK_60=1 WOL_PAIR_CHECK=1 WOL_DUMP=1`.

**Runtime source** (published in `runtime/wol-adapter.patch`): diagnostics are gated on
`aw_release_mode()` in three layers.

1. *Hot paths that cost real time*: per-syscall `SVC` trace (`emit_svc`), `NVN_CALL` trace, upload
   receipts, sparse readbacks. **The sprite-scan readback is deliberately NOT gated**: it consumes
   pending GL errors via `glGetError()`, so removing it could surface an otherwise-swallowed error
   in the fail-closed refresh check. Its cost is bounded (first twelve draws) and it stays.
2. *Bulk log spam*: `NVN_COMMANDS_EXECUTED`, `NVN_RESULT`, `NVN_TEXTURE_REAL`, `ZERO_TEXEL_WRITE`
   / `ZERO_TEXEL_FLUSH(_DEFERRED)`, `T2P_CB_CALL_BEGIN` / `_END`, `T2P_CMDMEM_CALLBACK_TIME`,
   `T2P_CB_NVN`, `WOL_COMMAND_ARENA_POOL_RECYCLE`, `AUDOUT_HOST_PROFILE`.
3. *Everything else diagnostic*: a single helper `diag_printf()` in `aw_release.h` that returns
   without printing when `AW_RELEASE=1`. **722 `printf` sites across 103 files** were converted.

**Never gated:** the `stop()` fail-closed receipt (it builds its line with `text()`/`emit()` and a
raw `write()`, not `printf`), the black-screen guard, the memory floor, `START`, `HOST_BASE`,
`T2_ALIAS_REGION`, `WOL_UPRENDER_CONFIG`, the guest's own debug-string echo (svc `0x27`) and the
once-per-20 s `T2_MEMWATCH_SAMPLE` pressure line.

## Measured

| build | per-session log | steady state |
| --- | --- | --- |
| `b60057ea…` accepted | 54 MB (one long session), 8.0 MB (one play session) | ~2.7 MB/min |
| `ab132760…` stage 2 (hot paths + 13 bulk tags) | 8.0 MB | ~124 KB/min |
| **`fef4f783…` stage 3 (global `diag_printf`)** | **49 KB** | **1.5 KB/min** (1139 B / 18 lines in 45 s) |

That is ~1800× less than the accepted build's rate, with no rendering, shader-substitution, memory
or guard behaviour touched.

## Build and deployment

- Overlay regenerated from the pinned baseline: 107 files, 843 774 B, applies cleanly and reproduces
  the source tree with **0 differences**.
- Build `build_horizon.sh` in `pmjs-arm64-spruce-local:20261002-gcc10`: **0 errors**, all accepted
  feature markers present (`WOL_UPRENDER_720`, `T2_TRANSFER_SPARSE_COPY`, `NVN_COMMAND_RECORD_SIZE`,
  `WOL_ROMFS_COW`, …).
- Deployed ELF **`fef4f7831407e21459c51cce17e19a8474de014d2e737f695117b5f02e5525b9`** (1 966 864 B).
- Rollbacks kept on device: `backups/wol-horizon.ab132760-quiet1.bak`,
  `backups/wol-horizon.a38ff2eb-quiet2.bak`, `backups/wol-horizon.b60057ea-accepted.bak`.
- The 720 UpRender default is unchanged; game behaviour, shader substitution and memory handling
  are untouched — this is a **logging-only** delta.

## Verification status

- Launcher: `bash -n` OK; default/override matrix covered by tests (unset→1, `0`→0, `1`→1 for
  both `WOL_UPRENDER_720` and `AW_RELEASE`); data-free suite 94 tests green.
- Overlay: regenerated from the baseline and verified to reproduce the current source tree with
  **0 differences**; CI parses and tests it.
- Live on hardware: game boots to the menu, 45 s of steady play added **1139 bytes / 18 lines**
  (≈1.5 KB/min), 49 KB for the whole session including boot.
- The device was rebooted afterwards to restore the Spruce menu after a handoff experiment left
  `principal.sh` waiting in `wait4`; it came back normally (MainUI up, no port processes).
- Still open from the acceptance track: a full SAVE→QUIT→cold-launch→LOAD cycle and town-building
  interiors (see `../release-720/README.md`). Logging work does not change those.
