# TSPS native Horizon adapter — incomplete graphics bring-up

**Verdict: partial. No WoL game frame, playable launch, input or audio proof.**

This adapter is separate from `wol_native_probe.c`. The minimal QEMU probe still stops at LM; the recovered GPL Horizon adapter has progressed farther on the real TSPS.

## Device evidence

Five launches used the real Spruce principal → `standard_launch.sh` → port launcher flow, not a parallel shell launch beside MainUI. Their full port logs and after-exit DRM menu captures are under `evidence/device-01` through `device-05`.

Progressive, isolated changes:

- Run 01: `NVN_QUEUE_DEVICE`.
- Run 02: corrected queue-builder device offset; next stop `NVN_MEMORY_POOL_DEVICE`.
- Run 03: corrected memory-pool builder device offset; next stop `NVN_BUFFER_DEVICE`.
- Run 04: corrected buffer-builder device offset; next stop `ZERO_SHADER_CONTROL_LAYOUT` at `main+0xafe4c8`.
- Run 05: captured the measured old-format shader envelope without attempting a guessed translation; controlled stop `WOL_SHADER_TRANSLATION_REQUIRED`, same caller, exit 20.

All three builder setters in this exact SDK perform `str x1,[x0]; ret`: queue RVA `0x2c5238`, pool `0x2c154c`, buffer `0x2b6590`. The inherited runtime read device at builder +8. WoL-specific macros select +0, while the inherited defaults remain unchanged. Buffer objects themselves still have the measured 48-byte layout; builder and object offsets must not be conflated.

The latest run:

- Real Mali-G57, EGL 1.4, OpenGL ES 3.2.
- Surface **8×8 pbuffer**, explicitly `no-draw-no-present`. This is NOT an SDL game window, physical frame or rendering-success proof.
- Queue initialized; command/control storage, memory pools, buffer mapping/address and first ProgramSetShaders reached.
- RSS at controlled stop: **159040 kB / 155.3125 MiB**; VmSwap 0. This does not measure later UnityFS bundle loading or scene-transition peak.
- First shader control capture: 2120 bytes, SHA-256 `461f9847f0242e09c8fe146fbac7221c822a3c260f3759a8f2fdea6b4c0d4492`.
- GPU-code **prefix**, not a complete shader package: 512 bytes, SHA-256 `e033dd6a7f4f886c57e6a90cd156f87c8c6185cb9c9197a7939948f22771cb87`.
- Captured proprietary bytes remain in the owner's local workspace/device; they are not committed here.

Latest installed diagnostic runtime SHA-256:
`0e400a8de03bd4bd2ae0e72e2ab96c7edfe0801f434a7203984b950e2c768c97`.

The owner payload manifest passes on-device, including this binary. Its dynamic GLIBC requirements are only 2.17 and 2.27; it uses firmware SDL/EGL/GLES libraries. The previous runtime is retained in the port's `backups/`.

After run 05, fresh SSH checks found MainUI running, no runtime process, no pending `/tmp/cmd_to_run.sh`, and CPU online mask restored to 4–7. The actual DRM screenshot `evidence/device-05/after-menu.png` shows the normally rendered Spruce home menu, **not** a WoL frame. Menu recovery is proven; successful game startup is not.

## Source and owner-data boundaries

The baseline consists of the two supplied upstream source patches, reconstructed as described in `upstream-source.md`. `runtime/source-manifest.sha256` pins all 435 baseline files. `runtime/wol-adapter.patch` contains only our GPL modifications, not modules, assets or shader payloads.

The recipe validates the entire baseline, copies it into a new output workspace, applies the overlay with `git apply --check`, compiles the providers and builds the adapter. It does not modify the recovered baseline. The source overlay disables inherited title-specific texture/clear exceptions, adjusts the guest budget/name, selects old WoL builder offsets and captures the unsupported first shader fail-closed. It does not implement a WoL shader translator.

