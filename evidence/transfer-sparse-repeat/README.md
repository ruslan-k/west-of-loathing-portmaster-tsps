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

## Paired device repeat (in progress)

Six alternating trials `sparse-a1,b1,b2,a2,a3,b3` via `tools/wol_acceptance_batch.py
--protocol sparse`: `WOL_UPRENDER_720=1` fixed (accepted trace-off profile), only
`T2_TRANSFER_SPARSE_COPY` differs; same ELF/section/save/route; `--vma-swap` adds per-VMA
Pss/SwapPss at startup/menu/game-idle/precleanup; stock clocks; adaptive watchdog unchanged.
Reports must show net SwapPSS/RSS pressure, swap faults, startup/transition latency, Mali
commit, KMS parity and hold-moving parity before any default-on consideration. Raw artifacts
land in this directory (per-trial subdirectories, batch.json, summary).

## Status

Fixtures: **done, pass** (this checkpoint). Paired repeat: **collecting**; promotion stays
blocked until it shows data-correct, repeatable net pressure savings without load-stall or
visual regressions.
