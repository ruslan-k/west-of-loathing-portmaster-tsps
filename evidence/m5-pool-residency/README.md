# Graphics pools and the big live blocks (M5 attribution)

Read-only host analysis of the pinned owner image plus two device traces
(`memoryowners2`, `bundlehdr-b1`) identify the dominant live large allocations
reported by `WOL_ALLOC_TRACE`.

## What the code says (owner-local, hashes not code published)

At `main.text.seg+0xaf5af8` and `+0xaf6214` the engine clamps a failed pool
allocation to `min(requested, 0xC000000)` (192 MiB) when `w24 == 0x22`, or to
`min(requested, 0x4000000)` (64 MiB) otherwise, then retries. The strings
passed to the logging wrapper at those sites are **"BufferPool # %zi"** and
**"TexturePool # %zi"**. The live blocks therefore are the clamped retry sizes
of Unity's graphics buffer/texture pools.

The origin of `w24` was not resolved read-only; it must not be assumed to be a
docked/handheld switch. The clamp path itself only runs after an allocation
failure, which is why both pools end up at exactly 192 MiB.

## Dominant live blocks (deterministic across two runs)

| guest ptr | requested | identity |
| --- | --- | --- |
| `0x106058b000` | 192 MiB + 4 KiB | graphics pool (BufferPool/TexturePool family) |
| `0x1050186000` | 192 MiB + 4 KiB | sibling graphics pool |
| `0x1047752000` | 138.2 MiB | GC heap segment that hosts the launch `System.Byte[]` (recycled in place) |
| `0x106f85a000` | 96.0 MiB | unresolved graphics-family block |
| `0x105c188000` | 64.0 MiB | unresolved graphics-family block |
| `0x1078b00000` | 64.0 MiB | pre-main loader block |
| `0x106d8b3000` | 31.6 MiB | graphics-buffer structure (five sub-allocations at `+0x1a90..+0x1ab8`) |

Allocator requests are not physical residency: a 192 MiB pool can be sparse.
`host-facts.json` records the strings, offsets and caller chains; the device
run `poolres-b1` measures page-level residency (present/swapped) of every live
>=4 MiB block with `--block-pages`, and its receipt holds the raw counts.

## Why this matters for no-swap

PSS (~380-400 MiB) + SwapPSS (~530-560 MiB) already exceed the 963 MiB board.
If the two 192 MiB pools are substantially resident, capping them lower is a
real memory lever; if they are mostly sparse reservations, shrinking them would
only reduce virtual size and risk pool exhaustion. The residency measurement
decides which case is true before any patch is proposed. No reclaim, swapoff or
page discard is implied by this census.

## Measured residency (`poolres-b1`, 720 candidate, pagemap)

Same-ELF candidate run, 87 progress checks, clean save/Spruce recovery. Its FPS
window is **invalid** (a 10.7 s gap sits inside the 18.6 s window; 9.86
presents/s), so it is used only as a memory census. At game-idle:

| block | requested | present | swapped |
| --- | --- | --- | --- |
| 0x106058b000 pool | 192.0 MiB | 62.8 MiB | 1.1 MiB |
| 0x1050186000 pool | 192.0 MiB | 13.5 MiB | 0.0 MiB |
| 0x1047752000 GC segment | 138.2 MiB | 127.5 MiB | 10.2 MiB |
| 0x106f85a000 graphics | 96.0 MiB | **0.0 MiB** | 0.1 MiB |
| 0x105c188000 graphics | 64.0 MiB | 47.7 MiB | 0.4 MiB |
| 0x1078b00000 loader | 64.0 MiB | 64.0 MiB | 0.0 MiB |
| 0x106d8b3000 buffer struct | 31.6 MiB | 23.7 MiB | 0.0 MiB |
| **total (11 blocks)** | **813.9 MiB** | **362.3 MiB** | **12.7 MiB** |

**Verdicts (facts, not hopes):**

- The pools are sparse reservations: 76.3 MiB present out of 384 MiB requested,
  and one 96 MiB graphics block is completely untouched. **Capping the pools is
  closed as a no-swap lever** - it would shrink virtual size, not resident RAM,
  while risking pool exhaustion.
- Present pages of these tracked blocks (362 MiB) nearly equal steady-state PSS,
  so the ~550 MiB of swap in steady gameplay comes from allocations below the
  4 MiB trace threshold, not from these pools. The next memory instrument must
  lower the allocation-report threshold (<=256 KiB) and aggregate by caller.
- Gulch entry stalls are episodic and reach **10.7 s** while staying under a
  20 s budget; a 5 s watchdog cuts a load that may still finish. Budget guidance
  ("20-30 s near loads") is now measured, not guessed.
