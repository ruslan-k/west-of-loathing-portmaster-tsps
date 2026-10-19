# 720p acceptance — results (§16.3, first full alternating series)

## Frozen protocol (as executed)

- One frozen ARM64 ELF `b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158`
  (source/overlay identity in `../allocator-history/overlay-verification.json`; the added SDK
  allocation hooks are inactive under `WOL_ALLOC_TRACE=0`), section
  `49bd16718ed0dc46f16599255791c7603e8aa2b5f04898784a39d6cacb9d0722`, identical private gulch
  save hashes verified across all six arms by the batch runner.
- Order `accept-a1,b1,b2,a2,a3,b3` (A-B / B-A / A-B); only `WOL_UPRENDER_720` differs (0/1).
  All other experimental paths OFF; stock clocks; adaptive watchdog 5 s settled / 30 s
  transitions; heavy scans absent from timing arms. Route: 20 × 2 s movement holds, map/return,
  pause/return; each request receipt carries device-monotonic send/capture timestamps.
- Independent KMS review of the saved frames: every trial shows the real title flow, complete
  gulch gameplay with player body and HUD, the full parchment guide map (five locations with
  NEW tags), world return and the restored Spruce MainUI. The contact-sheet pass initially
  flagged `accept-b1/map`; its full-size frame is a complete, legible map — a thumbnail artifact,
  not a scene defect. No black/partial/wrong-scene frames in any arm.
- All six trials: `failure=null`, `cleanup_verified=true`, zero cleanup warnings, saves restored,
  163–164 present-progress checks each, 28 labelled captures per trial.

## Measured results (runtime presents; NOT independent panel FPS)

Hold-moving = the actual 2 s input-hold windows (capture time excluded); stage-moving includes captures.

| Trial | Variant | Idle fps / p95 ms | Hold-moving fps / p95 ms | Stage-moving fps | SwapPSS idle MiB | Stalls >1 s |
| --- | --- | --- | --- | --- | --- | --- |
| accept-a1 | 1080 | 23.52 / 46.1 | 22.53 / 48.1 | 22.89 | 470.3 | 1 |
| accept-b1 | 720 | 33.50 / 32.4 | 31.57 / 34.4 | 31.84 | 430.7 | 0 |
| accept-b2 | 720 | 26.96 / 36.0 | 32.97 / 35.7 | 34.18 | 436.5 | 2 |
| accept-a2 | 1080 | 23.93 / 45.3 | 22.97 / 47.4 | 23.28 | 472.1 | 0 |
| accept-a3 | 1080 | 24.02 / 44.9 | 22.83 / 47.8 | 22.95 | 476.1 | 0 |
| accept-b3 | 720 | 31.64 / 34.2 | 29.02 / 37.9 | 29.41 | 430.9 | 1 |

Walk captures are classified per window against the trial's own map/world references
(numpy luma diff + darkness + static check): 117/120 windows are clean world movement. The
exceptions are all in `accept-b2` — it crossed a scripted transition mid-route (fade to black
at `walk-l02`/`walk-r03`, then the Boring Springs guide auto-opened and stayed open while
dpad holds only moved the map cursor: `map` ×2, `static-nonworld` ×12, `ambiguous` ×1) — plus
one ambiguous `accept-a3/walk-r05` window. `moving_hold` excludes those; `moving_hold_all`
(raw pool) is kept in `summary.json` (b2 raw: 34.19 fps). This is a real game-scripted state
change, not a defect, but it means b2's raw moving number was inflated.

Pairs (720 − 1080, both orders; clean-window moving):

| Pair | Order | Δ hold-moving fps | Δ p95 ms | Δ idle fps | Δ SwapPSS idle |
| --- | --- | --- | --- | --- | --- |
| a1/b1 | 1080→720 | **+9.04** | −13.8 | +9.98 | −39.7 MiB |
| b2/a2 | 720→1080 | **+9.99** | −11.7 | +3.03 | −35.6 MiB |
| a3/b3 | 1080→720 | **+6.19** | −9.9 | +7.62 | −45.2 MiB |

## Stalls (§16.4 evidence)

Four >1 s gaps, all coincident with major-fault bursts and MemAvailable minima of
54.7–85.4 MiB — memory-pressure page-in, not scene-specific:

- `accept-a1` hold `walk-r01` +1.21 s, gap 0.62 s, majflt≈529, MemAvail min 85.4 MiB
- `accept-b2` idle +15.91 s, gap 2.74 s, majflt≈920, MemAvail min 54.7 MiB
- `accept-b2` idle +20.86 s, gap 1.29 s, majflt≈857
- `accept-b3` hold `walk-r01` +1.05 s, gap 0.58 s, majflt≈513, MemAvail min 74.1 MiB

No trial hit a watchdog abort; no true deadlock observed in this series. The historical
`upowner-a2` frame-1481 freeze is not reproduced here; this series alone does not rule it out.

## Verdict

- The 720 UpRender size change is **repeatable** in this scene family: all three pairs gain
  +6.2…+10.0 fps clean-window hold-moving with p95 −9.9…−13.8 ms and SwapPSS 35–45 MiB lower.
- The §16.3 promotion gate is **NOT met**: moving p95 is 34.4–37.9 ms (limit 33.33) in all three
  720 arms, and `accept-b3` hold-moving is 29.02 fps (<30). Idle fps also varies (27.0–33.5).
- Stalls correlate with memory-pressure page-ins; this motivates the §16.5 sparse-copy pairs
  (reduced swap pressure is a plausible stability lever) and the §16.4 stop/go on stalls.
- **Defaults unchanged; nothing promoted.** Interior, combat, dialogue, save/load, endurance,
  physical controls/audio and no-swap acceptance remain untested here.

Artifacts: per-trial directories (receipt, effective env, ledger, compressed log, 28 KMS
captures, input receipts), `batch.json`, `summary.json` (schema 2; analyzer
`tools/wol_accept_720_report.py`), host logs.
