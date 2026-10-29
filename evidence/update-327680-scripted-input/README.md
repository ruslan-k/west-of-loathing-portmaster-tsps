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

## Repeating schedule: presses fire, the title does not move

`start_ms:hold_ms:mask:period_ms` (w21 `5edbf1e5`) fixes the timing half of the problem: with
periods the schedule lands no matter how the worker cadence wanders during load.

```
script-a5: 43 presses fired, mask 0x400 (START) and 0x1 pinned, draws stay 7.00
script-a6: 49 presses fired, masks 0x1 0x2 0x4 0x8 0x400 cycling, draws stay 7.00
```

So the hook works end to end as far as the HID sample: the buttons are set, the worker publishes
them, the guest sample carries them (`connected-pad-required=1`, and the TSPS pad is present).

**The title still sits at 7 draws through every mask tried.** That moves the blocker from timing to
identity: either the bit assignment for this title is none of the five tried, or the title advances
on something other than a face button (stick), or the guest's npad poll is not the path this menu
reads.

## What the next attempt needs

One real human press on the title with `COTM_INPUT_DIAGNOSTIC` logging (or the existing pad trace)
to see which bit actually moves it - two minutes of a person's time that replaces guessing five
masks. Everything after that is scripted.

## Root cause: the probe path never set the controller map

`update-launcher.sh:114` exports `SDL_GAMECONTROLLERCONFIG` (the `TRIMUI Player1` mapping:
`a:b0,b:b1,start:b7,...`). My probe harness launched the runtime directly and did not, so SDL had no
mapping, no pad was opened, `hid_read_sample` returned an empty sample, and every press - physical
or scripted - was invisible. That is why the title sat at 7 draws through five masks and a human
pressing buttons.

With the map exported, the same build reports:

```
HID_JOYSTICK_COUNT 1 pad=TRIMUI Player1
```

## Scripted entry works

```
pad-a2 (90 s):  94 presses, still 7 draws - the window ended during loading (178-373 ms/frame)
pad-a3 (260 s): 254 presses, draws-mean 71.0-72.8, frame 40.3/41.6 ms, replay 24.7/25.0
```

So the runtime reaches gameplay without a human, and the scene it lands in is a band of its own
(~71 draws, heavier than the 56-61 windows seen when the title timed out into a demo/attract
state). Presses at 20 s and later, repeating every 4 s, are enough: 90 s is simply too short.

## The method now

```json
SDL_GAMECONTROLLERCONFIG="0300a3845e0400008e02000014010000,TRIMUI Player1,a:b0,b:b1,..."
WOL_SCRIPT_INPUT="20000:250:1:4000,20200:250:2:4000,20400:250:10:4000"
WOL_PROBE_SECONDS=260
```

filter `NVN_COUNTER_PROFILE ordinal=1` to `draws-mean` 70-73 and take three windows. That is the
first honest baseline this build has had.
