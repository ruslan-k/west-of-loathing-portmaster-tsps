# Gulch combat route attempt — movement reproduced, battle not triggered

Owner instruction: load the Thousand Snakes Gulch save and walk right until adjacent
to the enemy. Two bounded runs were executed on the ordinary runtime
(`0cca40eca762c984…`, all optimization features off), owner save restored, exact
PID/start-time cleanup, real Spruce menu verified, zero cleanup warnings, zero GL errors.

## What actually happened (measured, both input paths)

| step | d-pad right run | analog-stick right run |
| --- | --- | --- |
| 1st pulse | 18.93 % of pixels changed, 15.00 % above the visible threshold | 18.99 % / 15.05 % |
| 2nd pulse | 21.09 % / 17.01 % | 21.13 % / 16.97 % |
| 3rd pulse | 3.07 % / 0.99 % | 3.02 % / 0.90 % |
| 4th pulse | 3.75 % / 1.16 % | 1.41 % / 0.79 % |
| …later pulses | 3.15–4.29 % / ≤1.51 % | — |
| A press | 3.07 % / 1.16 % | 3.16 % / 1.04 % |

The first two pulses scroll the whole scene (`world` vs `right-7`: 132 664 pixels
changed by more than 16 levels across every row band — a camera pan). From the third
pulse on, only about 10 800 pixels above 16 levels change, and they sit in three fixed
areas: the left edge (x 0–90, y 427–528), the right edge (x 1144–1237, y 508–587) and a
~55 px wide sliver around x 505–560 (y 428–583). That is scene animation, not travel.

Independent confirmation that no new content was loaded after that point: in the second
half of the run the **only** texture uploaded to the GPU is id 460 every frame
(1 954/1 954 uploads); the battle/UI textures (283, 322, 334, 337, 358, 367) appear only
in the first half. No dialogue or battle panel appears either: the bottom third is 79 %
one flat colour in every frame with an identical 64 044-pixel uniform region at
(301,14)–(1041,153) from `right-2` through `engage`, and the whole frame stays 85–87 %
white (the game's pen-and-ink style).

## Reading, stated as fact versus hypothesis

**Fact:** both the d-pad and the analog stick produce the same two-pulse advance and then
a hard stop; no battle, dialogue or scene transition is visible in any captured frame; the
game accepted all 9 (d-pad run) and 7 (stick run) injected presses; nothing new is loaded.

**Hypothesis (not proven):** the character reaches a world/area limit or an obstruction
after roughly 70 px of travel, and the encounter trigger is not "walk right from the
spawn point". The trigger has now resisted three bounded routes (basement `left×3 +
interact×3`, gulch `right×7 + A`, gulch `stick-right×4 + A×2`), so per
`references/walk-input.md` the next step is an owner-demonstrated trigger rather than
more button guessing.

Frames for the owner: `world.png`, `right-2.png` (end of travel), `right-7.png`,
`engage.png` in this directory; the stick run's frames are in
[`../roadmap-v2-gulch-stick/`](../roadmap-v2-gulch-stick/).
