# Owner battle on the device — first real combat frames and timings

The owner entered combat themselves on 2026-10-16 while an automated route was running. The
route was killed the moment they reported it (no further injected input), the game was left
running for them, and these four KMS frames plus the runtime's own frame clock were captured
from the live session before it ended.

## What this adds

- **Combat is now covered by real frames** on the port (`battle-1..4.png`), not only by the
  menu/world scenes.
- **First battle frame-time measurement** (from the runtime's `MOMO_FRAME frame= ns=` series,
  last 200 frames of the battle):

  | window | n | median | P95 | max | implied rate |
  | --- | --- | --- | --- | --- | --- |
  | last 600 frames (incl. battle) | 599 | 40.85 ms | 44.48 ms | 94.31 ms | 24.5 /s |
  | last 200 frames | 199 | 40.74 ms | 45.25 ms | 55.81 ms | 24.5 /s |
  | last 60 frames | 59 | 40.55 ms | 45.73 ms | 55.35 ms | 24.7 /s |

  One in-battle frame breakdown (`T2P_SLOW_FRAME`): period 44.4 ms, replay 27.2, finish 12.9,
  present 6.1, swap 5.8, readback 0.0.

  **The roadmap acceptance target (30+ presents/s, P95 ≤ 33.33 ms) is not met in combat** —
  this is the first measurement that says so for a battle rather than for a menu/idle scene.

- **Memory during the battle:** `MemAvailable` 89–93 MB, `CmaFree` 9.9–11.6 MB, swap in use:
  `/mnt/UDISK/swapfile` 115 MB + `/mnt/sdcard/.../cachefile` 518 of 524 MB. Zero GL errors,
  zero `TNP_SLOW_FRAME`. No OOM, no crash.

- **The battle is recorded by the game itself:** the owner save's
  `__internal_fight_counter` moved 4 → 5 across their session, alongside `secondsplayed`
  +579 s and new horse-taming flags (`tut_horse4`, `crazyhorseeyes`, `crazyhorsenose`).

## Scope

Frame timings are runtime presents from the port's own clock, not an external high-speed
camera; the frames are real KMS scanout captures of the battle. Physical-button proof is the
owner's own input, reported by them, not an instrumented measurement.