Generate a NEW owner-only image:

```sh
python3 prepare_horizon_image.py \
  /path/to/exefs /path/to/wol-npdm.json /path/to/wol-romfs.json \
  /path/to/owner-horizon-image
```

NPDM metadata needs `title_id`, `is_64_bit`, `main_thread_stack_size`, `main_thread_priority`, `default_cpu_id`, `service_access`. RomFS metadata needs `section`, `section_size`, `sha256`, `romfs_offset`, `romfs_size`; the section must already be extracted and verified from the owner's input. This is an internal bring-up interface, not an end-user extractor. Image output contains proprietary data and must never be shared.

Build in the verified local Ubuntu/Focal ARM64 cross environment (image is local, not a publicly downloadable dependency):

```sh
docker run --rm --security-opt label=disable \
  -v /path/to/recovered-source:/reference:ro \
  -v /path/to/owner-horizon-image:/image:ro \
  -v "$PWD:/work" --entrypoint /bin/sh \
  pmjs-arm64-spruce-local:20261002-gcc10 \
  -c 'cd /work && bash build_horizon.sh /reference /image /work/horizon-build-new'
```

Require a previously absent output directory. The final executable is `horizon-build-new/wol-horizon`. Exact bytes depend on compiler/source paths; the installed hash above is a deployment receipt, not a promised portable reproducible hash.

`West of Loathing Switch.sh` is a **35-second diagnostic launcher**, not a playable release. It enables the cluster needed by the recovered runtime and leaves Spruce to restore its normal mask on return. It writes `wol-switch/logs/latest.log`, uses a separate laboratory save directory and exits nonzero on the unsupported shader. Test it only with authorization through the Spruce principal flow while the device is in the menu; never launch alongside another game.

## Remaining acceptance gates

1. Recover the exact old shader package layout and implement/pin semantic GLSL ES translations. No empty or guessed pass-through shader is acceptable game-frame proof.
2. Verify the remaining WoL-specific NVN texture/window/command layouts and actual present.
3. Obtain a physical DRM screenshot containing WoL, then verify controls, audio, scene transition, memory behavior and clean exit.

The five controlled stops establish a graphics bring-up frontier, **not completion of the requested port**.

## Progress log: runs 06-23 (same principal flow, one variable per run)

Every run below launched through the Spruce principal flow and ended with the menu restored (verified by
`/proc` plus a physical DRM capture). `evidence/tsps-device-runs.json` tabulates the stop code, guest PC
and RSS of each run; the per-run logs live in `evidence/device-NN/`.

