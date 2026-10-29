# draws-mean is a usable scene key, so a 5 ms change is measurable

I said the method could not separate a 5 ms change from noise. That was about comparing
`elapsed-ms` across *different* scenes. Restricted to the draw list and keyed by scene weight, the
measurement is much tighter.

Three runs, every `NVN_COUNTER_PROFILE ordinal=1` window, `draws-mean` -> `wall-ms`:

```
game scene, draws 56-61:   7.78 7.94 8.02 8.05 8.15 8.15 8.16 8.20 8.21 8.25 8.33 8.36 8.47
transitional, draws 7:     8.87 9.35 9.39 9.42 9.53 9.58 9.79 11.6 12.0 12.8 15.6 16.9
loading, draws 34/40:      8.53 15.4
```

- At 56-61 draws the draw-list wall time sits in **7.8-8.5 ms, spread 0.6 ms**. That is
  reproducible across runs and builds.
- At 7 draws the same measure swings 8.9-16.9 ms: those windows straddle a transition, which is why
  they looked like "lighter scenes are faster".
- Within one run the whole frame is similarly stable (39.6-41.1 ms over eight windows, spread 1.5).

## Consequence

A 5 ms change in the draw list or the frame is **five to eight times the observed spread**, so an A/B
does not need a scripted save after all: filter windows to `draws-mean` in the same band, take the
median of at least three windows, and compare. The earlier "blocked on a deterministic scene" was
too pessimistic - `draws-mean` already is the deterministic scene key, printed in the same line as
the number being compared.
