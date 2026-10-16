# GPU texture residency and vertex-stream census (read-only)

Roadmap section 7 first pass ("report unused-for-5/15/30-second bytes and candidate
safe-to-evict static storage; this first pass must not free resources") plus the vertex
census from road-map section 10. Build `982cb51b…` with `WOL_GPU_RESIDENCY=1
WOL_VTX_CENSUS=1` (run `m1m5-resaudit2`).

## Texture residency (level-0 estimate, read-only)

| Window | live | host total MiB | static MiB | RT MiB | inactive 5 s | 15 s | 30 s | safely reconstructible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| menu (frame 1681) | 206 | 145.7 | 102.6 | 43.1 | 90.1 | 90.1 | — | 8.0–27.3 |
| game (frames 2461–2761) | 239 | 153.1 | 110.1 | 43.1 | 97.2 | 97.2 | 88.1–97.2 | 7.1 |

Interpretation: of ~153 MiB estimated host image storage in gameplay, ~97 MiB was not
sampled for 5+ s — but only **7.1 MiB is safely reconstructible** under the current rules
(the rest are unique GPU-side results without a restore path). A budgeted eviction policy
would have almost no safe budget today; the roadmap's gate ("only if there is enough
inactive reconstructible storage") is not met. The estimate is level-0 base levels only and
is not a driver-allocation inventory.

## Vertex-stream census (guest streams, sampled hashes)

Game windows: 300 calls / 1,764,000 sampled bytes per 60-frame window,
`same-bytes=1764000 diff-bytes=0 same-pct=100.0 same-frame-reuse=0 slot-overflow=0`.
Menu: no pair-path draws (calls=0).

Interpretation: in the stationary scene every sampled vertex-stream range is byte-identical
to the previous frame. This satisfies the roadmap's precondition for a generation-tracked
immutable vertex/index cache ("only if repeated unmodified guest ranges are common") for
stationary scenes; moving/battle scenes must be measured before proposing the cache.

Artifacts: `analysis.json`, `runtime.log.xz`, `receipt.json` (run `m1m5-resaudit2`).
