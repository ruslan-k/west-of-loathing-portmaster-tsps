# Lowered-threshold allocator census: the remaining swap is NOT in known SDK allocations

Read-only single-arm device census requested by roadmap §§15.12–15.14: lower the SDK
StandardAllocator trace threshold (≤256 KiB) and aggregate the surviving blocks by caller to
find the owners of the ~350–390 MiB guest-arena swap. No reclaim, no swap policy change, no
default promotion; with the heavier instrumentation these arms are memory evidence only.

## Method

- **Runtime (`WOL_ALLOC_MIN`, new opt-in, default 1 MiB, accepted 64 KiB..1 GiB, decimal/hex,
  fail-closed on invalid):** selects the tracked-size threshold of the existing five-site pinned
  SDK StandardAllocator trace; live table 2048 slots, 8192-event cap, overflow reported as
  `incomplete=`, never unbounded.
- **Probe:** single streaming pass over the runtime log (bounded device memory), adopts the log's
  own `threshold=` (bounded, else 4 MiB), keeps each live block's `WOL_ALLOC` caller, samples
  `/proc/<pid>/pagemap` present/swapped/file/exclusive per block at game-idle and precleanup, and
  aggregates by caller (`by_caller`, top 40; detail capped 512 blocks, sample cap 2048; truncation
  flagged).
- **Report:** `tools/wol_allocmin_report.py` → `summary.json` (size bands, totals, arena join,
  swap cross-checks).
- **Runs:** `allocmin-b1` `WOL_ALLOC_MIN=262144`, `allocmin-b2` `WOL_ALLOC_MIN=65536`. Same ELF
  `84819832afa558de4c9cbcf9fd4e73bce891906f4070cbbefaf16443807f94ea` (overlay
  `e18fd454…`, 209-file parity), same layout/save/route, every other flag OFF (no UpRender, no
  sparse copy, no COW), watchdog 25 s, 87 present-progress checks per arm, owner saves restored
  byte-equal, real Spruce screen captured after each run.

## Results

| | b1 (256 KiB) | b2 (64 KiB) |
| --- | --- | --- |
| Logged events (alloc/free/realloc) | 227 (152/65/10) | 778 (477/257/44) |
| Overflow (`incomplete=`) | 0x0 | 0x0 |
| Live tracked blocks (game-idle) | 96 | 261 |
| Requested / present / swapped (tbl.) | 929.1 / 332.5 / 83.6 MiB | 947.3 / 395.3 / 38.9 MiB |
| Process PSS / SwapPss (same sample) | 464.7 / 454.6 MiB | 509.0 / 411.6 MiB |
| Swap outside tracked blocks | **371.0 MiB** | **372.7 MiB** |
| 1524.7 MiB arena: swap / tracked-inside | 295.2 / 31.9 MiB | 290.4 / 21.9 MiB |
| Arena swap unattributed | **263.3 MiB** | **268.5 MiB** |

Caller aggregation at game-idle (requested / present / swapped MiB):

- b1: `main.text.seg+0x13a49ec` 71 blocks 761.3/185.6/71.3; `+0x13a4b38` 24 blocks 167.5/146.8/12.2;
  `+0x13a4ae0` 1 block 0.2/0.1/0.1.
- b2: `main.text.seg+0x13a49ec` 229 blocks 778.8/249.7/24.6; `+0x13a4b38` 24 blocks 167.5/144.9/14.0;
  `+0x13a4a64` 3 blocks 0.4/0.2/0.2; `+0x13a4ae0` 5 blocks 0.6/0.4/0.1.

The 64–256 KiB band adds ~164 blocks but only ~3.5 MiB of swapped bytes. Full band tables are in
each `summary.json`. Precleanup repeats the same shape (b1 outside-tracked 373.4, b2 380.1 MiB).

## Findings

1. **Both censuses are complete:** no event-cap overflow, no pagemap errors, no truncation. The
   game's direct SDK StandardAllocator traffic is genuinely small — 96 live blocks ≥256 KiB and
   261 ≥64 KiB across whole sessions; the enumerable set is closed.
2. **The remaining swap is not in any tracked SDK allocation at ≥64 KiB.** Tracked blocks carry
   38.9–83.6 MiB of a 411.6–454.6 MiB SwapPss; the outside-tracked remainder is stable across both
   thresholds, both phases and both runs (~371–380 MiB).
3. The dominant **1524.7 MiB anonymous arena** carries 290–295 MiB of swap; tracked blocks inside
   it explain only 21.9–31.9 MiB — ~263–275 MiB is **unattributed**: allocated below 64 KiB or
   served by paths this trace does not cover (e.g. Unity-internal suballocation of big segments).
4. Mid-size SDK blocks (64–256 KiB) are **resident**, not swapped: the "sum of mid-size blocks is
   the swap holder" hypothesis is rejected at this granularity.
5. The known cold **72.0 MiB TransferMemory backing copy** (64.1 MiB swap) is present in these
   control arms (sparse gate OFF) and stays a separate, already-measured lever
   ([transfer-sparse](../transfer-sparse/README.md)).

## Position

- **Closed:** "the remaining arena swap hides in known ≥64 KiB SDK allocations" — measured as
  false. No pool cap, page discard or swap change is justified by this.
- **Open:** sub-64 KiB SDK allocations vs non-SDK suballocation as owners of the arena's
  ~265 MiB unattributed swap; liveness/coldness of those pages. Both runs ended clean; nothing
  promoted or reclaimed.

## Reproduction

```
python3 tools/wol_allocmin_report.py evidence/alloc-min/allocmin-b1/receipt.json --out evidence/alloc-min/allocmin-b1/summary.json
python3 tools/wol_allocmin_report.py evidence/alloc-min/allocmin-b2/receipt.json --out evidence/alloc-min/allocmin-b2/summary.json
```

Instrument tests: `test_wol_memory_block_pages` (caller capture, threshold parse, streaming scan,
aggregation) and `test_wol_memory_alloc_hook` (compiles the regenerated overlay and verifies
`WOL_ALLOC_MIN=262144` tracks a 300000-byte request while skipping 200000), plus
`test_wol_memory_allocmin` (bands, arena join).
