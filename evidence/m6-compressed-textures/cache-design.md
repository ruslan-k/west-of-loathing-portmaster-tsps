# M6 side-cache — design (first cut, 2026-10-16)

Goal (roadmap section 6): serve host GPU textures for immutable BC payloads from a local
content-hash cache of ASTC 6x6 images, keeping the guest NVN contract untouched, with an
RGBA fallback for anything dynamic. This note fixes the format and the integration points
now that the device-side upload acceptance is proven (`astc-acceptance.md`).

## Key: content hash of the RGBA8 decode

The runtime decoder (`zero_bc_decode`) produces the RGBA8 pixels; the cache is keyed by
`sha256` over exactly those bytes, plus `(width, height, block, levels)` in the entry.
Hashing *decoded* pixels (not the guest's tiled BC source) makes the key independent of
Tegra blocklinear tiling and of where the payload sits in the guest heap. The host builder
uses `UnityPy` for the decode; **first integration run must verify** that the runtime's
decoder produces byte-identical RGBA for at least one hit (log both hashes once). If a
tile/channel-order difference exists, it will show up as a systematic miss and the key
derivation gets a documented fix at that point — do not paper over it with fuzzy matching.

## Cache file (`wol-astc-cache.bin`, little endian)

```
u32  magic 'WOL6'            u32  version=1
u32  n entries
entry (64 B): sha256[32] | width u32 | height u32 | block u8 | gl_enum u32 |
              levels u8 | payload_len u32 | payload_offset u64 | reserved[6]
payloads: raw ASTC block streams (no .astc header), 16-byte blocks
```

- v1 supports **single-level** textures only (M4-stripped targets are single-level; the
  audit lists anything skipped). Multi-level needs per-level entries or a mip chain blob in
  a later version — do not half-load a texture (mixing ASTC and RGBA levels is illegal).
- `gl_enum` records 0x93B4 (ASTC 6x6) per entry so a future emitter can mix blocks.
- An entry that fails the block-math check at build time is dropped, not padded.

## Integration points (runtime; next implementation step)

1. **First upload of a BC texture.** Where the runtime currently decodes BC -> RGBA and
   uploads with `glTexImage2D`/`glTexSubImage2D`, add under `WOL_ASTC_CACHE=1`:
   decode once (needed for the hash), look the hash up in the loaded cache; on a hit and
   only for the accepted target/format set, upload the ASTC payload with
   `glCompressedTexImage2D` (level 0) instead of the RGBA pixels and mark
   `t->astc_from_cache=1`. Log `ASTC_CACHE_HIT id=... bytes=...` / `ASTC_CACHE_MISS id=...`.
2. **Fallback / invalidation.** On any later guest upload (`zero_texture_refresh`,
   writes, render-target use) for a texture served from the cache, rebuild the texture
   through the normal RGBA path (re-`glTexImage2D` full size), clear the flag, log
   `ASTC_CACHE_FALLBACK id=... reason=...`. Never mix formats within one texture object.
3. **Eligibility.** BC formats only; skip `host_scaled`/`host_half`/packaged/cubemap/
   render-target/depth; skip when a mip tail is present (v1).
4. **Explicitly out of scope now:** eviction, in-runtime encoding, guest-visible changes.
   The cache is owner-local, read-only at runtime, and removable with no trace.

## Verification plan for the first in-game run

- Device: run the standard m1m5 windows with `WOL_ASTC_CACHE=1` and a small cache built
  from 16-24 candidates; check `ASTC_CACHE_HIT` counts, compare KMS captures against the
  RGBA run (menu + street), and read `PSS+SwapPSS` plus `/sys/kernel/debug/mali0/gpu_memory`
  while textures are alive.
- Offline: re-decode the cached payloads with `astcenc -dl` and diff against the builder's
  source PNGs (expected: astcenc-error only, no structural difference).
- Roll out only if captures match and the memory signal is directionally positive; the
  acceptance remains the roadmap's step 4 (physical captures + PSS/SwapPSS + reload latency).
