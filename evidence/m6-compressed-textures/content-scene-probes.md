# M6 content-scene probes: every BC texture is created EMPTY in every scene

Date: 2026-10-16. Build astcfix1 (`e46cdd1f...`), section `a25600ce...`, device TSPS.

## What was probed

Three scenes were driven on the device with the diagnostic input channel:

- `tut_main` (start save),
- `tut_gulch` "Thousand Snakes Gulch" (save `user-after-first-battle`),
- `tut_saloonbasement` (save `user-after-goblin-attack`).

Runs: `m1m5-gulch-astc` / `m1m5-gulch-nocache` (wide cache vs control),
`m1m5-saloon` (control), `m1m5-saloon-astc` (wide cache).

## Result

- The wide ASTC cache (365 entries, 66 348 252 B, md5 `c686a6ea3707cfc6c60bd9556ecd6e50`)
  loads fine in every scene: `ASTC_CACHE_LOADED entries=365`.
- Real content is never visible at texture-creation time:
  - `tut_gulch`: 2 BC textures created; the ASTC probe sees only the empty 512x512 pattern
    (hash8 `52140e3ce635ce4a`, `means=0,0,0,255`).
  - `tut_saloonbasement`: 74 BC textures created (5x BC1 `0x41`, 69x BC3 `0x44`; sizes up to
    1024x512), 8 `CopyBufferToTexture` events, 347 textures total.
  - In every probed case the ASTC probe prints `means=0,0,0,255` - the creation-time pixels are
    EMPTY; content arrives later via `nvnCommandBufferCopyBufferToTexture`.
- Therefore HIT=0 in every content run: the create-time side-cache has nothing real to match.
  (The 16 HITs in the earlier null-cache run matched the *empty* 512x512 pattern - a mechanism
  proof, not content.)
- The compressed store itself stays clean: 0 `NVN_REPLAY_GL_ERROR`, visual parity between the
  cache and no-cache arms (w0 diff <= 9 178 px, mean 1.4; idle diff <= 6 909 px, mean 0.9).

## Conclusion for the roadmap

In WoL every BC texture is uploaded empty and filled by buffer->texture copies, so a
create-time pixel side-cache cannot capture real content and cannot reduce residency on
content scenes. M6 as designed has no measurable benefit in this game; making it useful would
require a copy-path transcode (decode + re-encode on every upload - CPU-expensive, a separate
project), or a different target (e.g. render-to-texture residency). Recommended: mark the
create-time variant as closed in the roadmap and re-check priorities.

## Artifacts

- `prof-round/mvtG/*`, `prof-round/gulch-ab/{astc.log,nocache.log,saloon.log,saloon-astc.log,*.png}`
- device saves: `backups/save-lab-before-gulch-20261016-1316.json` (tut_main),
  `backups/save-lab-gulch-keep-*.json` (gulch, restored as the current save),
  `/tmp/saloon-save.json` (saloon), backups under `save-lab/` on the host.
