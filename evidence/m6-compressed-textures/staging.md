# M6 compressed host GPU textures — staging inventory (not implemented)

Roadmap section 6 / commit 4 status: **not implemented**. The main technical gate —
native ASTC upload + decode acceptance on the device — is **proven** (2026-10-16, see
[astc-acceptance.md](astc-acceptance.md)): `glCompressedTexImage2D` ASTC 6x6 (0x93B4)
uploads cleanly on Mali-G57 and decodes byte-exact against the astcenc reference. The
cache and the runtime wiring remain open.

This document records the first inventory slice collected 2026-10-16 so the next
iteration starts from measured facts.

## What is known (measured)

- Guest BC content exists and is decoded on the CPU by the runtime's own decoder
  (`zero_bc_decode`, bcdec-based): NVN formats `0x41/0x42` = BC1-class, `0x43` = BC2,
  `0x44` = BC3, `0x45–0x48` sRGB-class, `0x4d/0x4e` BC7, `0x49–0x4c` BC4/5, `0x4f/0x50` BC6H.
- Live-texture format sample (run `m1m5-cpt2`, bounded scan lines): `0x25` ×2981,
  `0x39` ×262, **`0x44` (BC3) ×226**, `0x1` ×88, `0x35` (depth) ×57, **`0x41` (BC1) ×15**,
  `0x6` ×2. BC formats are present among live textures, not only in the bundle.
- Owner ledger (serialised payloads, not resident RAM): DXT5 500,077,312 B,
  DXT1 48,283,728 B, ARGB4444 48,116,130 B, RGBA32 36,330,680 B, RGB24 700,284 B.
- Host image storage estimate (level-0, read-only census): ~153 MiB gameplay / ~146 MiB menu
  (see `evidence/gpu-texture-residency/`), of which ~110 MiB static.
- Mali-G57 driver extensions observed on the device (ES2 presentation context):
  `GL_OES_texture_compression_astc`, `GL_KHR_texture_compression_astc_ldr` (+hdr),
  `GL_OES_compressed_ETC1_RGB8_texture`, `GL_EXT_texture_rg`, sRGB variants.
  **No S3TC/DXT and no ETC2 extension is advertised**, so the only compressed-upload path for
  the GPU side-cache is ASTC (or ETC1 for alpha-less static payloads).

## Next implementation steps (roadmap section 6 as written)

1. Extend the inventory to per-texture rows: native format, sampled/static/mutable, mip
   levels, sRGB/swizzle, render-target status, guest backing bytes, measured DRAM where
   possible. Pick **one immutable BC texture** as the validated first candidate.
2. Prove `glCompressedTexImage2D` acceptance for the chosen ASTC mode on one texture and
   inspect actual driver allocations before building the cache. **Acceptance: DONE**
   (2026-10-16, [astc-acceptance.md](astc-acceptance.md) — upload clean, decode
   byte-exact on Mali-G57). Driver-allocation inspection: still open (debugfs not
   mounted as-is; fold it into the first cache-validation pass).
3. Owner-local content-hash cache outside UnityFS (BC → ASTC RGBA/RGB; keep the guest API
   contract untouched; RGBA fallback for dynamic/partially-updated/render-target assets).
4. Preserve mips, block sizes, alpha, linear/sRGB, wrapping, swizzle and invalidation on
   guest writes; keep a revertible flag and compare against the RGBA path on physical
   screenshots, PSS/SwapPSS and reload latency.

An ASTC encoder is not present on the host and must be provisioned (e.g. an `astcenc`
build in the existing cross container) before step 2 can produce real content; the
advertised driver support above is the gate check, not a proof of decode correctness.
