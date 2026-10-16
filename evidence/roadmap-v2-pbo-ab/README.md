# Roadmap v2: bounded unpack PBO versus ordinary and direct upload

**Decision: do not promote. Functional in the tested route, no demonstrated whole-frame win, increased GPU commitment. Default remains OFF.**

## Different mechanism and safety contract

This is a new opt-in `WOL_PBO_UPLOAD=1` path, not the rejected VBO ring, immediate GPU blit, generic lazy alias or compositor async toggle. Two fixed 3,686,400-byte unpack buffers retain the same upload pixels and GL command order. A slot is reused only after a zero-time `glClientWaitSync` reports retirement; busy slots fall back to ordinary client-memory upload. No fence wait, unsynchronized map or in-flight overwrite is introduced. Context/binding/shape/type gates refuse uncertain uses. Buffer storage is bounded to 7,372,800 requested bytes; that is not an actual-driver-memory claim.

The actual overlay C helper is compiled in synthetic tests covering default off, two busy slots, ordinary fallback, signaled reuse, pixel preservation and context mismatch. All 31 memory/overlay/hazard tests pass. A clean ARM64 build and parity of all 199 native files are archived beside this report.

## Device comparison

One exploratory three-arm round on ELF `0cca40eca762c984acb53ecd7af1f56caba8b9756041406f154a07daad74b8fc`, same owner section/gulch save, periodic readback 120 and the same lightweight sampler. ASTC and queue-drain timing are explicitly off. These are not cache-cold boots or sampler-off physical-panel FPS measurements.

- `v2-pboab-control-1`: 22.874 runtime presents/s; P50 43.120 ms; P95 46.759 ms; Mali commit 254.668 MiB; PSS 379.33 MiB; SwapPSS 531.28 MiB.
- `v2-pboab-direct-1`: 22.760 runtime presents/s; P50 43.326 ms; P95 47.759 ms; Mali commit 254.438 MiB; PSS 384.43 MiB; SwapPSS 528.34 MiB.
- `v2-pboab-pbo-1`: 23.047 runtime presents/s; P50 42.622 ms; P95 46.639 ms; Mali commit 262.895 MiB; PSS 391.46 MiB; SwapPSS 520.46 MiB.

PBO minus ordinary: **+0.173 presents/s**, well inside the documented ~1–1.5 presents/s natural variance, with **+8.227 MiB** observed Mali context commit. No repeatable speed-up is claimed from a single three-arm round. This does not justify adding staging RAM to a zero-swap project; additional repetitions are not needed to reject promotion of an unproven, memory-costly candidate. It is not a proof that every possible PBO algorithm is slower.

The last bounded PBO counter receipt reports 3072 issued uploads / 3072 attempts and 0 busy fallbacks at that receipt (not necessarily the whole-run final total). The feature really executed; it was not a disabled-flag comparison. All three runs recorded zero GL errors and no runtime STOP record.

## Visual and recovery checks

KMS review shows the same gulch/player/snake/HUD without an obvious PBO-specific regression at reviewed scale; clouds/camera animations differ. All three final frames show real Spruce Recents menus, not black transients. Exact owner-save hashes and owned PID/start-time cleanup pass, with no cleanup warnings. This is not physical-button, audio, battle or late-game acceptance.

During this three-arm comparison, no production launcher defaults, global VM knobs, swap configuration or scene assets were changed. The later clean-title correction only makes input injection opt-in; it does not enable PBO or change graphics/performance defaults. The latest diagnostic ELF remains installed with the feature off for ordinary launches. Source, exact build hashes, effective environments, ledger intervals and raw compressed logs are preserved.

Reproduce the saved analysis:

```
python3 tools/wol_roadmap_analyze.py evidence/roadmap-v2-pbo-ab/v2-pboab-* \
  --out evidence/roadmap-v2-pbo-ab/summary.json
```
