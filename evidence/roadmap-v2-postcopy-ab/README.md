# Roadmap v2: three alternating real-content ASTC single-texture pairs

**Result: mechanism verified; persistent physical-memory win not established. Default remains OFF.**

All six arms used ELF `2093c1a9018195ede915f0756229b8a5102997a8a77a73c481ec738e27e002d2`, the same owner section/save and effective settings except ASTC treatment variables and the non-behavioural run ID. The lightweight same-window sampler remains enabled; these are not sampler-off normal-play FPS controls.

Each post-copy arm hit real nonempty texture 469 (`sand_900`): 1,048,576 RGBA bytes → 118,336 ASTC bytes. Controls had zero hits. All arms had zero recorded GL errors; post-copy arms had no recorded fallback. This establishes a retained compressed image through this smoke route, not a complete later-scene lifetime certificate.

## Requested game-idle window (2 s warm-up excluded)

- `v2-sandab-control-1`: Mali commit median 253.555 MiB; PSS 393.10 MiB; SwapPSS 519.03 MiB; runtime presents/s 23.244; P50 42.297 ms; P95 46.897 ms.
- `v2-sandab-control-2`: Mali commit median 254.859 MiB; PSS 398.76 MiB; SwapPSS 512.09 MiB; runtime presents/s 22.847; P50 43.042 ms; P95 47.096 ms.
- `v2-sandab-control-3`: Mali commit median 262.988 MiB; PSS 404.19 MiB; SwapPSS 510.03 MiB; runtime presents/s 22.466; P50 43.645 ms; P95 49.607 ms.
- `v2-sandab-postcopy-1`: Mali commit median 254.125 MiB; PSS 394.83 MiB; SwapPSS 522.32 MiB; runtime presents/s 22.795; P50 43.079 ms; P95 47.325 ms.
- `v2-sandab-postcopy-2`: Mali commit median 253.727 MiB; PSS 396.92 MiB; SwapPSS 515.74 MiB; runtime presents/s 22.714; P50 43.366 ms; P95 47.456 ms.
- `v2-sandab-postcopy-3`: Mali commit median 254.312 MiB; PSS 380.43 MiB; SwapPSS 532.52 MiB; runtime presents/s 22.596; P50 43.545 ms; P95 48.395 ms.

Paired post-copy minus control GPU-commit differences: +0.570, -1.133, -8.676 MiB. The sign changes and the last difference exceeds this one-image size. Unrelated GPU resource churn/pooling dominates; a negative median-of-run delta alone is not a causal persistent-saving proof.

## Visual and cleanup limits

Reviewed world KMS captures show the same gulch art/player/snake, without obvious lost alpha or missing strokes at reviewed scale. Animated clouds differ naturally. Cross-launch whole-frame differences are not a compression-only diff. Map/portrait/player-body acceptance remains independent.

All six runs restored exact owner-save hashes and returned to MainUI. The first pair used an older observer that captured a black transient scanout; its two original `restored-menu.png` files are not visible-menu proof. Later arms use the repaired RGB-signal gate. The final postcopy-3 screenshot was independently reviewed as the real Spruce Recents menu.

30 presents/s and P95 ≤33.33 ms are **not** achieved in these windows. SwapPSS remains hundreds of MiB. No swap-disabled cold boot was attempted or implied.

Reproduce:

```
python3 tools/wol_roadmap_analyze.py evidence/roadmap-v2-postcopy-ab/v2-sandab-* \
  --out evidence/roadmap-v2-postcopy-ab/summary.json
```
