# Resource optimization — measured baseline and next isolated tests

## Scope

The current owner build reaches real menus and Boring Springs with restored skinned bodies and the WANTED portrait mask. Map layout remains partially unresolved. Keep this visual baseline unchanged while measuring resource work. This document ranks **candidates**, not shipped performance improvements.

Evidence: [gfx265](../evidence/gfx265/README.md), including raw `/proc` samples, compressed runtime interval and physical scene/cleanup captures. Date: 2026-10-15.

## What the current session actually costs

A read-only, 30.183-second sample of the stationary Boring Springs scene used the installed `c25640be…` runtime and repaired `e3073432…` section. No CPU/GPU clocks, VM parameters, affinity or asset quality were changed during the sample.

- 356 consecutive frame records, approximately **11.79 presents/s**, median period **84.55 ms**, p95 **91.2 ms**. `T2P_SLOW_FRAME` is thresholded at 40 ms; in this window every present was above it. This is a diagnostic-binary stationary-scene observation, not a gameplay benchmark or A/B.
- Mean replay wall time **53.44 ms**, including **6.12 ms** finish time. Readback **16.50 ms/frame**. These phases do not describe all remaining frame time and must not be added as independent CPU work.
- Process CPU **156.88%**, where 100% is one CPU core. The busiest guest thread spent **84.92%** on CPU 2. This is not 157% of the whole machine.
- `/proc/status`: RSS **649.3–659.3 MiB**, VmSwap **739.7–743.9 MiB**. `smaps_rollup` reports a lower RSS on this kernel; preserve both views rather than adding or substituting them. GPU allocations may overlap process accounting and must not be added blindly.
- Largest anonymous mapping: **785.39 MiB RSS+Swap**, within a larger virtual reservation. This is a committed-mapping attribution, **not** proof that every byte is currently live or immediately reclaimable.
- Major faults **1.16/s**; system swap-in **15.90 KiB/s**, swap-out **59.24 KiB/s**. Large occupied swap is not evidence of severe active thrashing in this particular warm window. Startup and scene transitions need separate samples.
- Runtime log growth **346.33 KiB/s**, about **20.29 MiB/min**. In 30 seconds, 136389 lines were emitted; most are repetitive per-draw catalogue/bank/texture/draw records even with `WOL_QUIET=1`.
- Clock snapshot: guest-affined lower cluster **1.416 GHz**, other cluster **1.992 GHz**, GPU **150 MHz**, battery 96%. A snapshot does not establish sustained utilization, a GPU bottleneck, watts or energy consumption. No battery-runtime improvement has been measured.

## 1. Remove repeated diagnostic work without touching rendering

**Observed:** `WOL_QUIET=1` suppresses texture-content probes and samples IPC, but the pair path still emits `WOL_CAT_DRAW`, `WOL_PAIR_BANK`, `WOL_PAIR_TEX`, `WOL_PAIR_DRAW` and `WOL_PAIR_DRAW_ISSUED` for every draw. The sample has roughly 23k of each in 30 seconds.

**Next isolated A/B:** gate these successful-draw trace lines with an explicit detailed-trace flag (default off), retaining one initial configuration receipt and a bounded periodic summary. Keep error detection, pointer/range validation, shader identity checks, unknown-operation stops and actionable failures always on. Do not optimize by simply skipping GL error/state work that rendering depends on.

**Acceptance:** same binary and saved scene, detailed trace on/off, matched menu/scene/map captures and input response; report log bytes/s, CPU seconds/frame, median/p95 period and major faults. Any lower write rate is a proven logging saving, not automatically a proven FPS or battery gain.

## 2. Repair the present-proof accounting before using sparse readback

**Observed source contract:** `nvn_video_should_sample()` samples every frame while `!proved`, irrespective of the requested sparse period. `nvn_present.h` only sets proof when `nonblack>=32 && t->draws`, while the substituted draw path increments `nvn_replay.draws` but does not account the draw into the texture's `draws`. In this visible gameplay interval all 356 readbacks reported `texture-draws=0 status=INCONCLUSIVE`. Therefore merely exporting `COTM_PRESENT_READBACK_60=1` / `COTM_READBACK_PERIOD=600` is **not sufficient** to guarantee a lower sampling cadence for this path.