| Run | Stop | Cause and what the fix had to prove |
|----|------|--------------------------------------|
| 01-03 | `NVN_QUEUE_DEVICE` / `NVN_MEMORY_POOL_DEVICE` / `NVN_BUFFER_DEVICE` | The inherited runtime read the device pointer at builder+8; this SDK stores it at builder+0 (`str x1,[x0]` in `sdk+0x2c5238`, `+0x2c154c`, `+0x2b6590`). Three separate builder offsets, each pinned to the original store. |
| 04-05 | `ZERO_SHADER_CONTROL_LAYOUT` | The inherited control-layout checks (`0x850`/`0x880`, `+0x70c` semantics) do not describe this SDK. The WoL build now validates the measured envelope: magic `0x98761234`, version 1, control size `0x848`, code size at `+0x704`, and stops with `WOL_SHADER_TRANSLATION_REQUIRED` instead of guessing a translation. |
| 06-07 | `NVN_CAPTURE_OPEN` -> `NVN_SAMPLER_PARAMETERS` | Dump filenames collided (same sequence); the sampler builder was decoded with the 17.5.3 packed layout. This SDK's `NVNsamplerBuilder` is the unpacked `0x48`-byte form (`nvnSamplerInitialize` copies exactly `0x48` bytes; `SetDefaults` writes min 1 / mag 1 / wrap 1,1,1 / lod 0..1000 / compare 0,2 / aniso 1.0). |
| 08-09 | `NVN_SAMPLER_ALREADY_LIVE` -> `NVN_TEXTURE_DEVICE` | This title re-initialises one stack `NVNsampler` several times (legal: the pool copies the state at register time). Referenced entries are now retired by address but keep their id, unreferenced ones are rewritten. The texture builder is likewise unprefixed (device +0, flags +0x18, target +0x1c, size +0x20.., levels +0x2c, format +0x30, samples +0x34). |
| 10-11 | `NVN_WINDOW_CONTRACT` -> `ZERO_TEXEL_VIEW_RESERVED` | Window builder is unprefixed too (device +0, count +8, textures +0x10, native +0x18, interval +0x20; `nvnWindowInitialize` copies the same offsets). `NVNtextureView` is the 36-byte form (flags byte +0 with bits levels/layers/format/swizzle/depth-stencil/target, level u8 at +1/+2, layer u16 at +4/+6, format +8, swizzle +0xc, depth-stencil +0x1c, target +0x20). |
| 12 | `WOL_SHADER_TRANSLATION_REQUIRED` on the second shader | All 16 shader programs in `main.rodata` are enumerated, disassembled and hashed; the runtime logs each request with code/control SHA-256 and continues with a placeholder that binds and draws nothing. |
| 13-19 | `CPU_FAULT` (SDL-raised, then the real guest fault) | The SDL crash handler was masking the real fault; `SDL_NO_SIGNAL_HANDLERS=1` makes this runtime's handler authoritative. The real fault was in the guest SDK's `printf` path: Unity's `DynamicHeapAllocator` reported "System out of memory!" while formatting the message. |
| 20 | (no stop) | The guest memory budget was the diagnostic 768MiB; this title sizes its Unity heap from the reported total and then failed an allocation during asset loading. Raised to 2048MiB as a **virtual** quota (guest mappings stay lazy; RSS is reported separately). The run then passed the OOM point entirely. |
| 21 | `NVN_TEXTURE_DIMENSIONS_REQUIRED` | The camera target is requested as target 5 with 2 samples (1920x1080). Downgraded to a plain 2D target with `WOL_MSAA_DOWNGRADED` logged - a quality deviation in the same class as the existing HDR-as-RGBA8 case, not an MSAA claim. |
| 22 | `NVN_OPERATION_REQUIRED` (`nvnCommandBufferDownsample`) | The title resolves its camera target with a downsample. Accepted as `WOL_DOWNSAMPLE_PLACEHOLDER` (logged, copies nothing, invents nothing): the source has no GPU-produced content until draws are translated. |
| 23 (current) | `NVN_COPY_TEXTURE_FORMAT_REQUIRED` (format `0x41`) | **The title now records and submits real frames**: run 23 reached `nvnCommandBufferBindProgram` and `nvnQueueSubmitCommands` with a 182-command list. The stop is in the replay of a compressed (`0x41`) buffer-to-texture upload, which the copy path does not accept yet. |

### Current frontier

- Device: real EGL/KMSDRM window at 1280x720, 29 textures, 116 shader programs inventoried, ~300MB RSS,
  zero swap, menu returns cleanly after every run.
- The rendering pipeline is exercised end to end except the parts that need translated shaders: programs are
  bound (`mask=0x1` seen) and command lists are submitted; nothing is rasterised because every program is
  still a placeholder.
- Next, in order: (1) accept the compressed upload in the copy replay path (BC layout helpers already exist
  for texel writes), (2) translate the first real shader pair and replace the placeholders programme by
  programme, (3) then re-check the downsample as a real blit and, only after that, claim a frame.

**Nothing in this document claims a rendered frame, playable launch, input or audio.**

### Runs 24-31: the first frame reaches the panel

