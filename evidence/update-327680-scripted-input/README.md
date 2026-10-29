# Scripted input: the hook works, the schedule does not yet

New, default-off `WOL_SCRIPT_INPUT="start_ms:hold_ms:mask,..."` in `input_host.h`. It sets
`hid_host.diagnostic_buttons` on a schedule so a run can reach a menu without a human, and prints
`WOL_SCRIPT_PRESS t=... mask=...` when it does.

Builds: `w19 a3af04d3` (schedule from the first sample), `w20 09ab0d4b` (schedule anchored at host
init). Both run, both print, neither reaches the game.

## What happened

```
script-a2  (w19): WOL_SCRIPT_PRESS t=16008 mask=0x3      draws stay 7.00
script-a3  (w19): WOL_SCRIPT_PRESS t=24000 mask=0x1      draws stay 7.00
script-a4  (w20): WOL_SCRIPT_PRESS t=19003 mask=0x1      draws stay 7.00
```

Every run applies exactly one scheduled press, and it is never the first one in the schedule. With
four entries at 8/14/19/24 s, only the 19 s entry fires.

## What that tells me

The clock the schedule is measured against is not the clock the worker runs on: `t0` is captured
either too late (w19, first sample - which happens after the game has started its own input path)
or still not early enough (w20, host init). The presses before the worker really starts are simply
past by the time it looks.

So the mechanism is sound - one press proves the path reaches the guest sample - but the timing
anchor is wrong. Fixing it needs the worker's own first iteration as t0 (not the host init), or a
frame-count trigger instead of wall time, which is the more robust of the two because the load
phase varies between runs.

Not claimed: that the menu ignores input. Every press fired before the input path was live, so
there is no evidence either way about the game's response.
