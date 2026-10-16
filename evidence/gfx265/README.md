# gfx265 — skinned bodies, portrait masking, map metadata and resource baseline

Date: 2026-10-15. Target: TSPS / Spruce. This is a **diagnostic development state**, not a release or a completed optimization.

## What changed

- Substituted draws now honor each enabled vertex attribute's own stream, stride and offset. The PC torso and Cactus Bill use a separate UV stream. The `f309b86a#fbd5` mesh vertex exports UV x/y with the material ST transform; `f08bad2f#c320` has a separate mesh fragment and does not receive the display composite override (`#a9b0`).
- `WOL_PAIR_STENCIL=1` replays the game's recorded stencil state on substituted draws and invalidates the cached enable state first. This restores the WANTED portrait's own mask rather than inventing a crop rectangle.
- Mip promotion can repair Sprite sampling metadata while keeping baked normalized UVs, vertex and index bytes unchanged. UGUI logical pixel rect/border/offset/PPU track the new pixel scale together; world-sprite geometry stays unchanged. The original PC atlas is selectively preserved.
- Runtime-assigned map Image sprites were absent from the serialized `m_Sprite` reference scan. Add a narrow map-family classifier, not a blanket world-map rule.
- Launcher defaults match the repaired owner bundle (`TOP_UV=raw`, `TOP_RAWID=none`, `TOP_SMART=0`, `F191_UV=none`, `F191_NOFOLDID=none`, stencil on). These defaults must not be applied to an old, unrepaired owner bundle.

## Physical screen evidence and limits

- `wanted-before.png` / `wanted-after.png`: the character's legs previously extended below the portrait window; the final capture keeps the portrait inside the frame and leaves the two-line name visible.
- `gameplay.png`: after closing the map, the PC torso and full Cactus Bill body/arms remain visible outside Alice's office. A diagnostic B packet was delivered to the same Npad path and the physical screen changed from map to scene. Earlier body-fix captures also established visible movement; this capture alone is not physical-button proof or a full-game test.
- `map-before.png` / `map-after.png`: the visible paper now occupies its intended large area instead of collapsing into a lower corner. **Map fidelity is still open:** a circle overlaps the BORING SPRINGS title and the main sheet has no resolved location markers in this save. Do not describe the entire map as fixed or infer whether marker absence is save-state or rendering without reference validation.
- `map-metadata-validation.json`: comparison with the immediately preceding repaired bundle found 23 changed Sprite objects, restricted to dynamic-map logical metadata. All Texture2D objects and baked mesh bytes stayed exact. The wider repack repairs 1712 Sprite entries, promotes 1449 textures and retains the PC atlas.
- `restored-menu.png`: the test was stopped by exact runtime identity. A fresh non-multiplexed SSH read found MainUI PID 6966, no `wol-horizon`, CPU online mask `4-7`, and no pending handoff. The actual frame shows Spruce's PORTS list.

## Build, checks and hashes

- `checks.txt`: 22 existing unittest tests pass; all six focused scripts (Sprite metadata, vertex streams, mesh UV, stencil, indexed geometry and color contract) pass; launcher shell syntax and whitespace checks pass.
- `runtime/wol-adapter.patch` was independently regenerated in memory against the recovered source baseline and matches the current source exactly. The actual ARM64 build artifact exists and its SHA matches the on-device runtime. Source-tree validation alone is not presented as a build.
- `deployment.json` records full runtime, owner-section, launcher and overlay SHA-256. On-device `payload.sha256` verification passed. Pre-change runtime/section/launcher backups remain local to the owner.
- The section is **owner data**, not in this repository. Reproduce the tested core bundle locally with:

```sh
python3 tools/wol_memory_repack.py /path/to/original/StreamingAssets/core /path/to/new-output \
  --repair-sprites --keep-texture-id 3690507347886531380
```

This command creates an owner-only bundle. It does not itself install it or verify section offsets. Use the local verified section-assembly/deployment procedure, retain a baseline, update the payload manifest and read back the installed SHA. Never repack an already-repacked input.

## Resource baseline, not an improvement claim

See [resource-summary.json](resource-summary.json), [resource-baseline.json](resource-baseline.json) and [the optimization follow-up](../../docs/resource-optimization.md). The read-only sampler is included as `resource-sampler.py`; its invocation was:

```sh
python3 /mnt/UDISK/wol-resource-sample.py 5482 30 /mnt/UDISK/wol-resource-baseline.json
```

The process PID is an example receipt, not a reusable PID. The sampler verifies its start-time identity, reads `/proc` and clock snapshots, and changes no game, VM, affinity or frequency settings. It writes only its output JSON and the exact log interval beside that output. It samples an already-running process; it never launches/stops one.

One stationary gameplay window: 30.183 s, 356 slow-frame records, approximately 11.79 presents/s; median period 84.55 ms. CPU 156.88% (100% = one core). Process `/proc/status` RSS 649.3–659.3 MiB; swap 739.7–743.9 MiB. `smaps` and status RSS differ on this kernel and are not interchangeable. Readback mean 16.50 ms/frame; log growth 346.33 KiB/s; major faults 1.16/s. System swap-in 15.90 KiB/s and swap-out 59.24 KiB/s. No power/energy measurement was taken.

The logs are stored compressed (`runtime.log.xz`, `wanted-stencil.log.xz`, `resource-interval.log.xz`). No owner bundle, shader blob, executable or save is distributed. Historical logs and captures are separate from the final map-UI session; their filenames identify that scope.