| Run | Stop | What happened |
|----|------|----------------|
| 24-25 | `ZERO_BC_MIP_STORAGE` | The compressed upload path needed this title's 2D target set (targets 1/2/4 all occur here) and the measured target is now logged once per texture (`WOL_BC_PIXELS`) instead of assumed. |
| 26 | `NVN_PROGRAM_INVALID` | Draws resolved programs that the placeholder binds never recorded. Placeholder draws are now counted and skipped (`WOL_DRAW_PLACEHOLDER`, mode 4 count 6 = Unity quads) so the recorded frame stays replayable. |
| 27-30 | `ZERO_TEXTURE_COPY_FORMAT_REQUIRED` / `WOL_COLOR_COPY_*` | Colour texture-to-texture copies (RGBA8, one level) are storage byte copies with the host copy following on refresh; the log proved the real shape: a 1280x720 region copied 1:1 out of the 1920x1080 render target. A differing-extent case falls back to a logged box-average resample until a translated blit shader exists. |
| **31** | `NVN_QUEUE_CONTEXT` (EGL_BAD_SURFACE) on the second submit | **The first frame was presented**: record (182 then 157 commands) -> submit -> replay -> window swap -> `NVN_PRESENT_PIXELS frame=1 status=BLACK-SAMPLE`. The picture is black because every draw is still a placeholder; the pixel probe reports exactly that instead of claiming content. |

### Where the picture must come from now

The pipeline is complete end to end with one honest hole: **no program is translated**, so every draw is
skipped and the frame is black by construction. Translating the first vertex/fragment pair and replacing
the placeholders program by program is the actual path to a picture; the downsample, the box-average
resample and the MSAA downgrade are all downstream of that and revisit with the real blit.

Next engineering steps, in order:

1. Fix the second-submit `EGL_BAD_SURFACE` (the present path and the queue path disagree about which
   surface owns the context after a swap).
2. Translate the first shader pair: pick the pair actually used by the first drawn quad from the
   inventory, write the GLSL ES translation into the catalogue, and re-run until the documented stop
   moves past the draw.
3. Only then revisit quality items (real downsample blit, real MSAA, filtered scaling).

### Runs 32-37: the surface lifecycle fix, and 33 frames on the panel

`NVN_QUEUE_CONTEXT`/`NVN_PRESENT_CONTEXT` (EGL_BAD_SURFACE, 0x300d) were the same root cause: the window comes
from **SDL's KMSDRM backend** (`NVN_SYSTEM_WINDOW backend=SDL driver=KMSDRM`), SDL recreates its EGL surface on
swap, and the runtime kept binding the cached handle. Measured along the way:

