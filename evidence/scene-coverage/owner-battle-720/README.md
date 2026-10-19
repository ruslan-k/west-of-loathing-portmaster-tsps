# Owner acceptance run — 720 profile battle + cave visit (2026-10-19)

After the launcher was repointed to the 720 candidate (`export WOL_UPRENDER_720="${WOL_UPRENDER_720:-1}"`,
backup `West of Loathing Switch.sh.bak-720prep-20261019`), the owner relaunched the port from the
Spruce menu, entered a cave location and opened a battle. Read-only live measurements over SSH;
frozen ELF `b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158` (same build).

**Profile verification — the 720 UpRender size-only patch was ACTIVE:**
- process env contains `WOL_UPRENDER_720=1`;
- `logs/latest.log`: exactly one `WOL_UPRENDER_CONFIG trace=0 component-settings-720=1 hooks=1
  image=exact-metadata23-main source-files-unchanged=1`;
- `WOL_BUILD_ID sha256=b60057ea…`; zero `STOP` lines.

**Metrics (battle on screen, session age ~2.4 min at measurement, frame counter 2726):**
- **Live fps**: 481 counts / 15 s = **32.1 fps**; 476 / 15 s = **31.7 fps**.
- **Process swap**: `VmSwap` 453,744 → 456,128 kB (**443.1 → 445.4 MiB** over ~2 min);
  `SwapPss` 455,720 kB (445.0 MiB).
- **System**: swap used **601.6 → 606.3 MiB** / 1.97 GiB; `MemAvailable` 50.6 → 51.3 MiB;
  `VmRSS` 729.2 → 725.4 MiB; `Pss` 489.5 MiB.
- **GPU (Mali ctx `9359_123`)**: **254.7 MiB** committed (244.1 Native + 10.5 Imported UMM).
- **Audio**: ALSA PCM-out `RUNNING` (owner 9397).
- **Frame**: `kmsgrab` (FB 160, 1280x720) — same Wimpy Fricker battle arena as the
  default-profile record (97.1 % of pixels within |Δ|≤24 grayscale; HP values differ) —
  `battle-cave-720.png`, sha256 `c737cba7b66d2e1b11bb41161b25e01d7a66a16757968cad0ea05b7e61ae6150`.

**Comparison vs the default-profile record** (same battle arena, different sessions — indicative,
not a paired A/B; the paired acceptance series remains `../accept-720/`):

| metric | default profile | 720 profile |
| --- | --- | --- |
| live fps (w1 / w2) | 28.3 / 28.1 | **32.1 / 31.7** (+3.6…+3.8, ~+13 %) |
| process VmSwap | 487.5 → 580.2 MiB (↑94.7) | **443.1 → 445.4 MiB (↑2.3)** |
| SwapPss (late) | 579.5 MiB | **445.0 MiB** |
| system swap used | 631 → 708 MiB | **602 → 606 MiB** |
| MemAvailable | 51.5 → 73.3 MiB | 50.6 → 51.3 MiB |
| Mali ctx commit | ~322.0 MiB | **254.7 MiB** |
| VmRSS | 709.6 → 698.5 MiB | 729.2 → 725.4 MiB |
| Pss | 427.5 → 394.9 MiB | 489.5 MiB |

Owner-reported context: the battle was reached after entering a cave location (owner's question
"считается как дом?" — treated as the entered-interior coverage item; the captured frame shows
the battle itself, the cave entry is not on this frame).

Coverage status vs §17.9: **battle in the 720 profile — now verified** (owner sighting + frame);
entered cave location — owner-reported; save/load + full physical-button acceptance still open;
sparse battle/save-load coverage still open.