**Next isolated A/B:** restore truthful per-target written-draw accounting for translated geometry and validate the complete final presentation chain. Do not count skipped placeholders, color-mask-zero stencil writers or failed draws as color proof. Then enable the existing sparse cadence and verify in the actual log that sampling becomes sparse after real proof. Retain explicit captures and honest `NOT-SAMPLED` state; do not relabel unobserved frames healthy.

**Acceptance:** real menu/gameplay KMS frames unchanged, a genuine proof of visible output, sparse readback count observed, sampled readback cost reported separately from unsampled frame cost, no black-state safety regression. `T2_READBACK_OFF=1` exists as a diagnostic floor experiment but disables periodic video health and is **not** the proposed production default. Mode 2 also waits for proof, so it is not a workaround for broken accounting.

## 3. Attribute and shrink the live guest/texture working set

The stored owner texture ledger (`texture-ledger.json`) still contains 500077312 bytes of DXT5 data, 48283728 of DXT1, 48116130 of ARGB4444, 36330680 of RGBA32 and 700284 of RGB24 after the selective mip promotion. Serialized payload size is not resident RAM or GPU memory. Guest source bytes, CPU-decoded pixels, temporary upload buffers and GPU storage need separate lifetime accounting.

**Next measurements:** record texture lifecycle live counts/bytes by native format, staging allocations and their lifetimes; compare fresh startup, the same scene and a return transition. Attribute the large Unity arena before patching an allocator or dropping pages. Cross-check live texture accounting against `/proc` and Mali memory, with explicit overlap caveats.

**Candidate changes after attribution:** release or reuse upload staging only after confirmed completion; avoid retaining redundant CPU RGBA copies where a GPU-authoritative/coherence contract permits it; explore lossless indexed/palette representations for suitable monochrome assets. Palette conversion saves an expanded RGBA copy only if the runtime samples the indexed representation directly—it does not automatically beat already-compressed DXT bytes. Do not globally halve textures again or promise a no-swap result.

**Acceptance:** lower committed/live memory at matched milestones, lower startup/transition major-fault and swap-I/O rates, no stale-texture overwrite, correct screenshots including text/portrait/map, save/load and clean exit.

## 4. Evaluate physical CPU placement, not blanket overclocking

**Observed:** the runtime maps guest CPU masks to physical CPUs 0–2 and pins guest main to CPU 0; the launcher enables cluster 0–3 so this works. Those CPUs are capped at 1.416 GHz while CPUs 4–7 are available at 1.992 GHz. One guest thread is close to saturating a lower-cluster core. This is a plausible latency lever, not a demonstrated gain or CPU-shortage proof.

**Next isolated A/B:** preserve guest-visible core IDs/masks but remap their physical execution to the faster cluster. Keep all thread placement, HID/audio workers and cleanup explicit. Do not run a blind process-wide taskset or disable cores while threads remain affined to them. A slower-clock/fewer-active-core variant may also matter for energy, but must be tested separately.

**Acceptance:** matched scene and clocks, per-thread CPU, frame-time distribution, audio continuity, input response, temperature/energy measurement if available, and restoration of original affinities/online mask. Faster frames are not synonymous with lower power.

## 5. Defer render-target size changes until the above baseline is stable

The scene/UI pipeline still uses intermediate 1920x1080 targets before 1280x720 output. An explicit 720p target path could reduce fill/storage/copy cost, but changing only the window does not change those intermediates, and lying about texture dimensions breaks viewport/UV/stencil/coherence contracts. Treat this as a separate quality-controlled phase with text, mask, layout and image-difference checks—not a quick launcher flag.

## Working rules

- Change one subsystem per A/B, preserve the current owner-section/runtime/launcher baseline and verify SHA-256 after activation.
- Separate source inspection, measured resource savings, frame-time changes and physical correctness in the report. No invented FPS, memory or battery gains.
- Keep no-op title-specific compaction/lazy-mesh patches disabled: the inherited lazy-mesh patch is keyed to another title's text identity, and the previous guest-compactor sample saved no pages here.
- Do not swapoff a loaded device, alter global swappiness or pin GPU maximum as an unmeasured default. No process killing outside the exact test runtime, no MainUI priority/OOM changes.
- End each bounded device test with a fresh process check and real Spruce KMS capture. Owner data and binaries remain local; publish authored code, tests and measured evidence on `feat/native-horizon-adapter`.
