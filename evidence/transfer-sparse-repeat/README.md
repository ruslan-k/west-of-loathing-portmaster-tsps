# Sparse TransferMemory — fixtures and paired repeat (§16.5)

## Shipped-code contract (verified)

The sparse scan block is copied **verbatim** from the frozen build source `native/memory.h`
(file sha256 `68974762e5551fbc57f6753e1c9c311488bcf2283642806e35051778be96ed8b`; block sha256
`4f146003c1c920928f540a8dd067052a4f44ce69c2134b403b50ad34086c3041`), and the frozen ELF
`b60057ea…` contains the compiled `T2_TRANSFER_SPARSE_COPY index=…` path (strings check).
`tools/test_wol_memory_sparse_copy.py` re-checks the verbatim span hash and compiles/runs the
matrix (`tools/fixtures/t2_sparse_copy_fixture.c`).

Audit notes (source): the destination is a fresh private anonymous zero-fill of the same
page-aligned size (the page-alignment/size guards run **before** any mapping, so every refused
input leaves no partial destination state); the source is guest memory handed off exclusively
per the inherited contract and is protected immediately after the scan, exactly like the
original full-copy path; skipped pages read as zero by construction and the release path
(`transfer_release_locked`) always performs the full copyback. Byte order is irrelevant
(page-wise `memcmp`/`memcpy`); `Reallocate`/reuse semantics are unchanged.

## Host matrix (`small`, 1 MiB): all green

`all_zero` (copied 0, byte-equal), `sparse_mixed` (exact copied count, byte-equal, source
unchanged), `read_after_write` (skipped page reads zero, write/read-back, others still zero),
`dense` (copied = size), `double_creation` (independent destinations), `copyback` (release
memcpy reproduces the creation-time source exactly).

## On-device ARM64 run (`device`, 64 MiB, static build)

`device-fixture-run.json` / `.txt`; binary sha256
`25ed323278a6407859f1ee185300ca31e5db18fe13d13ed7569e5ee85d67210d`, linked static,
kernel `5.15.147`, device idle at run time (binary hash verified on device, removed after).
Runner: `tools/wol_sparse_device_fixture.py` (pinned cross container, no runtime change).

| Case | copied | Rss delta |
| --- | --- | --- |
| all_zero (64 MiB zero source) | 0 | **0 KiB** |
| sparse_mixed (16 nonzero pages) | 64 KiB | **64 KiB** |
| dense (64 MiB patterned) | 64 MiB | 65,536 KiB |

`read_after_write`, `double_creation` and `copyback` all pass on device. Interpretation:
**skipped zero pages stay uncommitted at kernel level** on the real device — this is the
mechanism behind the previously measured net SwapPSS reduction. Not game adoption and NOT a
license to discard live game pages.

## Paired device repeat — results (3 valid alternating pairs, complete)

Six alternating trials `sparse-a1,b1,b2,a2,a3,b3` via `tools/wol_acceptance_batch.py
--protocol sparse`: `WOL_UPRENDER_720=1` fixed (accepted trace-off profile), only
`T2_TRANSFER_SPARSE_COPY` differs; same ELF/section/save/route; `--vma-swap` adds per-VMA
Pss/SwapPss at startup/menu/game-idle/precleanup; stock clocks; adaptive watchdog unchanged.
All six trials: `failure=null`, `cleanup_verified=true`, saves restored, identity checks passed.

| Pair | Order | ΔSwapPSS startup | Δ idle | Δ precleanup | Δ transfer-VMA swap | Δ moving fps | Stalls |
| --- | --- | --- | --- | --- | --- | --- | --- |
| a1/b1 | OFF→ON | −64.2 MiB | −67.5 MiB | −56.5 MiB | −64.1 MiB (all phases) | −0.14 | 0+0 |
| b2/a2 | ON→OFF | −44.2 MiB | −57.7 MiB | −57.5 MiB | −64.0…−64.1 MiB | +0.38 | 0+0 |
| a3/b3 | OFF→ON | −64.3 MiB | −75.1 MiB | −49.9 MiB | −64.1 MiB (all phases) | +0.03 | 0+0 |

Key measured facts:

- In every ON trial the sparse printf fires exactly once:
  `T2_TRANSFER_SPARSE_COPY index=0 source=0x… bytes=67108864 copied-bytes=0 skipped-bytes=67108864`
  — the entire 64 MiB transfer is zero at creation (OFF trials: 0 lines).
- The 72.0 MiB anonymous backing (plus merged neighbor) carries 64.0–64.1 MiB of swap in
  every OFF arm at every phase; in ON arms it disappears entirely from the swap census.
- Net process SwapPSS improvement is **44–75 MiB** depending on phase and pair — NOT a fixed
  −64 MiB (other guest arenas redistribute), and always in the same direction (3/3 pairs).
- Moving hold-window fps parity within ±0.4 fps; **zero >1 s stalls across all six trials**
  (the earlier acceptance series had four pressure-related stalls — noted, small sample).
- KMS parity: world/map/pause/restored-menu frames identical between OFF and ON arms
  (only the clock differs); no black or corrupted frames.

Caveats: sequential read-only snapshots; page-accounting, not summed physical totals; one
route/scene family; runtime presents are not independent panel FPS.

## Status

- Fixtures: **done, pass** (verbatim block + host matrix + on-device ARM64 commit-avoidance).
- Paired repeat: **done** — data-correct, repeatable, no moving regression, no stalls.
- Full-route coverage for a default-on decision (§16.5.4: battle/save-load/extended cycle)
  is **not yet exercised** — the flag stays default OFF until those scenes are available.

