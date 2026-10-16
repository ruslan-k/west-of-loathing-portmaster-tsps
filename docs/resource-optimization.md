# Resource optimization — measured baseline and next isolated tests

## Scope

The current owner build reaches real menus and Boring Springs with restored skinned bodies and the WANTED portrait mask. Map layout remains partially unresolved. Keep this visual baseline unchanged while measuring resource work. The historical baseline below is followed by the first measured logging-only optimization; the remaining sections are **candidates**, not shipped improvements.

Evidence: [gfx265](../evidence/gfx265/README.md), including raw `/proc` samples, compressed runtime interval and physical scene/cleanup captures. Date: 2026-10-15.

## Current M1–M9 status (supersedes historical numbers below)

The accepted M4 section remains installed. The [M1/M5 measurement pass](../evidence/memory-profile-m1m5/README.md)
adds reproducible read-only startup/phase, pagemap and descriptor-lifetime tooling.
Two cold launches measured ready-menu PSS+SwapPSS **878.29 / 881.96 MiB** and
outdoor-game **910.50 / 910.24 MiB**. One street → sheriff interior → street cycle
was verified in real DRM captures. These repeat observations are not a new
optimization A/B; the 700–750 MiB / no-swap target remains unmet.

- M1: bounded benchmark and runtime inventory implemented/exercised; GPU physical
  allocations and allocator active bytes remain unknown.
- M2/M3: deployed mip-tail removal and corrected RomFS entry length; see
  [M2 evidence](../evidence/mipstrip-m2/README.md).
- M4: first selective wave accepted by the owner; a conservative **53-texture**
  extension is staged and fully offline-verified only (18.75 MiB payload estimate),
  **not deployed** and not a measured RAM saving.
- M5: read-only pool/heap-page attribution and endpoint texture lifecycle measured;
  deeper Unity owner/free-list attribution remains open. About 699 MiB of counted
  heap pages in one snapshot lie outside NVN pools; this is not reclaimable/free proof.
- M6: side-cache implemented and E2E-verified on the device (create-path hook; fallbacks on
  the refresh, texel-flush and copy/image write paths; bcdec content canon; two final clean
  runs). Physical-memory win not demonstrated: a three-scene content probe (tut_main,
  tut_gulch, tut_saloonbasement - the last with 74 BC textures) shows **every** BC texture is
  created empty and filled later through `CopyBufferToTexture`, so the create-time cache has
  no real content to match (HIT=0 on content; the earlier 16 HITs matched the empty 512x512
  pattern only). The compressed store itself is clean (0 GL errors, visual parity between
  cache/no-cache arms). The create-time variant is effectively **closed**; a copy-path
  transcode would be a separate, CPU-expensive project. Evidence:
  `evidence/m6-compressed-textures/`, `content-scene-probes.md`.
- M7/M9: unsuccessful/deferred probes, not universal impossibility proofs. The
  earlier commit's 'dead end' language was too strong; see [scope corrections](memory-benchmark.md).
- M8: no page decommit until allocator ownership and full-page freedom are proven.

## FPS experiment: reusable buffers in the hot draw path (2026-10-15)

The chat-plan's "priority #1 for FPS" (reusable VBO/EBO instead of per-draw
create/delete) was measured on the **actual** hot path. Two findings, both device-based:

- The standard vertex path is unused on this title (`NVN_VERTEX_STATE_PROFILE
  pointer-sent=0` in every window), so the existing streaming-buffer opt-ins there
  cannot help; an A/B of `COTM_STREAM_VBO=1` changed nothing (game 25.44 → 25.05
  presents/s, within noise).
- The substituted-draw path did allocate/delete GL buffers per draw; a 6-slot
  reusable ring (`WOL_PAIR_RING`, default on, `=0` restores the old path) removes
  that churn. Measured over three paired runs: game **25.88 vs 25.51** median
  presents/s (ring on vs off) — **no gain beyond run-to-run variance**, no regression,
  pictures and saves intact.

Full numbers, receipts and limits: [fps-pair-ring](../evidence/fps-pair-ring/README.md).
Runtime `d3a4ce6a…` (build `wol-horizon-build-pairring`); owner section unchanged
(`a25600ce…`). GL-object churn being real but not a bottleneck rules the buffer-arithmetic
family out as the next FPS lever; the measured frame split (replay ~28-33 ms, finish
~11-16 ms per slow frame) points at replay/CPU work and the per-submit finish instead.

