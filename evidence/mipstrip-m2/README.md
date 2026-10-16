# M2: mip-strip repack + RomFS size fix — measured on TSPS (2026-10-15)

Owner data stays local; this note carries only numbers, hashes of shipped artifacts and log lines.

## What was built

| Stage | Payload (decompressed texture bytes) | Container |
| --- | --- | --- |
| Original bundle | 1899.7 MB | 200,367,356 B |
| Deployed baseline (mip-promotion, 1450 textures halved) | 603.2 MB | padded to 200,367,356 B |
| **M2: promotion + `--max-mip-levels 1`** | **452.3 MB** | **145,624,417 B** (no padding) |

`tools/wol_memory_repack.py` gained `--max-mip-levels N` (drop mip tails, dimensions
untouched), `--dry-run` and `--manifest` (4402 rows, all `strip`, zero skips — every
chain was exact-length, single-image, non-streamed). Independent verification
(`verify_m2.py`): 4411 textures in and out, payload 452.3 MB, **0 multi-mip textures
remaining, 0 size/length mismatches, 40/40 sampled textures byte-exact at level 0**
(promoted ones match the old level 1, the rest the old level 0).

`tools/wol_romfs_section_patch.py` replaced the bundle inside the section and shrank
the RomFS FileEntry size (0xCFA7E08) from 200,367,356 to 145,624,417, zero-filling the
old padding inside the same section extent. Section sha256 **5597af58…1d81c**; previous
section kept as `backups/wol-romfs.section.before-m2-20261015`; `payload.sha256`
updated. The runtime verifies the section by size only, so no runtime change was needed.

## M3 result: the guest takes the file size from the RomFS entry

Largest `ROMFS_READ` per session (one-shot whole-bundle read):

* OLD section: `ROMFS_READ offset=0x4630d0 size=0xbf15cfc` = **191.1 MiB** (the padded declared size);
* NEW section: `ROMFS_READ offset=0x4630d0 size=0x8ae0d61` = **138.9 MiB** (the real bundle length).

That is a 52.2 MiB smaller load read and buffer. Boot, menu and gameplay completed
with zero stops.

## Memory: menu/game profile vs the canonical checkpoint

Same launcher defaults, controlled baseline save, ~30 s windows, `/proc` sampler plus
smaps_rollup; the M2 run was cold (caches dropped).

| Metric | Checkpoint (baseline repack) | M2 | Delta |
| --- | --- | --- | --- |
| Menu PSS + SwapPSS | 1054.92 MiB | **894.09 MiB** | **−160.83** |
| Game PSS + SwapPSS | 1079.86 MiB | **926.58 MiB** | **−153.28** |
| Menu mean VmSwap | 606.01 MiB | 416.75 MiB | −189.26 |
| Game mean VmSwap | 673.90 MiB | 492.93 MiB | −180.97 |
| Menu mean RSS | 686.23 MiB | 696.19 MiB | +9.96 |
| Game mean RSS | 703.85 MiB | 673.80 MiB | −30.05 |
| Menu / game presents/s | 21.815 / 19.042 | 25.43 / 25.02 | not attributed |

Caveats: single exploratory runs per side (the checkpoint numbers are also single
runs); the M2 run dropped caches first (cold start), the checkpoint protocol did not
document one. The delta magnitude (−150…−160 MiB) matches the removed texture payload
(−150.8 MB), which is the expected mechanism, but this is not yet a replicated A/B.

GPU-side: the runtime previously uploaded the full chains (10–12 levels) to GL; with
single-mip textures GL storage drops about a quarter of the texture footprint and the
runtime's sampler-completeness path (mip filter falls back for 1-level textures) covers
the sampling contract. Quality acceptance (characters, UI, map, combat) is the user's
playtest; minified content now samples level 0 with a non-mip filter.

## Remaining budget

Target ≈700–750 MiB PSS + SwapPSS → about 145–175 MiB still to free after M2
(game 926.58). Next candidates unchanged: M4 selective mip2 for backgrounds, M6
ETC2/ASTC for static BC textures, M5 Unity heap/lifetime profiling, and the M1
consolidated benchmark harness.
