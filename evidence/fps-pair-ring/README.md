# FPS experiment: reusable GL buffers in the substituted-draw path ("pair ring")

Date: 2026-10-15. Runtime under test: `wol-horizon-build-pairring`
SHA256 `d3a4ce6a410868c368e88e6ca9b3fcf60c65a8d7cb401cae3ddf92c6e3582440`.
**Experimental checkpoint, not a release.** Owner section stays `a25600ce...`.

## What changed (source)

`nvn_render.h`, substituted-draw path: every draw allocated and deleted GL objects -
one interleaved vertex buffer, one per distinct vertex stream and one element buffer
for indexed draws (~2-5 `glGenBuffers`+`glDeleteBuffers` per draw). The change keeps a
6-slot rotation of persistent buffers and refills the current slot with `BufferData`
(orphan semantics: the previous storage stays alive for pending draws, the same
contract the deleted-per-draw buffers relied on). `WOL_PAIR_RING=0` restores the
per-draw gen/delete path; the mode is printed once at startup.

Unit coverage: `tools/test_wol_vertex_streams.py` compiles the real binding code and
exercises both modes plus the rotation wrap (6 distinct slots, then wrap).

## Why the substituted path was the target (measured)

- The standard vertex path is **unused** on this title: every 60-frame
  `NVN_VERTEX_STATE_PROFILE` window in a live run shows `pointer-sent=0`. The existing
  streaming-buffer opt-ins (`COTM_STREAM_VBO`, `COTM_STABLE_VBO`, `COTM_TIGHT_PACK`)
  hook that unused path.
- Device A/B of `COTM_STREAM_VBO=1` (runs in this session, see the PR comment log):
  menu 26.35 -> 26.23, game 25.44 -> 25.05 presents/s - no effect, consistent with the
  hook being unreachable.
- The title's draws are handled by the substituted ("pair") path: `game-draws` grows
  ~44 per submit in the run logs.

## Method

Same device (TSPS), same section `a25600ce`, same controlled save, same harness
(`wol_memory_benchmark.py run`, cold cache, 30 s ready menu, CONTINUE, 30 s street),
one env variable `WOL_PAIR_RING` (0/1), alternating order, three runs per arm.

## Results - presents/s (menu / game), benchmark phase JSONs

| run | arm | menu | game | note |
|---|---|---:|---:|---|
| m1m5-ringC | ring-off | 26.47 | 22.83 | window with anomalous swap thrash: 94.3 major faults/s |
| m1m5-ringC2 | ring-off | 25.35 | 25.51 | |
| m1m5-ringC3 | ring-off | 26.39 | 25.85 | |
| m1m5-ringD | ring-on | 25.87 | 26.11 | |
| m1m5-ringD2 | ring-on | 26.74 | 25.30 | |
| m1m5-ringD3 | ring-on | 26.51 | 25.88 | |
| (earlier, pre-ring runtime) | reference | 26.35 / 26.23 | 25.44 / 25.05 | runs m1m5-fpsA/B, same day |

Means/medians: ring-on menu **26.37**, game **25.76** (median 25.88); ring-off menu
**26.07**, game **24.73** (median 25.51); pre-ring reference game **25.25**.

**Conclusion: no gain beyond run-to-run variance.** The game window alone varies by
about +-1.5 presents/s at n=3; paired same-order differences are +3.28 / -0.21 / +0.03.
The per-draw GL object churn is structurally removed, but it was not a frame-time
bottleneck for this title. No regression was observed.

## Integrity and limits

- Every run restored the owner save with matching SHA256, left no `wol-horizon`
  process and produced a real Spruce menu frame (`receipt.json`, `cleanup_verified`).
- Reviewed in-game frames (run C and D captures) show the ordinary Boring Springs
  street (Alice's clinic / sheriff facade) with no new corruption.
- PSS+SwapPSS stayed within the known envelope (~903-932 MiB) in all runs.
- Limits: two 30-second windows per run in ONE scene (ready menu + starting street);
  no combat, map, later locations or long-session behaviour. The GL-object reduction
  itself is verified by construction and the unit test, not by on-device counters.
  The pre-ring reference runs were taken earlier the same day, so thermal/system
  state may differ slightly.
- `WOL_PAIR_RING=0` restores the exact previous per-draw behaviour without a rebuild.

## Files and reproduction

- `run-ring{C,C2,C3,D,D2,D3}/` - phase JSONs (`*.json.xz`), receipts, effective env,
  the raw runtime log (`runtime.log.xz`). The ring mode is visible in each log as
  `WOL_PAIR_RING mode=reuse|per-draw-gen-delete`.
- `ab-compare.py` - the table generator used for the numbers above.
- `m5-layout-pairring.json` - descriptor layout bound to this runtime's ELF SHA.

```sh
WOL_PAIR_RING=0 python3 /mnt/UDISK/wol_memory_benchmark.py run --label m1m5-ringC \
  --layout /mnt/UDISK/m5-layout-pairring.json \
  --control-save /mnt/UDISK/wol-goal-20261015/copy-off-a1-saves-before \
  --out /mnt/UDISK/wol-m1m5-ringC --seconds 30 --cold
# ...and the same with WOL_PAIR_RING=1 for the reuse arm.
```

No owner bundle, executable or save is distributed here.
