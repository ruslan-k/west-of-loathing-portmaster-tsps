# Gulch right ×3 + up-step + right bump + A pair

Continuation of the owner's route with one added variable: after the up-step (which loads
texture ids 321/323), press right once more to make contact.

Measured: right-3 → up-tiny changes 5.2 % of the frame (largest cluster 9 047 px at
x495 y429, plus 7 282 px at x994 y345); the bump-right press changes 4.1 % (11 729 px cluster at
x495 y364). Texture ids 321/323 load again after the up-step, reproducibly, and nothing new
loads after the bump or the A presses. No dialogue box, no battle panel, no transition.

Same stop condition as the other two routes: combat was not reproducible from the spawn point by
scripted input; the owner subsequently triggered combat themselves
([`../roadmap-v2-owner-battle/`](../roadmap-v2-owner-battle/README.md)).