## FPS profiling and the per-frame texture-copy chain (2026-10-15, later)

An `AW_PROFILE=1` sampling run plus three bounded attribution counters found the real per-frame
chain: one `CopyTextureToTexture` of 3.69 MB runs every frame into texture `460`, implemented as
a CPU row copy plus a full-texture re-upload (measured 9.44 GB copied and 9.44 GB uploaded in one
run). Replacing it with a GPU region blit (`WOL_COPY_GPU=1`) removed the whole chain and kept the
picture correct, but measured **slower** (menu 26.74 -> 21.51 presents/s; finish 12.6 -> 18.3 ms):
the mid-frame blit serialises GPU work more than the overlapped CPU copies cost. Default stays
`WOL_COPY_GPU=0`. Details: [fps-gpu-copy](../evidence/fps-gpu-copy/README.md).

A second, narrower attempt removed the staging memcpy of the re-upload itself
(`WOL_REFRESH_DIRECT=1`: upload straight from guest storage): it engaged on all 2560 refreshes
(`direct-levels=2560`) and measured, over three paired runs, **flat-to-slightly-negative**
(staging menu 26.28 / game 26.17 vs direct menu 25.68 / game 26.03). The staging copy was not on
the critical path; the option stays opt-in and the default keeps the staging copy. Details:
[fps-refresh-direct](../evidence/fps-refresh-direct/README.md).

Both ends of the per-frame copy/upload chain are therefore closed as FPS levers - the remaining
measured costs sit in replay CPU work and the per-submit finish, not in this chain.

**Draw-path attribution (2026-10-16, roadmap section 3):** the replay draw records cost
8.6-9.2 ms per frame. Sub-span instrumentation places ~4.4 ms in the texture-selection first
resolve (quiet-pick), ~0.8-1.1 ms in `glUseProgram` plus the two 96-float constant uploads and
~1.0 ms in the GL submissions themselves; the six first-after-target-change draws average
~820 us against ~68 us for ordinary draws. Details, methods and limits:
[fps-frame-timeline](../evidence/fps-frame-timeline/README.md).

**Texture-copy dependency trace (2026-10-16, roadmap section 4):** the per-frame colour copy
rotates between three source buffers into a fixed destination, samples the destination twice
right after the copy and re-draws the source afterwards; no destination read ever follows a
source re-draw (256/256 intervals, whole run). A guarded lazy alias is rejected: the source
mutates on every frame, so a deferred copy would have to materialise before that mutation and
keep the full per-frame copy cost, and the no-materialisation variant needs an invariant the
trace cannot guarantee beyond stationary scenes. The copy chain stays as-is.
[copy460-dependency-trace](../evidence/copy460-dependency-trace/README.md)

Code, scene coverage, cleanup receipts, exact artifact hashes and limitations:
[measurement documentation](memory-benchmark.md). Game binaries, owner bundles,
texture bytes and saves are not published.

## Historical baseline: what the earlier session cost

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

**Implemented:** `WOL_DRAW_TRACE=1` opts into the old successful per-draw trace volume. Unset, `0` and other values keep that success output off. The same gate covers successful downsample-blit and compute-only program-bound messages. One configuration receipt and the existing periodic summaries remain. Error detection, pointer/range validation, shader identity checks, unknown-operation stops and actionable failures remain always on. In particular, `glGetError()` still executes at both draw/blit sites, and nonzero errors still print when detailed tracing is disabled. Resource binding, uniforms, geometry, stencil, counters and readback cadence were not changed.

**Acceptance:** same binary and saved scene, detailed trace on/off, matched menu/scene/map captures and input response; report log bytes/s, CPU seconds/frame, median/p95 period and major faults. Any lower write rate is a proven logging saving, not automatically a proven FPS or battery gain.

**Measured A/B/A/B:** [resource-draw-logging evidence](../evidence/resource-draw-logging/README.md), same `c35548fb…` binary and SHA-verified save snapshot, four approximately 30-second stationary Boring Springs windows. Both control runs restore trace verbosity without rebuilding. `WOL_RECT_TRACE=off` and `MOMO_FRAME_CLOCK=1` are identical in all four runs; this is not a comparison against gfx265's differently instrumented baseline.

