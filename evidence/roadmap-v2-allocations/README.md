# Roadmap v2: SDK allocation owners and the large core read

## Measured, not reclaimed

The default-off `WOL_ALLOC_TRACE=1` hook identifies five exact pinned SDK StandardAllocator instruction sites, verifies original instructions and replays their original register/stack effects. Synthetic C tests cover allocation/free/reallocation success/failure. It does not replace the allocator. The device receipt and runtime log identify the measured build and owner section.

`reconciled-summary.json` is reproducible from the compressed log with `tools/wol_roadmap_analyze.py`; the earlier `allocation-lifetimes.json` is retained for comparison.

- 93 logged SDK allocation/free/reallocation events; 43 large allocations remain tracked at the endpoint. No overflow flag was reported. Tracking starts at 1 MiB; smaller allocations, inner Unity suballocation/free lists and concurrent-trace uncertainty remain outside its complete ownership contract.
- Endpoint **requested SDK bytes**: 955,246,245. This is not physical memory or an active-working-set estimate.
- Of those, 687,517,738 bytes belong to SDK allocations observed containing an NVN pool binding; 267,728,507 bytes have no observed pool binding. Repeated pool aliases do not add new SDK bytes. An allocation ever bound to a pool is not proof that the pool is still live.
- No physical total is constructed from SDK bytes, PSS, Mali commit or CMA. The latter counters overlap.

## The 143,554,106-byte RomFS read

The output begins at `0x104781e020`, **32 bytes into** allocation `0x104781e000` of requested size **144,080,896** bytes. The read fits inside that allocation; this is not a base-pointer-only association.

Observed call-chain identity:

```
main.text.seg+0x13a4b38
main.text.seg+0x809694
main.text.seg+0x7eb450
main.text.seg+0x7e5fc0
main.text.seg+0x7e5b1c
```

The same read output address is later reused for an 11,633,735-byte RomFS read. No matched release of the containing SDK allocation is observed before the trace ends. This establishes retained arena identity and buffer reuse, **not** that all 136.9 MiB still contain live bundle data, that Unity duplicated it, or that the pages may be discarded.

## Explicit unknowns / stop condition

Reserved/requested SDK extents are known at this layer. Inner Unity active bytes, free-list bytes, last guest access to each bundle page, current per-allocation residency and safe reclaimable bytes are **unknown**. The report emits null for these fields rather than zero. No allocator-safe page release is established; `MADV_DONTNEED`, speculative free and owner-buffer replacement remain disabled.

The ≥1 MiB SDK trace is a useful boundary, not the complete allocation-owner acceptance gate from roadmap §5. Full street↔interior/battle lifetime coverage and inner Unity attribution are still open. Heavy pagemap samples are kept separate from FPS observations.

## Same-window physical pressure

The accompanying lightweight ledger contains PSS/SwapPSS, status VmSwap, major faults, global swap I/O, MemAvailable/CmaFree, clocks and exact Mali contexts inside recorded begin/end timestamp windows. The collector's own duration is reported. Startup and scene transitions approach the CMA floor; map/pause stability is not cold-boot-without-swap proof.

Reproduce:

```
python3 tools/wol_roadmap_analyze.py evidence/roadmap-v2-allocations \
  --out evidence/roadmap-v2-allocations/reconciled-summary.json
```