| Run | Change | Result |
|----|--------|--------|
| 32 | `T2_GPU_PIPELINE=0` | **Falsified**: the async present path is not the cause, identical stop. |
| 33 | surface diagnostic before the bind | The window surface answers `eglQuerySurface` (alive) while `eglMakeCurrent` still fails; `EGL_SUCCESS` pending. |
| 34 | `COTM_SINGLE_CONTEXT=0 COTM_GAME_PBUFFER=1` (the runtime's pbuffer-producer mode) | The **second submit passes** (157 commands, `glFinish`); the stop moves to the second present. |
| 35 | `T2_DISPLAY_BACKEND=fbdev` | **Falsified**: device init fails with EGL_BAD_DISPLAY (0x3008) — SDL/KMSDRM owns the display. |
| 36 | `nvn_platform_live_surface()` with `eglGetCurrentContext()` | No effect: the runtime detaches between operations, so the thread has no current context to hand SDL. |
| **37** | same helper using **SDL's own context** | **33 frames presented in a row**, 8 submits, no EGL error. Render surface = pbuffer, presentation = physical window. |

Runtime is now stably in the game loop: the stop is `INVALID_ROMFS_READ_RANGE` (a guest asset read outside the
mapped RomFS section, detail 0x4630d0) with RSS 500 MiB - an asset-mounting question, not a graphics one.
Nothing here is a rendered picture; every draw is still a placeholder, so every present is `BLACK-SAMPLE` by
construction.

### Runs 38-39: the engine loads its assets, and the device runs out of RAM

After the surface fix the title reads its own content: 23 RomFS reads succeed, then one request is refused by
the runtime's own guard. The refused request says exactly what it wanted (`ROMFS_READ_REFUSED`):
`offset=0x4630d0 size=0xbf15cfc romfs-size=0xcf2ffe4 outputs=1 output-size=0xbf15cfc clause=over-64M` - the
title reads the **whole remaining RomFS (191 MiB) in one request** with a matching guest buffer, and only the
zero-family 64 MiB cap rejected it. The cap is now a build parameter (`FILESYSTEM_ROMFS_READ_LIMIT`, 64 MiB by
default, 256 MiB for this title) and the refusal prints every field instead of just the offset.

Run 39 then presented 32 frames and stopped on `T2_MEMORY_FLOOR` with VmRSS 666 MiB, VmPeak 3.0 GiB - the
runtime's own availability guard (140 MiB, `T2_MEMORY_FLOOR_MIB`) caught the device running out of RAM during
asset load. That is a memory-budget problem, not a graphics one: the guest heap is declared 2048 MiB virtual,
the device has ~1 GiB, and the title keeps its bundles resident.

### Runs 40-42: memory ceiling, and a tracer that must never crash the report

| Run | Change | Result |
|----|--------|--------|
| 40 | probe budget 35s -> 90s | Same floor hit (available 133 MiB, RSS 693 MiB): the load's memory is resident, not a transient peak. |
| 41 | `T2_MEMORY_FLOOR_MIB=64` (bounded diagnostic) | **120 frames presented** (3.6x run 39) with the kernel starting to swap (VmSwap 95 MiB); then a **host** SIGSEGV inside the runtime's own frame tracer while it reported another problem. |
| 42 | tracer hardening (`accessible()` guard on lr and each frame) | The tracer now prints `unmapped` instead of dying on guest addresses, and the remaining host fault is localised: `trace_frames` is also called with a **host** fault context, where its module lookup walks host addresses (`pc` offset 0x19abc in the binary, resolved offline with the cross toolchain as `trace_frames.isra.0`). |

Notable runtime fact for the memory work: `T2_MEMWATCH` documents its own guard - `floor-MiB=140 swap-floor-MiB=16 texture-budget-MiB=420 reason=gpu-memory-is-invisible-to-vmrss`.

### Run 43: the guest compactor does nothing for this title, and the crash is a bridge

- `T2_GUEST_ZRAM=1` with `T2_GZRAM_TARGET_MIB=400 T2_GZRAM_STATS_MS=1000 T2_GZRAM_POOLS=0`: the compactor
  reports `compressions=0 faults=0 restores=0 scans=0 saved-MiB=0.0` for the whole run with
  `scope=alias_physical` - Unity's memory is not in the areas it can compress, so this lever is **falsified
  for this title** (measured, not assumed; the reviewer asked exactly this).
- The frame tracer guards hold: every stop now prints guest traces (`GUEST_FRAMES ... <- unmapped`)
  instead of dying in the tracer.
- The host crash that replaces the report is localised: the faulting register dump is a **bridge context**
  (guest x28 = `main.text.seg+0xaf2d14`, the `nvnQueuePresentTexture` call site) with host `pc`/`lr` at
  offsets 0x19a8c/0x19abc of the binary. In other words the runtime dies inside a reimplemented SDK
  bridge called from the present path, and the stop report only ever shows the crash, not its cause.
  Next: name that function from the symbol table and fix it so the real stop surfaces.
- Launcher: CPU online state is now captured per cpu and restored on exit (runs had left 0-3 permanently
  online); guest zram settings are env-reversible (`WOL_GUEST_ZRAM=0`).
