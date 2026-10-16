# Gulch right-walk + small up-step (route parts 1-4 and an A pair)

Owner route: reach the snake walking right, then a short up step. Runtime `0cca40eca762c984…`,
owner save `tut_gulch` restored, features off, zero GL errors, exact cleanup.

Measured: pulses 1-2 scroll the scene (18.8 %/19.9 % of pixels changed), pulses 3-4 add only
2.5-3.6 % in fixed animated areas; texture ids 321 and 323 are uploaded exactly once at frame
2802, i.e. immediately after the up-step press at frame 2797 — the up step makes the game load
new content. The A presses load nothing new and open no dialogue or battle panel (bottom third
stays 79 % one flat colour, no box outline longer than 186 px).

Fact: movement and the up-step are delivered and produce a real content load.
Hypothesis (not proven): the enemy is farther right; the walk stops at a world limit after
roughly 70 px and the encounter trigger is not "right from the spawn point".
