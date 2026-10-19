# West of Loathing — portable layout

Drop-in layout for the native aarch64 runtime, mirroring
[`the-dream-machine-portmaster-tsps/port`](https://github.com/ruslan-k/the-dream-machine-portmaster-tsps/tree/main/port).

```
port/
  West of Loathing.sh      PortMaster launcher (also works from the plain TSPS path)
  wol-switch/
    wol-horizon            runtime binary (GPL-3.0; built from this repo's runtime/ + build_horizon.sh)
    LICENSE-RUNTIME.md     runtime license and source pointer
    *.seg, wol-romfs.section   ← YOU must add these from your own game copy (not distributed)
```

## What is in the repository and what is not

**Included:** the launcher, the runtime binary and its license. The runtime is built from the
GPL-3.0 recovered baseline plus [`runtime/wol-adapter.patch`](../runtime/wol-adapter.patch); the
published source reproduces it (`../evidence/source-parity/`).

**Not included, and must never be uploaded:** the NSO segments, the RomFS section, the NPDM, saves,
textures, shaders or anything else extracted from the game. They are the owner's own data.

## Install on a handheld (TSPS / SpruceOS)

1. Copy the folder `port/` to the device, then place the game files inside `wol-switch/`:

   - `rtld.text.seg`, `rtld.rodata.seg`, `rtld.data.seg`
   - `main.text.seg`, `main.rodata.seg`, `main.data.seg` (main.text.seg must be 20,762,904 bytes)
   - `subsdk0.text.seg`, `subsdk0.rodata.seg`, `subsdk0.data.seg`
   - `sdk.text.seg`, `sdk.rodata.seg`, `sdk.data.seg`
   - `wol-romfs.section` (the extracted RomFS section, 217,743,360 bytes for the accepted build)

   The launcher refuses to start and names every missing file, so a wrong/partial copy is obvious
   instead of a black screen.

2. Put `port/West of Loathing.sh` next to the other port launchers (for TSPS:
   `/mnt/SDCARD/Roms/PORTS/`) and the `wol-switch/` directory where that launcher expects it
   (`/mnt/SDCARD/Roms/PORTS/wol-switch/`, or `/…/ports/wol-switch/` under PortMaster).

3. Launch from the menu. The launcher writes `logs/latest.log` and `logs/exit-status.txt` inside
   the game directory and restores the CPU online mask on exit.

## What you get

- 720 UpRender size-only profile by default (`WOL_UPRENDER_720=1`): measured **+9.04 / +9.99 / +6.19
  presents/s** in paired moving-world A/B runs, P95 improved 9.9–13.8 ms, process SwapPSS 35.6–45.2 MiB
  lower. Owner-accepted in real battle/cave play (32.1/31.7 fps vs 28.3/28.1 on the old profile).
- Quiet release profile: no per-frame trace, no dumps beside the game, `~1.5 KB/frame` log volume removed.
- Saves live in `save-laboratory/` beside the game, not in the runtime's memory.

## Known limits (honest list)

- Strict performance certification is **not** claimed: moving P95 is 34.4–37.9 ms (goal ≤33.33) and one
  arm measured 29.02 presents/s. It is an accepted *experimental* profile, not a 30 fps guarantee.
- A town-building interior and a full SAVE→QUIT→cold-launch→LOAD cycle were not captured; a cave
  interior and battle were. See [`../evidence/release-720/README.md`](../evidence/release-720/README.md).
- One rare fail-closed `NVN_COMMAND_RECORD_SIZE` stop was observed once in 18 runs and did not
  reproduce. The guard is intentional: it refuses to execute a command record whose size prefix is
  zero rather than guess.
- Zero-swap is **not** achieved and not claimed; the port runs with swap enabled.

## Controls

D-pad and left stick move, A confirms, B cancels, X/Y as in-game prompts, L/R for the in-game
action/target menus, ZL opens the guide map, START pauses. The mapping baked into the launcher is the
TRIMUI Player1 gamepad (`0300a3845e0400008e02000014010000`); adjust `SDL_GAMECONTROLLERCONFIG` for a
different device.

## Rebuilding the runtime

```sh
bash build_horizon.sh /path/to/recovered-baseline /path/to/owner-image /path/to/new-output
```

The recipe verifies the 435-file manifest, applies `runtime/wol-adapter.patch` and cross-compiles.
Exact bytes depend on the toolchain; per roadmap §18.2 a rebuilt binary must re-run the acceptance
basis instead of borrowing the deployed hash's results.
