# M5 heap / allocation attribution — first read-only pass (roadmap section 5 / commit 2)

Status: **partial.** This pass compares the existing per-phase read-only snapshots
(`evidence/memory-profile-m1m5/run-a`: startup → menu → game → sheriff → returned, one
street→sheriff→street cycle) and answers what the aggregates can answer; the allocator-level
owner trace (allocations ≥1 MiB with call sites, lifetimes, frees) and the VMA grow/shrink
diff are **not implemented yet** and are listed below as the next instrument.

## Phase comparison (run-a, last sample per phase)

| Phase | RSS KiB | VmSwap KiB | PSS KiB | PSS_Anon KiB | MemAvailable KiB |
| --- | --- | --- | --- | --- | --- |
| startup | 711,460 | 413,644 | 486,062 | 477,716 | 50,724 |
| menu | 698,624 | 426,916 | 472,977 | 464,756 | 60,648 |
| game | 692,964 | 484,640 | 448,073 | 417,504 | 90,216 |
| sheriff | 683,896 | 485,280 | 437,654 | 419,068 | 80,288 |
| returned | 686,408 | 481,648 | 437,191 | 423,100 | 57,640 |

Reading: PSS stabilises after the initial load (486 → ~438 MiB) and stays flat through the
interior and the return; anonymous PSS drops ~60 MiB from startup to gameplay and then moves
by only ~6 MiB across the interior cycle. No growing phase is visible in these aggregates
over this single cycle — which is exactly the level of claim the raw data supports.

## The 136.9 MiB launch read (roadmap question)

`runtime-memory-excerpt.json.xz` (same run) records the largest launch read:
`ROMFS_READ offset=0x4630d0 size=0x88e763a` = **143,554,106 bytes = 136.9 MiB** — one shot.
The snapshot format has no allocation identity, so released / retained / duplicated cannot be
proven from it. Weak evidence only: if the read buffer had been fully released after loading,
the startup→game anonymous drop would have to be at least ~137 MiB; the measured drop is
~60 MiB, and the flat post-load PSS is consistent with a large retained working set that
includes such buffers. **This is not proof, and no memory is proposed for reclamation on it**
(per the roadmap: do not free it solely because initial loading completed).

## VMA diffs between phases (second pass, 2026-10-16)

Two independent runs (`m1m5-cpt2`, `m1m5-dtime5`; menu-end → game-end snapshots, which embed
`/proc/<pid>/smaps` rows of 428 mappings) agree closely (`tools/analyze_vma_diff.py`):

- **Anonymous Pss falls ~37 MiB** (457.8 → 420.9 MiB) **while file-backed Pss rises ~14 MiB**
  (14.4 → 28.6 MiB); `SwapPss` rises ~47 MiB (430.6 → 477.9 MiB): part of the anonymous set
  moves to swap when gameplay starts.
- **`libmali.so.0` grows +11 MiB Pss** (6.5 → 17.6 MiB) — driver-side allocations grow with
  gameplay and are separate from guest anon accounting.
- `main.text.seg` +2.6 MiB, `main.rodata.seg` +0.2 MiB (code/data cache), everything else is
  small or flat.
- Largest mappings in gameplay: a **guest-heap VMA at `0x1001d1c000` (= guest heap base
  `0x1000000000` + ~29 MiB), 1.66 GiB virtual, Pss ~358 MiB**; a second heap VMA at
  `0x106d8b2000` (Pss ~24.7 MiB); `libmali` ~17.3 MiB; an anonymous 0x7f74000000 region
  (Pss ~14 MiB). `guest_heap` pagemap: present 143.1k → 136.1k pages (−27 MiB), swapped
  82.6k → 94.4k pages (+46 MiB) menu → game.
- For the 136.9 MiB launch read above: no region of that size disappears between the observed
  phases; the heap VMA stays large and increasingly swapped — consistent with the buffer
  being retained (or aliased inside the heap), still **not proof**.

## What the next instrument needs (not implemented)

1. ~~maps/smaps collection~~ — already present: the phase snapshots embed 428 smaps rows per
   snapshot and `tools/analyze_vma_diff.py` diffs them; repeat over more scene cycles when the
   harness route can be scripted safely.
2. A bounded runtime trace of guest allocations ≥1 MiB with call-site identity, lifetime and
   free path (Unity allocator, IL2CPP managed, AssetBundle read staging, texture staging),
   plus the allocator's reserved/committed/active/free-list bytes.
3. Repeated scene cycles (more than one street→sheriff→street loop); the current evidence
   covers one cycle plus two independent menu→game transitions.

Artifacts: `phase-comparison.json` (machine-readable tables above), produced by
`tools/analyze_memory_phases.py` from the repository's existing compressed snapshots.
