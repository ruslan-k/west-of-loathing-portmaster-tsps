# Owner battle check on the default (non-720) profile — 2026-10-19

The owner launched the port from the Spruce menu (stock `West of Loathing Switch.sh` env;
the launcher does not set `WOL_UPRENDER_720`), played from the gulch save into a battle and
reports the fight and the audio feel fine. Read-only live measurements over SSH while that
battle was on screen; frozen ELF
`b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158`.

- **Profile: the 720 UpRender profile is NOT active.** No `WOL_UPRENDER_720` in the process
  environment; zero `WOL_UPRENDER_CONFIG` lines in `logs/latest.log`. This session ran the
  default (1080-class scene settings) profile; the KMS scanout is 1280x720.
- **Live fps** (deltas of the per-frame `NVN_PRESENT_UNMEASURED` lines over two 15 s
  windows, battle on screen): 424 counts / 15 s = **28.3 fps**; 422 / 15 s = **28.1 fps**.
- **Swap** (two read-only snapshots ~6 min apart, battle open the whole time): process
  `VmSwap` 499,180 → 594,168 kB (`SwapPss` 566,800 → 593,452 kB) — 488 → 580 MiB — still
  growing while play continues; system swap used 631 → 708 MiB of 1.97 GiB; `MemAvailable`
  52.7 → 73.3 MiB; `Pss` 437,763 → 404,409 kB; `VmRSS` 726,664 → 715,240 kB.
- **GPU (Mali ctx `4437_119` `mem_allocs`)**: committed ~322 MiB (311.4 Native + 10.5
  Imported UMM), unswappable.
- **Audio**: ALSA PCM-out `RUNNING` (SDL thread owner 4481) — stream live at check time;
  audio quality is the owner's observation.
- **Frame**: `kmsgrab` FB id 163 (1280x720) — battle vs Wimpy Fricker, `Melee Attack`
  7–8, 1 Action Point, target HP 12/20, full HUD, no visible artifacts —
  `battle-live.png` (sha256 `9a0ca6b7c65d6a6c402835e5c9b5ecb55b0e27fbdb88c1e4c770d6f5bc99793f`).

Scope note: this validates the **default** profile in a battle (owner sighting). It does
NOT cover the 720 UpRender profile in battle (requires a run with `WOL_UPRENDER_720=1`),
nor the sparse TransferMemory flag in battle/save-load.

Follow-up (2026-10-19, after this record): the stock launcher was repointed to the **720
candidate** for the owner acceptance run — added `export WOL_UPRENDER_720="${WOL_UPRENDER_720:-1}"`
(line 87; backup `West of Loathing Switch.sh.bak-720prep-20261019`; launcher sha256
`272a499c4ef874fb5e9d2c46aa74e5541234ccd5800ab0a3dfb643eeb1e283de`, backup sha256
`fa30af838b22e01b7a5eeeb7c4f34c4b5eaf3f67c7a984eee0ba87ba90581f3a`). The measurements
above remain the default-profile baseline.
