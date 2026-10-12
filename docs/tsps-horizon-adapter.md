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

### The first draw's shader pair: identity and captured binaries

The reviewer's P2 item is done from the existing evidence, without a new device run: for the first recorded draw
(`WOL_DRAW_PLACEHOLDER mode=4 count=6`) the runtime bound two program objects, and their identities are now
pinned in `evidence/first-pair/`:

| Stage | Program object | Program id | Code bytes | Code SHA-256 | Control SHA-256 (variant used by the bind) |
|-------|----------------|-----------|-----------|--------------|--------------------------------------------|
| vertex (mask 0x1) | 0x100103f168 | 233 | 768 | `f309b86a229fafbf3e47c6b33cea95af652212cfe3603c77ac44b2e221c9e20e` | variant of `f309b86a` (many; see note) |
| fragment (mask 0x2) | 0x100103f298 | 235 | 512 | `f08bad2f44a02bae7083854769755e05be1a692c35f6e17dbc88f80625b83d0e` | variant of `f08bad2f` |

- The captured blobs are `evidence/first-pair/vertex-f309b86a229f.{code,control}.bin` and
  `evidence/first-pair/fragment-f08bad2f44a0.{code,control}.bin`; both code files were fetched **by matching
  SHA-256 on the device** (the dumps carry no sha in their names), so the mapping is verified, not guessed.
- Note on variants: one *code* blob appears with many *control* SHAs (`f309b86a` shows at least four control
  layouts in a single run). The catalogue must therefore be keyed by **code SHA + control SHA**, not by program
  id - the control block carries the interface (attributes, uniform layout) for that variant.
- Next for this workstream (offline, no device): feed the two code blobs to the Hades/Yuzu Maxwell recompiler
  (`shader-compiler-rs`), check the 0x30-byte SPH expectation against our 0x848-byte control + separate code
  layout, then translate to GLSL ES and register the pair in the catalogue by its SHA pair.

### The first pair disassembled: a tinted 2D sprite (both stages)

Tooling: envytools' `envydis` built from source (cmake + ninja) - the captured blob already begins with the
NVIDIA SPH header (`0x12345678`), so the SASS starts at `+0x30`:

    envydis -m gm107 -d 0x30 -i <blob>      # gm107 covers the Tegra X1 GM20B ISA

Full listings are `evidence/first-pair/vertex.sass.txt` and `fragment.sass.txt`. What they do:

- **Vertex (`f309b86a`, 768 B)**: two `mov $rX c3[0x80/0x84]` uniform constants, two attribute loads
  (`ld b32 $r6 a[0x80]`, `ld b32 $r8 a[0x90]` - attribute slots 8 and 9, matching the 0x58-byte vertex
  stride seen in the bind logs), then a chain of `fmul`/`ffma`/`fadd` against `c3[0x4..0x34]` - i.e. a
  uniform matrix/offset transform of the position, no texture access.
- **Fragment (`f08bad2f`, 512 B)**: two `ipa pass` interpolants (`a[0x7c]`, `a[0x84]`), `mufu rcp` +
  `fmul` (the perspective divide of the UV), `texs nodep $r2 $r0 $r4 $r5 0x8 t2d rgba` (a 2D RGBA texture
  sample with computed LOD), two `fmul ... c3[0x4/0x8]` tint multiplies, `exit`.

