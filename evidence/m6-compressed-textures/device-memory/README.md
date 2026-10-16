# M6 device memory window — physical measurement (2026-10-16)

Question: does the ASTC side-cache actually hold less GPU memory while cached textures
stay compressed? Method: two m1m5 runs of the same build (`astcfix1`, section `a25600ce`),
differing only by `WOL_ASTC_CACHE=null-cache`, sampled every 6 s with:

- `mali0/gpu_memory` — coarse per-context KiB (did not resolve the difference; kept for reference);
- `mali0/ctx/<ctx>/mem_allocs` — per-allocation VA/commit sizes of the Mali context (this
  one resolves it);
- `/proc/<pid>/smaps_rollup` Pss/SwapPss of the port process.

Sampler: `snap-gpumem.sh` (this directory; also in the spike). Raw per-sample data was
aggregated in `mem-allocs-plateau.json`.

## Result

| phase | with cache (`ctxmem-cache2`) | without cache (`ctxmem-nocache2`) |
| --- | --- | --- |
| menu plateau (before content copies) | **239.41 MiB** | **247.49 MiB** |
| game peak (after `CopyBufferToTexture` fallbacks) | 254.9 MiB | 255.0 MiB |

- While the 82 cached BC textures stay compressed, the no-cache arm holds **+8.08 MiB** of
  GPU memory. The plateaus are rock-steady in both series (4+ samples each, ±0.1 MiB), so
  this is a real difference, not a snapshot artefact.
- The end states converge (255.0 vs 254.9 MiB): on this route every cached texture later
  receives its content through `CopyBufferToTexture` and correctly falls back to RGBA, so
  the saving exists only inside the compressed window.
- The measured 8 MiB is smaller than the naive per-texture sum (82 × level-0 RGBA = 31 MiB
  vs ASTC = 3.5 MiB). Explanations consistent with the data: the driver pools/rounds
  allocations (the mid-size band shows many 0x40000/0x41000/0x42000 allocations differing
  between arms rather than clean RGBA/ASTC pairs), and some textures are likely created
  later than the plateau. The number is therefore a measured lower bound for the window,
  not the theoretical maximum.

## Reproduce

```
cd /mnt/external/Hermes/spikes/wol-switch/prof-round
# arm A: WOL_ASTC_CACHE=/mnt/UDISK/wol-astc-cache-null.bin ; arm B: no env
LAYOUT=/mnt/UDISK/m5-layout-astcfix1.json ELF=.../wol-horizon-build-astcfix1/wol-horizon MIN=55 \
  ./run-arm.sh <label> [WOL_ASTC_CACHE=...] &
./snap-gpumem.sh <label> &   # 30 samples x 6 s
```

GPU-memory reading is only meaningful while the process is alive; the last samples show
the context vanishing (and one later sample shows the restored MainUI context).
