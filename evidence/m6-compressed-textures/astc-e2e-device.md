# M6 side-cache on the device — E2E run log (2026-10-16)

The host-side parts were in place after commit `0d86916` (builder, format, acceptance). The
runtime hook was wired and run on the device; both the defect it first hit and the fix are
closed the same day (commits below). Two structural facts from the run shape the next
iteration.

## What was built

- Runtime (`runtime/wol-adapter.patch`): `nvn_astc_cache.h` (WOL6 loader + lookup),
  create-path hook in `nvn_textures.h` (decode -> sha256 -> lookup -> `glCompressedTexImage2D`
  instead of the RGBA upload; `ASTC_CACHE_HIT/MISS/PROBE` logs), fallbacks for later guest
  uploads in `zero_texture_refresh` and the texel-flush path (`ASTC_CACHE_FALLBACK`).
  Opt-in via `WOL_ASTC_CACHE=<file>`; without the env var the runtime is unchanged.
- Host tools: `tools/wol_bcdecode_host.c` (exact replica of the runtime BC path over
  vendor/bcdec) and `tools/wol_m6_null_cache_build.py` (null-content cache).
- `session.py` (device harness) gained the `WOL_ASTC_CACHE` passthrough (backup kept).

## Run results, round 1 (build `4633e091…`, runs `m1m5-astc-8` / `m1m5-astc-10`)

- Cache loaded: 63 entries / 3.48 MB (`ASTC_CACHE_LOADED`).
- **16 real HITs** in both runs — textures 469, 471, 473, 475, 477, 479, 481, 483, 485,
  487, 489, 491, 544, 546, 548, 550 uploaded through `glCompressedTexImage2D` from the
  cache, e.g. `ASTC_CACHE_HIT id=469 bytes=118336 w=512 h=512`. No `GL_FAIL`, no
  `FALLBACK` events. The decode->hash->lookup->upload path is proven end to end against the
  real runtime and the real game process.
- **Deterministic crash afterwards**: both runs stopped in the gameplay phase with
  `STOP status=NVN_REPLAY_GL_ERROR pc=main.text.seg+0xaf2c0c detail=0x502`
  (GL_INVALID_OPERATION inside `nvnQueueSubmitCommands` replay). Absent from all earlier runs
  of this route (dtime*, m4w2, resaudit, sparse: 0 occurrences).

## Update — root cause and fix (builds `astcerr1` -> `astcfix1`)

The error boundary was replaced with one that names the operation plus a bounded 16-entry op
ring (`NVN_REPLAY_GL_ERROR_DETAIL` / `NVN_REPLAY_OP_RING`). The first such run
(`m1m5-astcerr-1`) named the culprit on the first hit:

```
NVN_REPLAY_GL_ERROR_DETAIL op=nvnCommandBufferCopyBufferToTexture idx=84 error=0x502 frame=223 draws=1568 a0=0x10502cae00 a1=0x1000999018 ... target=30
```

`a1=0x1000999018` is the destination texture object of id **469** (confirmed against its
`NVN_TEXTURE_REAL` line). Root cause: the BC branch of `CopyBufferToTexture` decodes the
staged blocks to RGBA and writes them with `glTexSubImage2D` — an operation that is illegal
on the compressed storage this texture now has. The existing fallbacks covered the refresh
and texel-flush write paths only; the copy path was not covered.

Fix: rebuild the uncompressed store (level 0) and clear the flag right before every
compressed-incompatible write, in all three pixel-write paths — the BC copy branch
(`reason=copy-buffer`), the RGBA copy branch (`reason=copy-buffer-rgba`) and the CPU-image
refresh (`reason=cpu-image`).

Results with the fix (runs `m1m5-astcfix-1` / `m1m5-astcfix-2`, same null cache):

- 16 `ASTC_CACHE_HIT` lines again (the log caps at 16), **82 `ASTC_CACHE_FALLBACK` events
  across 82 unique texture ids** — i.e. effectively all cached textures get their content
  later through a buffer copy and correctly fall back to RGBA.
- **0 `NVN_REPLAY_GL_ERROR`; both runs complete with `CLEANUP_VERIFIED`.**
- Visual check (physical screens): menu, in-game street and the restored menu are
  indistinguishable from the baseline captures (see `device-visual/`; the moving dark
  scribble on the title screen is the game's animated tumbleweed).

## Structural facts learned

1. **On the m1m5 route the BC content arrives *after* creation.** All BC textures are
   created zero-filled (create-time hashes are content-free), and every one of the 82 cached
   textures later receives its real content through `CopyBufferToTexture` (probably the
   Unity staging buffer path). The visible street is drawn from non-BC textures at the start;
   the BC content is loaded on top of it. Consequence: a create-time cache only covers the
   window between creation and the first copy — on this route it cannot produce a
   lasting physical-memory win, and the null cache remains a mechanism proof. A
   content-bearing E2E needs either a scene whose BC textures are never re-uploaded, or a
   different cache policy for copy-updated textures.
2. **The runtime-decoder canon matters.** A UnityPy-keyed cache never matches (rounding
   differs by ±1: identical means, different sha256). After switching the builder to
   `bcdecode_host` (vendor/bcdec replica), the 512x512 zero-content hash matched the
   runtime probe byte-for-byte (`52140e3ce635ce4a`).
3. Three defects found and fixed on the way: (a) the lookup treated a hash match at a
   different shape (identical zero content at 512x512 vs 256x1024) as a hard refuse —
   `return` instead of `continue`; (b) later guest uploads (texel flush) needed the
   compressed storage rebuilt before RGBA subimage writes; (c) the `CopyBufferToTexture`
   path did the same thing but had no guard at all (the 0x502 above).

## Next steps (for the next iteration)

1. Content-bearing E2E: find a scene/route where BC textures keep their content (no later
   copies), or decide the copy-aware policy (compare a copy against the cached decode before
   rebuilding — only if it pays).
2. Physical-memory comparison while textures are alive: PSS/SwapPSS against the cache-off
   arm plus `/sys/kernel/debug/mali0/gpu_memory` snapshots (debugfs node is mounted).
3. Keep the noisy extra logging (op ring) behind the existing opt-in path only; nothing in
   the default runtime behaviour changed.
