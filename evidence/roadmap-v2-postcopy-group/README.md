# Roadmap v2: real-content ASTC group, three alternating device pairs

**Limited positive memory result after content upload; experimental/default OFF. No zero-swap or 30-FPS claim.**

All six runs use ELF `a8f63d0313d9d0b0984d26004166b94d440443fbba33865908ec9c44e381a6d1`, the same section, basement save and effective renderer settings. The first pair is in this directory; the two repetitions are under `repeat/`. Helper hashes are pinned per receipt: later starts use the published start/press-only helper, which refuses an already-running game. Measurement warm-up and route are unchanged.

Each ASTC arm has **nine nonempty complete-image post-copy hits**, no recorded fallback, and no recorded GL error. Controls have zero post-copy hits. CPU BC bytes are retained; the cache is read-only mapped, not fully copied into anonymous memory. No synchronous encoding runs in-game.

## Requested game-idle window after real content copies

- `v2-groupab-control-1`: Mali commit 253.617 MiB; PSS 390.02 MiB; SwapPSS 521.86 MiB; 20.367 runtime presents/s; P95 55.895 ms.
- `v2-groupab-postcopy-1`: Mali commit 250.277 MiB; PSS 381.47 MiB; SwapPSS 530.45 MiB; 21.123 runtime presents/s; P95 52.159 ms.
- `v2-grouprep-control-1`: Mali commit 250.859 MiB; PSS 407.47 MiB; SwapPSS 504.87 MiB; 19.757 runtime presents/s; P95 58.731 ms.
- `v2-grouprep-control-2`: Mali commit 252.160 MiB; PSS 402.26 MiB; SwapPSS 508.81 MiB; 20.816 runtime presents/s; P95 53.479 ms.
- `v2-grouprep-postcopy-1`: Mali commit 248.359 MiB; PSS 423.68 MiB; SwapPSS 488.00 MiB; 20.697 runtime presents/s; P95 53.923 ms.
- `v2-grouprep-postcopy-2`: Mali commit 247.289 MiB; PSS 417.37 MiB; SwapPSS 493.79 MiB; 21.243 runtime presents/s; P95 51.933 ms.

## Paired GPU commit differences (ASTC minus control)

- `game-idle`: -3.340 MiB, -2.500 MiB, -4.871 MiB.
- `map`: -3.340 MiB, -0.379 MiB, -7.176 MiB.
- `map-return`: +4.785 MiB, +0.008 MiB, -7.051 MiB.
- `pause-return`: -7.246 MiB, -10.062 MiB, -10.188 MiB.

The stable post-content idle window is lower in all three pairs (2.5–4.9 MiB), unlike the single-image experiment. This is actual per-context driver commitment, not a calculated texture/cache ratio. Later transient map-return differences are inconsistent, so it is **not** a global/all-scene saving certificate. PSS and swap move in opposite directions and overlap GPU accounting: do not add a GPU delta to a synthetic process-memory total.

Observed FPS differences remain below the documented natural run variation and do not establish a speed improvement. The lightweight sampler is enabled in both arms; the 30+ presents/s / P95 ≤33.33 ms gate is unmet.

## Visual/lifecycle/recovery scope

Reviewed KMS frames show the same basement room, player, goblin and thin strokes/alpha at reviewed scale, and the same guide title/paper. Animated figures differ between captures; this is not a lossless or subpixel compression-quality certificate. No dimensions or shader defaults were reduced/changed.

All six runs restore the exact owner-save hash and pass the repaired nonblack-menu signal gate. Screenshots remain available for independent review. The smoke route covers loading the basement, movement requests, guide and menu cycles, not confirmed combat, street/interior travel, late-game or physical-button/audio acceptance. Subsequent render-target binding restores complete RGBA storage before attaching; unsupported copy/readback semantics remain fail-closed rather than silently widened.

Reproduce:

```
python3 tools/wol_roadmap_analyze.py \
  evidence/roadmap-v2-postcopy-group/v2-groupab-* \
  evidence/roadmap-v2-postcopy-group/repeat/v2-grouprep-* \
  --out evidence/roadmap-v2-postcopy-group/summary.json
```