- Log growth: **312.26 / 329.46 KiB/s** with detailed trace; **27.04 / 23.80 KiB/s** without it. Mean **320.86 → 25.42 KiB/s**, **92.08% less log growth**.
- Presents/s: **11.64 / 11.65 → 12.36 / 12.13**. Mean **11.65 → 12.25** (observed **+5.12%**, not a universal FPS guarantee).
- Process CPU time per frame: mean **133.24 → 126.23 ms**, observed **−5.26%**. This is summed process CPU time, not frame wall time. Overall CPU utilization stays approximately **155% of one core** in both modes; no material reduction in utilization or power is established.
- Median periods: **82.25 / 83.46 → 77.89 / 79.32 ms**; p95: **88.56 / 89.73 → 84.24 / 84.06 ms**. Major faults vary **29.78–42.41/s**; cache/swap state and scene animation are not controlled perfectly.
- No RAM saving: per-run mean RSS is **684–708 MiB** and VmSwap remains around **700 MiB**. No watts, battery-life or physical-button validation was performed. The visible stick response was checked through the opt-in diagnostic Npad channel, with real KMS movement frames.
- Menu/WANTED mask, complete player/Cactus Bill bodies, map open/close and final Spruce menu were checked in real KMS frames. The map remains largely blank; this change neither fixes nor validates its unresolved content/layout. Only exact test-runtime PIDs were stopped, the original owner save snapshot was restored and re-hashed, and the new runtime remains installed.
- Native build, 22 baseline unit tests, seven standalone regression commands (including the compiled trace/error policy test), upstream-overlay dry check and an independent code-only review passed. The review applies only to this small diff, not to all historical experimental code.

## 2. Repair the present-proof accounting before using sparse readback

**Observed source contract:** `nvn_video_should_sample()` samples every frame while `!proved`, irrespective of the requested sparse period. `nvn_present.h` only sets proof when `nonblack>=32 && t->draws`, while the substituted draw path increments `nvn_replay.draws` but does not account the draw into the texture's `draws`. In this visible gameplay interval all 356 readbacks reported `texture-draws=0 status=INCONCLUSIVE`. Therefore merely exporting `COTM_PRESENT_READBACK_60=1` / `COTM_READBACK_PERIOD=600` is **not sufficient** to guarantee a lower sampling cadence for this path.

**Next isolated A/B:** restore truthful per-target written-draw accounting for translated geometry and validate the complete final presentation chain. Do not count skipped placeholders, color-mask-zero stencil writers or failed draws as color proof. Then enable the existing sparse cadence and verify in the actual log that sampling becomes sparse after real proof. Retain explicit captures and honest `NOT-SAMPLED` state; do not relabel unobserved frames healthy.

**Acceptance:** real menu/gameplay KMS frames unchanged, a genuine proof of visible output, sparse readback count observed, sampled readback cost reported separately from unsampled frame cost, no black-state safety regression. `T2_READBACK_OFF=1` exists as a diagnostic floor experiment but disables periodic video health and is **not** the proposed production default. Mode 2 also waits for proof, so it is not a workaround for broken accounting.

**Validated 2026-10-16** (build `982cb51b…`, `COTM_PRESENT_READBACK_60=1`, period 300): pixel proof at frame 4, `texture-draws>0` on every sample, post-proof spacing exactly at the 300-frame period and 2895 honest `NOT-SAMPLED` frames. [evidence](../evidence/present-proof-sparse/README.md)

## 3. Attribute and shrink the live guest/texture working set

The stored owner texture ledger (`texture-ledger.json`) still contains 500077312 bytes of DXT5 data, 48283728 of DXT1, 48116130 of ARGB4444, 36330680 of RGBA32 and 700284 of RGB24 after the selective mip promotion. Serialized payload size is not resident RAM or GPU memory. Guest source bytes, CPU-decoded pixels, temporary upload buffers and GPU storage need separate lifetime accounting.

**Next measurements:** record texture lifecycle live counts/bytes by native format, staging allocations and their lifetimes; compare fresh startup, the same scene and a return transition. Attribute the large Unity arena before patching an allocator or dropping pages. Cross-check live texture accounting against `/proc` and Mali memory, with explicit overlap caveats.

