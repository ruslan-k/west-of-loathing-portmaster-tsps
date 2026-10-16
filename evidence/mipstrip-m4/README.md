# M4: selective second-level mip promotion — measured on TSPS (2026-10-15)

Owner data stays local; this note carries numbers, hashes and log lines only.

## Selection

`tools/wol_m4_select.py` reads the M2 repack manifest and selects candidates:
DXT1/DXT5 only (16/32-bit formats are UI/font/character pixels), width and
height >= 1024 in the post-M2 bundle, token-matched block list (ui, atlas, title,
map/mainmap, font, icon, sprite, controller, poster/sign/logo, hud/menu, face,
portrait, char, cursor, button, panel, letter, fakebuilding) plus substring
blocks (poster, wanted). Result: **100 textures, 100.0 MB payload, expected save
75.0 MB** — world scenery/backgrounds (mountainsides, saloon/bar/barn
fronts, town-hall variants, ceiling/floor tiles, foreground frames), while map
backgrounds, UI atlases, the wanted posters and all 16/32-bit art stay verbatim.

`tools/wol_memory_repack.py --levels-file` applies per-texture extra promotions
on top of the width-based baseline (chain sliced from level N; sprite pixel
metadata scaled by 0.5^N; up to two levels supported).

## Bundle

| Stage | Payload | Container |
| --- | --- | --- |
| Original | 1899.7 MB | 200,367,356 B |
| M2 (deployed before) | 452.3 MB | 145,624,417 B |
| **M4** | **377.3 MB** | **143,554,106 B** |

Independent verification (`verify_m4.py`): 4411 textures, payload 377.3 MB,
0 multi-mip, 0 size/length mismatches, 80/80 sampled level-0 slices byte-exact
against the source chain at the right level (single AND double promotions).

Section `wol-romfs-m4.section` sha256 **a25600ce…23deb36**, entry size = real
bundle length; previous section kept as `backups/wol-romfs.section.before-m4-20261015`;
`payload.sha256` updated. Largest `ROMFS_READ` this run: `size=0x88e763a` = **136.9 MiB**.

## Memory: menu/game profiles (same protocol as M2, cold start, controlled save)

| Metric | Baseline | M2 | **M4** |
| --- | --- | --- | --- |
| Menu PSS + SwapPSS | 1054.92 | 894.09 | **879.86** |
| Game PSS + SwapPSS | 1079.86 | 926.58 | **910.73** |
| Menu mean VmSwap | 606.01 | 416.75 | 400.58 |
| Game mean VmSwap | 673.90 | 492.93 | 503.75 |
| Menu mean RSS | 686.23 | 696.19 | 704.17 |
| Game mean RSS | 703.85 | 673.80 | 650.38 |
| Menu / game presents/s | 21.815 / 19.042 | 25.43 / 25.02 | 26.34 / 25.56 |

M4 vs M2 measured −14.2 / −15.9 MiB in the probe scenes, while the bundle lost
75.0 MB — the probe save (Boring Springs) only loads part of the 100 touched
textures; the rest (Frisco, Potemkin, later towns) arrive in scenes not sampled
here. The full M4 payload win is expected to show across those locations.

## Caveats and remaining risk

* Single exploratory runs per side; VmSwap/RSS bounce between runs is visible in
  the table (menu vs game swap moved in opposite directions on M4).
* **Visual acceptance is the owner's playtest**: these are 1024→512 world
  textures; background art now upscales ~2.5x to the 720p screen and may look
  softer. Rollback = re-deploy `wol-romfs.section.before-m4-20261015` (M2) or
  `.before-m2-20261015` (baseline repack).
* Remaining to the ~750 MiB target: about **160 MiB** (game 910.73). Next
  candidates: M6 ETC2 side-cache for BC textures, M7 internal 1080p→720p
  targets (recon: the runtime reports display 1280x720 everywhere but
  ListDisplays advertises a 1920x1080 maximum; the guest still builds 1080p
  camera targets), M5 heap/lifetime profiling, M1 consolidated benchmark.
