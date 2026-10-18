# Where the swap lives (per-VMA census)

`--vma-swap` (read-only `smaps` parsing) was run on two same-ELF arms of the
UpRender profile at game-idle and before cleanup: `vmaswap-b1` (720) and
`vmaswap-a1` (control). Raw entries are in each receipt; `summary.json` holds
the extracted table.

## Game-idle picture

| VMA | size | Pss | SwapPss | comment |
| --- | --- | --- | --- | --- |
| guest arena (b1) | 1593.3 MiB | 244.8 | **358.0** | dominant swap holder |
| guest arena (a1) | 1524.8 MiB | 291.9 | **366.8** | same role in control |
| second guest arena | 125.0 / 193.5 MiB | 83.7 / 7.2 | 41.3 / **59.4** | control arm keeps a colder 193 MiB region |
| **72.0 MiB anon (both arms)** | 72.0 MiB | **0.0** | **64.1** | fully cold, randomized address, present in every run |
| remaining VMAs | <11 MiB each | - | - | minor |

Totals: candidate 419.4 Pss + 509.1 SwapPss; control 391.3 + 536.4 MiB.

## Findings

- **~70% of swapped pages sit inside the guest-heap arenas** (358/366.8 MiB).
  Since the >=4 MiB blocks inside them are already measured as sparse, the swap
  belongs to sub-4 MiB allocations - the next instrument is a lowered
  allocation-trace threshold (<=256 KiB) with caller aggregation.
- A **72 MiB anonymous mapping with 0 MiB resident and 64.1 MiB swapped** exists
  in every collected run at a randomized host address. Something wrote ~64 MiB
  once and never touched it again. It is not one of the port's own direct mmap
  sites (only signal stacks) and no 72 MiB constant exists in the native tree,
  so ownership is unresolved - candidates are glibc arenas, the Mali wrapper
  and guest SDK host paths.
- Releasing a proven-cold 64 MiB would remove ~12% of the measured swap; that
  is the single most concrete no-swap lead this census produced. Nothing is
  freed or discarded on this evidence.

## Phase timeline (vmaswap-b2, 720 arm)

| phase | total SwapPss | 72 MiB cold mapping |
| --- | --- | --- |
| startup (pre-CONTINUE) | 623.8 MiB | 63.9 MiB swapped, 0.2 resident |
| menu | 619.8 MiB | unchanged |
| game-idle | 556.0 MiB | unchanged |
| precleanup | 508.2 MiB | unchanged |

- The 72 MiB zero-filled mapping is present from the initial load onward and is
  never touched again; its first/last 64 bytes both read all-zero.
- **The initial load itself parks ~620 MiB in swap before gameplay starts** -
  more than the steady-state value, which then decreases as pages fault back.
- The 193.5 MiB texture-pool VMA carries 63.6 -> 45.9 MiB of swap and its head
  bytes are 0xFF-filled.
- Two runs of the 720 arm and one control arm all show the same cold 72 MiB
  mapping: deterministic content and residency, randomized address.

Next instrument: a bounded host-side mmap logger (LD_PRELOAD shim or a loader
interposer) that records size and caller for host mappings >=32 MiB while
staying read-only and default OFF - that names the owner before any release is
contemplated.

## Limits

Per-VMA Pss/SwapPss overlap for shared pages; totals are not physical sums.
Two runs per arm is not statistical acceptance; the 720 arm's slightly lower
SwapPss is a single-pair observation, not a promoted memory win. No swap,
governor or page policy was changed; both arms are the same default-OFF
diagnostic ELF.
