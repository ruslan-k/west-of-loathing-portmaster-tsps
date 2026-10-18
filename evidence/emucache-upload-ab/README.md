# Exact own-image upload skip — implemented, measured, NOT promoted

## Candidate and safety boundary

Build `wol-horizon-build-uploadskip1`, ARM64 ELF **87948d2c38efe0471049bb278705d9d3cd2f0904415a29fdf9c6dc28a58f4537**, 1,960,992 bytes; clean overlay/source parity **202 native files**. Owner section remains the corrected-map section `49bd16718ed0dc46f16599255791c7603e8aa2b5f04898784a39d6cacb9d0722`.

`WOL_UPLOAD_SKIP=1` is **default OFF**. The experiment keeps the original CPU row copy and compares the destination's full canonical raw RGBA8 bytes against its own last successfully uploaded image, never the rendered producer. One snapshot, capped at 4 MiB, no hash-only equality. Identity includes object/id, pool/address/size, GL name and current context. Unsupported representations, previous RT/draw use, aliases through shared storage, compressed/packed/scaled/multi-mip/multisample and externally named resources are refused. Render-target binds, buffer uploads, texel writes, CPU-image invalidation, downsample and region-blit writers invalidate overlapping cached storage. The existing texture bind and GL-error boundary remain on a skip. Failed/uncommitted uploads cannot establish valid host content.

Compiled helper tests exercise first upload, failed commit, changed bytes, exact repeats, overlap/adjacency, GL-name alias, context and object-id reuse. This is not full lifecycle/physical gameplay acceptance. Additional writer/context coverage remains a review gate before production use.

## Two alternating same-binary pairs (A=off, B=on)

Same save/section/launcher and ordinary clocks, periodic video proof unchanged. All four receipts verify restored original save hashes and real Spruce recovery.

Stable `game-idle` windows (runtime presents/s, P50/P95 ms):
- A1: **23.491; 41.956 / 45.910**
- B1: **23.363; 42.179 / 46.441**
- A2: **23.460; 41.815 / 46.194**
- B2: **23.629; 41.870 / 45.498**

**No repeatable full-frame improvement. Do not promote.** B1's last periodic receipt has 3,478 skipped uploads / 12,821,299,200 bytes avoided. Eliminating those uploads does not eliminate the whole-frame critical path. The snapshot itself adds up to 3.52 MiB, contrary to a standalone RAM-saving claim. No GL error is recorded by the existing analyzer.

Map/action windows are descriptive, not all matched: in B2 the two toggle outcomes are reversed relative to their requested labels. Do not use those mislabeled intervals for a map FPS claim. Full frames preserve the guide's five destinations, NEW tags, character and HUD in reviewed captures; no physical-button/audio/save-load acceptance is inferred.

Mali accounting is **unavailable**, not zero, in A1/B1 because debugfs was not mounted after reboot. It was mounted before A2/B2; their real driver context records are included. PSS/SwapPSS/GPU/CMA overlap and are never summed. Swap remains substantial; no swapoff was attempted.
