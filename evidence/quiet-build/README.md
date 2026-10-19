# Quiet release build (owner request, 2026-10-19)

Ordinary play must not write diagnostic volumes. The accepted `b60057ea…` runtime printed a
per-frame line, a per-syscall trace line and a per-upload receipt; on a full SD card that is a
real hazard (~1.5 KB/frame, ~2.7 MB/min — see `../log-volume/README.md`).

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

**Runtime source** (published in `runtime/wol-adapter.patch`): the remaining hot-path prints are
gated on `aw_release_mode()` — per-syscall `SVC` trace (`emit_svc`), `NVN_CALL` trace, the
`WOL_SPRITE_SCAN` readback (a full `glReadPixels` of the target on sprite draws) and the
`ZERO_TEXTURE_FLUSH_UPLOADED` / `ZERO_REFRESH_STATS` receipts. Fail-closed `stop()` receipts, the
black-screen guard, memory floor and every functional path are untouched; the game's own
debug-string echo (svc `0x27`) still passes through.

## Build and deployment

- Build: `build_horizon.sh` from the manifest-pinned baseline + the regenerated overlay, in
  `pmjs-arm64-spruce-local:20261002-gcc10`; 435/435 manifest OK, patch applies cleanly.
- New ELF **`072d07691ffe0b236d0d7243b12ec03fa2bb96dca4c933d551d3cedcd74e0bde`** (1,974,840 B).
- Deployed to `/mnt/SDCARD/Roms/ports/wol-switch/wol-horizon`; the accepted `b60057ea…` ELF is
  preserved at `backups/wol-horizon.b60057ea-accepted.bak` for an immediate rollback.
- All accepted feature markers are present in the new ELF and in `b60057ea…`
  (`WOL_UPRENDER_720`, `T2_TRANSFER_SPARSE_COPY`, `NVN_COMMAND_RECORD_SIZE`, `WOL_ROMFS_COW`, …).
- The 720 UpRender default is unchanged; game behaviour, shader substitution and memory handling
  are untouched — this is a **logging-only** delta.

## Verification status

- Launcher: `bash -n` OK; default/override matrix covered by tests (unset→1, `0`→0, `1`→1 for
  both `WOL_UPRENDER_720` and `AW_RELEASE`); data-free suite 94 tests green.
- Overlay: regenerated from the baseline and verified to reproduce the current source tree with
  **0 differences**; CI parses and tests it.
- **Live smoke run on the device was not possible in this pass** — the owner was playing another
  title (Iconoclasts) and Spruce MainUI was not running. First WoL launch after this change is the
  pending verification: it must show the game, write a small `latest.log`, and return to Spruce.
  Rollback is one file copy from `backups/wol-horizon.b60057ea-accepted.bak`.
