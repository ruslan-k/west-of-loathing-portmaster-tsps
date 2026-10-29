# `WOL_UNIFORM_CACHE=1`: the A/B could not be run

Intended test: median draw-list wall time in the 56-61 draw band, cache on versus off.

What the run produced, `ordinal=1`:

```
draws-mean 7.00:  9.84 9.46 10.82 13.02 44.53 9.42 9.87 10.08 ms
```

Every window is at **7 draws** - the title/transition scene - and never reaches the 56-61 band the
control runs sit in. A 70 s window with the cache on did not advance to the same content, so there
is nothing to compare; the one 44.5 ms window is a hitch, not a scene.

## What this corrects

The previous note concluded a scripted save was unnecessary because `draws-mean` keys the scene.
That is true only if both runs *reach* the band. Here they did not, and the difference is not
noise - it is content. So the prerequisite stands: the same view twice means reaching it the same
way, which needs scripted input (or a save that loads straight into a room).

Not claimed: that the cache is slow, broken, or that it changed the frame. The run simply did not
show the scene.
