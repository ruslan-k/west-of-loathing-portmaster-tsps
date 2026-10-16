# M6 side-cache on the device — E2E run log (2026-10-16)

The host-side parts were in place after commit `0d86916` (builder, format, acceptance). This
round wired the runtime hook and ran it on the device. Two structural facts and one open
defect came out of it; both are important for the next iteration.

## What was built

- Runtime (`runtime/wol-adapter.patch`): `nvn_astc_cache.h` (WOL6 loader + lookup),
  create-path hook in `nvn_textures.h` (decode -> sha256 -> lookup -> `glCompressedTexImage2D`
  instead of the RGBA upload; `ASTC_CACHE_HIT/MISS/PROBE` logs), fallbacks for later guest
  uploads in `zero_texture_refresh` and the texel-flush path (`ASTC_CACHE_FALLBACK`).
  Opt-in via `WOL_ASTC_CACHE=<file>`; without the env var the runtime is unchanged.
- Host tools: `tools/wol_bcdecode_host.c` (exact replica of the runtime BC path over
  vendor/bcdec) and `tools/wol_m6_null_cache_build.py` (null-content cache).
- `session.py` (device harness) gained the `WOL_ASTC_CACHE` passthrough (backup kept).

## Run results (build `4633e091…`, runs `m1m5-astc-8` / `m1m5-astc-10`)

- Cache loaded: 63 entries / 3.48 MB (`ASTC_CACHE_LOADED`).
- **16 real HITs** in both runs — textures 469, 471, 473, 475, 477, 479, 481, 483, 485,
  487, 489, 491, 544, 546, 548, 550 uploaded through `glCompressedTexImage2D` from the
  cache, e.g. `ASTC_CACHE_HIT id=469 bytes=118336 w=512 h=512`. No `GL_FAIL`, no
  `FALLBACK` events. The decode->hash->lookup->upload path is therefore proven end to end
  against the real runtime and the real game process.
- **Deterministic crash afterwards**: both runs stop in the gameplay phase with
  `STOP status=NVN_REPLAY_GL_ERROR pc=main.text.seg+0xaf2c0c detail=0x502`
  (GL_INVALID_OPERATION inside `nvnQueueSubmitCommands` replay). This has never appeared in
  any earlier run of this route (dtime*, m4w2, resaudit, sparse: 0 occurrences). The failing
  replay operation is not yet named — next step is one line in `nvn_replay_errors.h` to print
  the op name (and a shader pair/target line) at the boundary, then bisect the 16-texture set.

Excerpts: `e2e-hits-and-stop.txt`.

## Structural facts learned

1. **The m1m5 route (menu + stationary street) contains no live BC content.** All 83 BC
   textures the game creates there are created with zero content and never receive a guest
   flush (flush ∩ BC = ∅); the visible scene is drawn from non-BC textures. A
   content-bearing E2E needs another scene (e.g. an interior), or the menu/street route must
   be extended. This is why the null-content cache was used as the mechanism proof.
2. **The runtime-decoder canon matters.** A UnityPy-keyed cache never matches (rounding
   differs by ±1: identical means, different sha256). After switching the builder to
   `bcdecode_host` (vendor/bcdec replica), the 512x512 zero-content hash matched the
   runtime probe byte-for-byte (`52140e3ce635ce4a`).
3. Two defects found and fixed on the way: (a) the lookup treated a hash match at a
   different shape (identical zero content at 512x512 vs 256x1024) as a hard refuse —
   `return` instead of `continue`; (b) later guest uploads (texel flush) needed the
   compressed storage to be rebuilt before RGBA subimage writes (`ASTC_CACHE_FALLBACK`).

## Next steps (for the next iteration)

1. Name the failing replay operation (`nvn_replay_error_boundary` should print
   `nvn_functions[r.op].name` and the current target/program), then find which of the 16
   cached textures triggers it and add the matching guard (likely an operation that is
   illegal on compressed storage: candidate classes — copy paths, mip/mask helpers,
   palette-page setup).
2. Once clean: compare captures + PSS/SwapPSS against `m1m5-astcctl-1` (same build, cache
   off) and `/sys/kernel/debug/mali0/gpu_memory` while textures are alive.
3. Rebuild the cache from real content of a scene that actually loads BC (see fact 1).
