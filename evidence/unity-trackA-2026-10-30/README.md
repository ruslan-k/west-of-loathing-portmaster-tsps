# TRACK A — installed Unity port, measured through the principal flow (2026-10-30)

Host: accepted `ua_host` (`2408581859254d93d7a0f2eca9828a63dfe21af63593f7013c3d3aeb20a21b50`).
Launcher `/mnt/SDCARD/Roms/PORTS/West of Loathing.sh`, run id `trackA3`, 90 s bounded run, `UA_FPS=1`,
sound on (default legacy FMOD → SDL alsa), device freshly booted (`CmaFree` 130,412 kB).

**Launch method matters.** This run used the Spruce principal handoff — `/tmp/cmd_to_run.sh` written in
the Emu/PORTS form, then `TERM` on the exact MainUI PID, so `principal.sh` runs `standard_launch.sh`
with the menu already gone. Verified during the run: `MainUI=0`, `ua_host=1`.

## Result

```
[fps] 41.4 fps, frame 24.1 avg / 24.5 p99 / 24.5 worst ms, late 0 hitch 0, gc 0 heap 192 MB (42 frames, 3243 total, 87 s) rss 636 MB
[fps] 41.4 fps, frame 24.2 avg / 26.5 p99 / 26.5 worst ms, late 1 hitch 0, gc 0 heap 192 MB (42 frames, 3285 total, 88 s) rss 636 MB
[fps] 41.6 fps, frame 24.0 avg / 25.1 p99 / 25.1 worst ms, late 1 hitch 0, gc 0 heap 192 MB (42 frames, 3327 total, 89 s) rss 636 MB
[audio] legacy FMOD: frames=2047232 nonzero-blocks=6932 queued=3072
[audio] legacy FMOD closed: frames=2141440 nonzero-blocks=7300
WOL_SAMPLE {"seconds": 85.42, "MemAvailable": 172556, "CmaFree": 164, "SwapFree": 2037212, "VmRSS": "649224 kB", "VmSwap": "0 kB"}
```

- **41.4–41.6 fps**, 24.0–24.2 ms average frame, p99 24.5–26.5 ms, no hitches.
- Audio live and clean: FMOD frame counter advances throughout, close line present.
- Memory: VmRSS 636 → 649 MB, **VmSwap 0 kB**, `MemAvailable` ~172 MB, `CmaFree` ~164 kB during play;
  MainUI returned by itself and `CmaFree` recovered to 128,428 kB.

## Correction: an earlier 47 fps reading was contaminated

Run `trackA1` (same launcher, started from an SSH shell with MainUI killed by hand) reported
47.2–47.7 fps / 21.0–21.2 ms. The owner observed that MainUI was still contending for the display in
that run, and a repeat (`trackA2`, 41–42.5 fps) plus this principal-flow run (41.4) confirm it: the
higher number was an artefact of the launch path, not a better frame. Only the principal-flow number
should be quoted.

## What is and is not covered

Covered: cold start via the menu path, title/menu rendering, 90 s sustained, individual-frame
statistics from the host's own clock (avg/p99/worst), live audio, RSS/swap/CMA, clean shutdown and
automatic return to MainUI.

Not covered — needs a controller in hand or an input harness for `ua_host`: moving gameplay, save/load,
DLC entry, 45-minute endurance.

## Consequence for the Horizon branch

Horizon measures 40.2–40.6 ms per frame (**~24.7 fps**) with no equivalent audio path. The installed
Unity port measures **24.1 ms (41.4 fps)** with working sound and zero swap under the sanctioned
launch. Per roadmap §27 the "Unity already satisfies the target" branch applies: further Horizon
optimisation of this game is not justified, and the `zero_texture_refresh` stop-loss question does not
need to be answered to ship.
