# Present-proof accounting + sparse readback validation (roadmap section 2)

Validation of the already-implemented truthful per-target draw accounting and the opt-in
sparse readback cadence. Run `m1m5-sparse1`, build `982cb51b…`,
`COTM_PRESENT_READBACK_60=1 COTM_READBACK_PERIOD=300`.

## Result (runtime log, summary in `sparse-analysis.json`)

- Present samples: 13 lines — 3 `BLACK-SAMPLE` (startup) then 10 `PIXELS`.
- **`texture-draws>0` on all 13 samples** — the accounting fix from the resource-goal
  checkpoint is effective (the earlier failure mode was `texture-draws=0 status=INCONCLUSIVE`).
- First proof at **frame 4**; after proof the spacing between samples is exactly the sparse
  period: gaps median/max/min = **300 / 300 / 296 frames** (~11.5 s at 26 fps).
- **2,895 frames are marked `NOT-SAMPLED`** — unobserved frames are not reported as healthy.

## Conclusion

Section 2 acceptance met: real pixel proof of visible output, sparse sampling verified in the
actual log after proof, honest NOT-SAMPLED state for unobserved frames. Periodic video health
retained; explicit captures unchanged. Readback cost before/after: per-frame readback drops
from every-frame sampling to one sample per period (measured readback-time savings are small
at these refresh rates and were not separately A/B'd).

Artifacts: `sparse-analysis.json`, `runtime.log.xz`, `receipt.json`.