In other words the target is Unity's ordinary tinted sprite/UI pair. That makes a **hand translation to
GLES2 GLSL tractable** (the reviewer's variant B), and it fixes the interface for the catalogue entry:
constant bank c3 offsets, attribute slots 8/9, one sampler, one interpolated UV pair.

Next: write that GLSL ES pair, key it by (code SHA + control SHA), and let the first draw use it instead of a
placeholder - the first pixels that actually come from the game's own draw.

### Translation draft: what is measured, what is still open

`docs/shader-draft/f309b86a+f08bad2f.draft.glsl` transcribes every **decoded** SASS statement of the pair
one-to-one (constant bank 3 as `uniform float c3[]` so `c3[0xNN>>2]` is the exact u32 at byte 0xNN;
attribute and varying space addressed as slot `0xNN>>4`, component `(0xNN>>2)&3`). It is deliberately
**not wired to a draw**: four measurements are still missing before a translation may claim correctness -
(1) the attribute component order (the guest vertex-attrib state object is the source of truth and is not
decoded yet), (2) the 33 SASS lines envydis does not decode (they carry the position stores and part of
the varying writes), (3) the TEX operand roles, (4) the fragment tail. Everything unresolved is a TODO in
the file; nothing is invented to fill a gap.

### Runs 44-46: the diagnostic crash is gone; the stop is honest again

The crash that replaced the real stop in runs 41/43 was **two bugs in the fault path, both in the early
return of the signal handler** (`loader.c`):

1. `signal_dispatch()` publishes the *live* signal frame as the thread-local `current_guest_context`, and
   the `sig != SIGTRAP` early return never restored the previous value - so every later `stop()` traced a
   **stale frame**. That is exactly the hybrid context seen in the logs (guest registers such as
   `main.text.seg+0xaf2d14` with host `pc`/`lr`) and the SIGSEGV at `trace_frames.isra.0+0x74` when that
   memory was no longer usable.
2. The same early return never decremented `signal_handler_depth`, so the process believed a handler was
   still running and skipped later traces.

Additionally the stall census walked *other* threads' stored kernel contexts, whose host stacks may already
be released; it now only walks the calling thread's own context (the stall fields keep their value).

| Run | Result |
|----|--------|
| 45, 46 | **Two consecutive runs with a clean, controlled stop**: `T2_MEMORY_FLOOR` (available 136/134 MiB against the restored conservative 140 MiB floor), exit 26, zero `CPU_FAULT`, zero tracer crashes. |

This satisfies the review's acceptance criterion for the crash item ("several consecutive tests with a
clean exit or an unambiguous controlled stop, with no crash of the diagnostic code"). The honest limit is
now visible instead of hidden: the title's resident set no longer fits under the conservative floor, and
that is the next problem to attack - not a broken reporter.

### Run 47/48: the vertex interface the title declares (measured, not guessed)

`WOL_VERTEX_INTERFACE` prints the attribute state the title itself binds, taken from the state object the
runtime already decodes for the draw path (slot, stream, packed attribute word, stream stride):

```
WOL_VERTEX_INTERFACE draw=0 attribs=3 streams=1 s0=on/0/0x22/off0 s1=on/0/0x25/off12 s2=on/0/0x16/off16 stride0=24
WOL_VERTEX_INTERFACE draw=0 attribs=2 streams=1 s0=on/0/0x22/off0 s1=on/0/0x22/off40                             stride0=88
```

Two facts worth keeping: the sprite-shaped draws use **stride 88 (0x58)** with two attributes (offsets 0 and
40), and the earlier assumption that the first pair's attribute reads land on slots 8/9 has to be revisited -
these draws enable slots 0..2 only, so either the SASS attribute-space offsets do not map to slot*16 for this
SDK, or the first draw is not yet the draw that binds programs 233/235. The next measurement correlates the
**bound program ids** with the attribute state per draw, so the pair-to-interface mapping is exact before any
GLSL is wired.

### Run 49: the pair-to-interface correlation, measured

With the bound stage objects now printed next to the attribute state, the mapping is exact:

```
WOL_VERTEX_INTERFACE draw=0 attribs=3 bound=0x1000fc1e68/v266,0x1000fc2ca8/f268 s0=0x22/0 s1=0x25/12 s2=0x16/16 stride=24
WOL_VERTEX_INTERFACE draw=0 attribs=2 bound=0x100103f168/v233,0x100103f298/f235 s0=0x22/0  s1=0x22/40             stride=88
```

So **the first pair (v233/f235) belongs to the two-attribute, stride-88 (0x58) draws**: input slot 0 = FLOAT32x3
at offset 0 (position), input slot 1 = FLOAT32x3 at offset 40. The other draws are different programs
(v266/f268, v189/f191) with RGBA8 and FLOAT32x2 attributes - other Unity variants, not this pair.

This also corrected the attribute-space reading: in this SDK's SASS the **input attribute space starts at
0x80**, so `a[0x80]` is input slot 0 and `a[0x90]` is input slot 1 (the earlier "slots 8/9" was the same
numbers without the base). The decoded `ld`/`st` samples also expose the encoding of that space (byte 0 = the
slot, byte 1's high nibble = the component: `st a[0x70]` = varying 7.x, `st a[0x84]` = varying 8.y), which is
what the remaining undecoded lines will be read with - mechanically, against those five known samples.

### Runs 47-50: the translated pair compiles and links on the device driver

The hand translation of the first pair lives inside the runtime (nvn_shaders.h, `wol_pair_*_glsl`) and a
`WOL_PAIR_CHECK=1` startup check compiles and links it at the first placeholder bind, reporting the driver's
own verdict. That check found a real, otherwise invisible defect and then confirmed the fix:

```
# first attempt
WOL_PAIR_COMPILE stage=vertex ok=1 log=
WOL_PAIR_COMPILE stage=fragment ok=1 log=
WOL_PAIR_COMPILE stage=link ok=0 log=L0001 The fragment array variable c3 does not match the vertex variable c3.
# after declaring the shared array `uniform highp float c3[96]` in the fragment
WOL_PAIR_COMPILE stage=vertex ok=1 log=
WOL_PAIR_COMPILE stage=fragment ok=1 log=
WOL_PAIR_COMPILE stage=link ok=1 log=
```

Both stages compile and the program links on the Mali driver of the device. Nothing is drawn with it yet -
the draw is still the logged placeholder, and that is the next step together with the uniform feed from the
recorded constant bank and the window blit.

### Run 51: the translated pair draws the game's own geometry

With the pair keyed by its bound objects, the draw path no longer skips: the hand translation is compiled
once, the recorded primitive is issued with the measured vertex layout, and the driver reports no error.

```
WOL_PAIR_REALIZE ok=1 program=2 c3=1
WOL_PAIR_DRAW mode=4 count=6 stride=88 stream=67584 c3bank=0/0 avail=0
WOL_PAIR_DRAW_ISSUED primitives=6 glerror=0x0
```

So the chain translate -> realize -> bind -> feed -> draw -> present now runs with **zero GL errors** for the
title's own geometry (6 primitives per sprite quad, stream 67584 bytes, stride 88 as measured).

Two honest gaps keep the frame black, and both are named by the log rather than guessed:

1. `c3bank=0/0 avail=0` - **constant bank 3 is not bound** in the runtime's uniform state for this title, so
   the transform receives zeros (the bind path never ran because the program was never realized). Next: find
   and feed the bank the guest binds.
2. the sampler is not bound yet (`texture-draws=0`), and the frame composition (`WOL_DOWNSAMPLE_PLACEHOLDER`)
   still does not blit to the window.

The present line stays honest: `NVN_PRESENT_PIXELS frame=1 nonblack=0 status=BLACK-SAMPLE`.

### Runs 52-61: constants, sampler, the resolve blit - and the frame census

Four measured findings, each from a device run:

1. **Constant banks.** The binds are applied by `nvn_render_record`, but the shader's `c3` is not bank 3 at
   bind time: the title binds stage 0 at index 0 (144 bytes) and stage 1 at index 0 (16 bytes). Feeding the
   vertex bank to both stages made the fragment read the vertex matrix; the stage-1 bank measures `1,1,1,1`,
   which is the sprite tint. The hook now discovers the slots and feeds each stage its own bank.
2. **Sampler.** The sprite sampler asks for behaviour the adapter refuses (`anisotropy=9` on id 52). It is
   now admitted once with the exact values printed - the same shape as the Animal Well precedent.
3. **The resolve is a GPU blit.** The title's camera target lives in a GL texture and its guest storage
   mirror stays empty (a CPU census through the mirror read zero after real draws), so a CPU copy can only
   resolve zeros. `wol_downsample_copy` is now a real blit: destination texture bound as a framebuffer,
   source texture sampled through the driver, the previous binding restored afterwards. `glerror=0x0`.
4. **The frame census.** The blit's read-back census of the camera target measures `src-nonblack=0`: the
   translated pair is a *consumer* of the camera image (it samples a camera-sized texture), while the draws
   that *produce* that image are still placeholders. The pair-to-draw census of the first frames is:

| vertex | fragment | draws | path |
|--------|----------|-------|------|
| 0x100103f168 | 0x100103f298 | 66 | translated (this pair) |
| 0x100103d158 | 0x100103d288 | 4 | placeholder |
| 0x1000fc2b78 | 0x1000fc2ca8 | 2 | placeholder |

**The whole frame is drawn with three program pairs.** Translating the remaining two covers every draw of
the frame, which is the concrete path to a picture: the machinery (space rule, interface log, pair hook,
bank feed, blit) is in place and each new pair is a mechanical repetition of the first one.

### Runs 62-65: shader identity by address, the pair blobs, and what the boot frames really contain

- The capture log now carries `code-address`/`control-address` on both the inventory and the stage lines,
  so a program object joins to its code/control hashes directly (the log interleaves lines from several
  threads, so the join strips the interleaved `IPC` fragments first). The blobs of the two remaining pairs
  were fetched by content hash and verified: v189/v266 share one vertex code (`d88c64a6`, 1024 B, two
  different controls), f191 is 512 B and f268 is 1024 B.
- Space maps decoded with the validated rule: the shared vertex reads **three** input attributes (slot 0 all
  four components, slot 1 all four - the RGBA8 colour, slot 2 two) and writes four varyings (7 = the clip
  position, 8 = colour.rgb + position.w, 9 = the second attribute, 10 = the raw position). This matches the
  measured stride-24 layout (12 + 4 + 8) exactly.
- The boot frames were censused per frame: the camera target is black at frames 30, 33 and 41 as well, and
  the live texture table at that time holds only default fills (4x4, 16x16, 256x2, 64x64 with no pixels) -
  **the title has no sprite textures uploaded yet**. A black frame in the first ~40 frames is the game's own
  boot behaviour, not only a translation gap.
- The per-frame pace is limited by the memory floor (42 frames at the 64 MiB floor) and by the diagnostic
  volume; the long run that follows uses a 32 MiB floor and a 900 s budget to see how far the boot gets.
