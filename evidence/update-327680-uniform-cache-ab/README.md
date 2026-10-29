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

## Second attempt with a longer window: the band is reached, no win

150 s window, cache on, `ordinal=1`, game-scene band:

```
draws 56.5-57.5, 59.9, 60.5:  wall-ms 7.92 8.02 8.03 8.13 8.17 8.20 8.31 8.31 8.33 8.37 8.44 8.46 8.50 8.51
```

Control (cache off, same band from `stab-a1`): 7.78-8.47 ms.

Identical distributions: median ~8.3 both, spread 0.6 both. **`WOL_UNIFORM_CACHE=1` neither helps nor
hurts the draw list on this title** - consistent with the roadmap's own note that the historical
uniform win was worth ~1 ms, which is inside this spread.

Two lessons that cost real runs: a 70 s window can stay on the title (7 draws) and prove nothing,
and a 150 s window reliably reaches the 56-61 band. The band filter does work once both runs get
there.
