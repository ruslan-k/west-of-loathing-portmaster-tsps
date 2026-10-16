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

## What the next instrument needs (not implemented)

1. `/proc/<pid>/maps` + `smaps` collection in the phase snapshots so consecutive phases can
   be diffed VMA-by-VMA (grow / stabilise / shrink), without double counting the NVN pool
   aliases.
2. A bounded runtime trace of guest allocations ≥1 MiB with call-site identity, lifetime and
   free path (Unity allocator, IL2CPP managed, AssetBundle read staging, texture staging),
   plus the allocator's reserved/committed/active/free-list bytes.
3. Repeated scene cycles (more than one street→sheriff→street loop) once the harness route
   can be scripted safely; the current evidence covers a single cycle.

Artifacts: `phase-comparison.json` (machine-readable tables above), produced by
`tools/analyze_memory_phases.py` from the repository's existing compressed snapshots.
