# H-D1 — DrawArrays-only CPU/wall stage ledger: implemented, blocked at device identity

Date: 2026-10-30. Build under test: `wol-horizon` ELF `5786a3629f0210318d42e24a38f0703971e2019d0e7406cb87850a6e9ecf3c11`
(w9 source tree + the ledger). **No performance numbers were produced: the rebuilt ELF never reached gameplay.**

## What was implemented (roadmap 25.4)

- `native/wol_da_split.h` — default-OFF ledger, CPU (`CLOCK_THREAD_CPUTIME_ID`) + wall
  (`CLOCK_MONOTONIC`), 11 slots: the ten existing `NPS_*` sub-spans plus the enclosing draw span.
  Per-span start marks keep the spans exactly as non-overlapping as they already were.
  `wol_da_residual_cpu()` reports the CPU the bracketed stages do not explain, so the ledger
  cannot silently imply that the stages sum to the whole draw.
- `native/nvn_queue.h` — `nvn_sub_begin` gained the span index; the ledger is driven from the same
  boundaries the wall profiler already used (no second profiler, no new boundary).
- `native/nvn_render.h` — the ledger is armed only around `NI_nvnCommandBufferDrawArrays` records;
  all `DrawElements` paths stay outside it.
- `native/nvn_present.h` — one aggregated line per completed window:
  `WOL_DA_CPU_SPLIT frame=.. span=.. draws=.. wall=.. cpu=.. residual-cpu=.. stages-cpu=a1=.. .. submit=..`.
- `tools/test_wol_da_split.py` — host test (green): default-OFF records nothing, two spans plus a
  50 ns residual accumulate exactly, stray marks while closed are ignored, reset clears all buckets.

The three `.patch` files here are diffs against the `w9` build source, because the repository overlay
could not be used (see below). They are evidence, not an applied change.

## Blocker: any rebuild fails the segment identity check

`5786a362...` exits 0.256 s after `START` with:

```
segment size mismatch rtld.text.seg
WOL_WATCHDOG_EXIT reason=runtime-exit rc=1 elapsed=0.256
```

The check is `t2_image_file_map()` in `native/t2_image_file_map.h:43`
(`st.st_size != s->file_size`, then `exit(1)`). It fires for the same device files that the installed
`f5c6f6f2...` maps without complaint — verified in the same minute: a 30 s control run of `f5c6f6f2`
on the same probe directory passes segment mapping and reaches the video readback path.

Two independent rebuilds reproduce it:

| Build | Source | ELF | Result |
|---|---|---|---|
| `wol-horizon-build-hd1` | neutralized `upstream-source` + committed overlay | `9a64faed...` | mismatch, exit 1 |
| `/tmp/hd1src` (`hd1b`) | `build-up24-w9/source` + ledger | `5786a362...` | mismatch, exit 1 |

`T2_IMAGE_FILE_MAP=0` was passed through `E1C_EXTRA_ENV` in one attempt and the mismatch persisted,
so either the flag does not reach the runtime through `update-launcher.sh` or the failing check is not
the file-map path it appears to be. That is the first thing to settle next session.

Consequence: the H-D1 acceptance criteria (three matched fresh-boot arms, ≥3 windows, ≤5% overhead,
KMS proof, ±5% reconciliation against `WOL_OP_V3`) are **NOT MET**. No stage attribution exists yet.

## Device state

Restored to `f5c6f6f2` (sha verified), `device-manifest.json` and the `files[]` entry restored to the
same hash and byte count, MainUI up, no port processes left. The `hd1-a` boot receipt shows
`CmaFree=130412 kB`, so the failed arms never consumed CMA.

## Independent static audit of staged ledger (2026-10-30; no new device run)

**Additional source-level H-D1 ledger bug (2026-10-30 full audit):** [`wol_da_split.h`](wol_da_split.h) uses `WOL_DA_STAGES=11` for eleven `NPS_*` stage IDs **and** assigns its final index 10 to whole-draw start clocks. The indexed `NPS_SUBMIT=10` stage overwrites these draw-start clocks, while `wol_da_residual_cpu()` excludes index 10; totals/residual would therefore be wrong **if the code reached gameplay**. Host test only covers stages 0 and 1 and may `SkipTest` absent owner-local header. Separate whole-draw timestamps from NPS arrays (or allocate a distinct 12th index), include submit in the accounted sum, add final-stage regression, make fixture portable/non-skipping. This is independent of the observed `rtld.text.seg` boot failure. [Roadmap §26.3a](../../docs/optimization-roadmap-active-native-unity-2026-10-29.md#263a-h-d1-ledger-static-correctness-defect--must-fix-before-any-h-d1-numbers).

This annotation preserves the original source, two failed boot outcomes and recorded hashes; it does not claim that this timer collision caused the rtld map failure.
