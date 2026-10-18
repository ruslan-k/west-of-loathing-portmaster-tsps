# Shifted disk-backed private COW read — real test, no memory win

## Implemented experiment (default OFF)

`WOL_ROMFS_COW=1` preserves the synchronous IStorage output byte-for-byte but maps full interior output pages privately from a bounded-staging disk sidecar. Source and destination page offsets differ, so mapping the section directly is invalid. Edge pages retain their previous outside-output bytes; later guest writes COW normally. No free, MADV_DONTNEED, zero substitution or guessed Unity unload. First eligible >=64 MiB read only; full RW main-heap range, no existing stack/transfer/NVN pool overlap, no guest-zram/lazy-zero policy. Historical pool ranges are retained conservatively under a dedicated lock; later intersecting pool publication/stack alias stops rather than silently pinning stale backing. VM replacement retires region-generation caches. Every pre-commit failure falls back to pread; a failed destructive MAP_FIXED commit stops because Linux need not preserve the prior mapping.

Host fixture passes unaligned destinations across a page, different source offset, output parity, untouched edge bytes, actual private file VMA, private writes/source-file unchanged, subsequent ordinary overwrite, invalid fd/path/ranges and zero length. The **same compiled ARM64 fixture passed on the device's actual SD/VFAT filesystem** (`ROMFS_COW_OK`). Container UBSAN passed; the host UBSAN link was unavailable (missing libubsan), so it is not reported as a host sanitizer pass. At that checkpoint, 40 memory/helper tests passed. Clean overlay build/source parity 204 files for measured `romfscow2`.

Measured ARM64 ELF: `2518ae1ac8ed972148485d1a5bca11dd9d24da26780166da05ffc4af7c34319b`. Owner section `49bd16718ed0dc46f16599255791c7603e8aa2b5f04898784a39d6cacb9d0722` unchanged.

## Device result — reject as a zero-swap lever

The mapping really engaged: **144,384,000 bytes** at the existing interior guest address. But Unity rapidly writes through it: startup sample has **130,624 KiB anonymous** in that mapping and no clean-file resident pages. Menu later has about **55 MiB swapped** inside it. Gameplay has about **91 MiB resident + 36.7 MiB swapped**, still marked Anonymous by smaps. This is not a retained clean compressed-buffer saving. A file path in `/proc/maps` does NOT mean those pages stayed file-backed/clean.

Full game-idle window: **23.907 presents/s**, P50 **41.088 ms**, P95 **45.258 ms**, median process PSS **361.85 MiB**, SwapPSS **558.61 MiB**. No isolated whole-game RAM win is established; do not promote. `cow-mapping-samples.json` preserves actual VMA dirty/anon/swap series. Later map movement, map open/return and pause route completed; real KMS world and guide remain rendered. Save hashes and exact owned-process cleanup pass; reviewed restored scanout shows Spruce. Swap was never disabled.

Independent OpenCode review was attempted with available Zen/Go routes, but each returned **expired API key**; no independent approval is claimed. Synthetic/runtime tests are not a replacement for that review. The code stays diagnostic/default-off, not release accepted.

Next memory work must identify actual post-load anonymous owners/free-list semantics; do not rerun this generic read-buffer mapping expecting the arena to stay immutable.

## CI portability follow-up

The first push failed Ubuntu 24.04 GCC 13's fortified `pread` range analysis on the inner partial-read accumulator (host GCC 16 and the ARM64 GCC 10 build had passed). The helper now uses explicitly bounded single-block I/O with EINTR retry; a short block read/write is a pre-commit refusal and falls back to the ordinary read, leaving output unchanged. No warning was suppressed. The compiled fixture now also injects short block reads/writes and verifies unchanged output plus sidecar cleanup. The plain helper compiles/runs under actual Ubuntu GCC 13.3 with `_FORTIFY_SOURCE=3`; the updated ARM64 fixture passes on the real SD/VFAT filesystem (`ROMFS_COW_OK`). The full rebuilt runtime `ab89d72920e7136be4553d6c50086c484019d78da5f8ab73f1b7e822cd891c2a` passes 207-file source parity but **was not deployed**: the last game-tested `rtorigin1` ELF `5bb707bb…` remains installed, with COW default OFF. Historical measured overlays above remain immutable.