**Candidate changes after attribution:** release or reuse upload staging only after confirmed completion; avoid retaining redundant CPU RGBA copies where a GPU-authoritative/coherence contract permits it; explore lossless indexed/palette representations for suitable monochrome assets. Palette conversion saves an expanded RGBA copy only if the runtime samples the indexed representation directly—it does not automatically beat already-compressed DXT bytes. Do not globally halve textures again or promise a no-swap result.

**Acceptance:** lower committed/live memory at matched milestones, lower startup/transition major-fault and swap-I/O rates, no stale-texture overwrite, correct screenshots including text/portrait/map, save/load and clean exit.

**First read-only census 2026-10-16** (build `982cb51b…`): ~153 MiB host image estimate in gameplay, only ~7.1 MiB safely reconstructible (budgeted eviction gate not met); stationary vertex streams byte-identical between frames (100% of sampled bytes). [evidence](../evidence/gpu-texture-residency/README.md)

## 4. Evaluate physical CPU placement, not blanket overclocking

**Observed:** the runtime maps guest CPU masks to physical CPUs 0–2 and pins guest main to CPU 0; the launcher enables cluster 0–3 so this works. Those CPUs are capped at 1.416 GHz while CPUs 4–7 are available at 1.992 GHz. One guest thread is close to saturating a lower-cluster core. This is a plausible latency lever, not a demonstrated gain or CPU-shortage proof.

**Next isolated A/B:** preserve guest-visible core IDs/masks but remap their physical execution to the faster cluster. Keep all thread placement, HID/audio workers and cleanup explicit. Do not run a blind process-wide taskset or disable cores while threads remain affined to them. A slower-clock/fewer-active-core variant may also matter for energy, but must be tested separately.

**Acceptance:** matched scene and clocks, per-thread CPU, frame-time distribution, audio continuity, input response, temperature/energy measurement if available, and restoration of original affinities/online mask. Faster frames are not synonymous with lower power.

**Measured 2026-10-16** (isolated A/B with alternated order, same build and layout): no repeatable gain outside the ±1–1.5 ms run envelope in either direction; the remap stays an opt-in flag, not a default. [evidence](../evidence/cpu-remap-ab/README.md)

## 5. Defer render-target size changes until the above baseline is stable

The scene/UI pipeline still uses intermediate 1920x1080 targets before 1280x720 output. An explicit 720p target path could reduce fill/storage/copy cost, but changing only the window does not change those intermediates, and lying about texture dimensions breaks viewport/UV/stencil/coherence contracts. Treat this as a separate quality-controlled phase with text, mask, layout and image-difference checks—not a quick launcher flag.

## 6. Experimental menu/game checkpoint

The new [resource-goal checkpoint](../evidence/resource-goal-checkpoint/README.md) implements truthful target RGB accounting, optional exact RGBA4444 and guest-ABI-preserving host CPU remapping. With real periodic video checks enabled, the measured menu/game windows reached **21.815 / 19.042 presents/s**, compared with **13.745 / 12.953** in the exploratory baseline. Combined/sequential changes are not isolated causal A/B evidence.

The resource target remains **unmet**: end rollup PSS+SwapPSS is **1054.92 / 1079.86 MiB** in menu/game, and this still excludes a reliable driver-allocation inventory. Status RSS is lower than 1 GiB but does not establish a whole-game budget. Dimensions and clocks were not reduced/changed. Driver storage for eligible 4444 images is estimated, not measured.

This is a user-requested experimental checkpoint, **independent review not-cleared**, not a release. The latest freshly rebuilt artifact is recorded separately from the measured artifact and is being rechecked on-device. The map defect is unresolved. See the evidence README for receipts, standalone regression commands, KMS captures, cleanup/save checks and remaining work.

## Working rules

- Change one subsystem per A/B, preserve the current owner-section/runtime/launcher baseline and verify SHA-256 after activation.
- Separate source inspection, measured resource savings, frame-time changes and physical correctness in the report. No invented FPS, memory or battery gains.
- Keep no-op title-specific compaction/lazy-mesh patches disabled: the inherited lazy-mesh patch is keyed to another title's text identity, and the previous guest-compactor sample saved no pages here.
- Do not swapoff a loaded device, alter global swappiness or pin GPU maximum as an unmeasured default. No process killing outside the exact test runtime, no MainUI priority/OOM changes.
- End each bounded device test with a fresh process check and real Spruce KMS capture. Owner data and binaries remain local; publish authored code, tests and measured evidence on `feat/native-horizon-adapter`.
