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

### Run 66: the pipeline runs 120 frames and the title's own black-frame guard stops it

With the diagnostic memory floor at 32 MiB and a 900 s budget the run went to **120 presented frames** and then
stopped on `NVN_PRESENT_BLACK` (the runtime refuses to keep presenting black frames - detail 0x78 = exactly the
120th). Not memory, not a crash: the title's frames are still black, and that is now the single remaining
question, with two named causes:

1. the ~40 boot frames are black in the game itself (no sprite textures are uploaded yet - measured), and
2. only one of the frame's three program pairs is translated; the other two still draw nothing.

The two remaining pairs are prepared for translation: their code and control blobs are fetched and
hash-verified in the private workspace (`v189`/`v266` share vertex code `d88c64a6`, fragments `f191` and
`f268`), and the shared vertex pair's space map is decoded (three inputs of 12+4+8 bytes matching the
measured stride 24, four varyings with varying 7 as the clip position).

### Run 67: the black-present bound lifted, and the next real constraint appears

`COTM_BLACK_LIMIT` (default 120, a diagnostic bound rather than a release rule) was raised to 4000 for a
bounded long run with the memory floor at 32 MiB. The result is a precise picture of where the boot stands:

- **147 frames** presented (up from 120), all still black; memory stayed healthy (available 63 MiB at the
  worst against the 32 MiB floor, VmRSS 721 MiB), so neither memory nor the black bound was the ceiling.
- The run then stopped on a **new guard: `NVN_COMMAND_ARENA_OVERLAP`** (a guest address in the detail):
  during the boot the title's command buffers grow past the arena the runtime recorded, and the arena
  guard refuses. That is a runtime-side constraint to solve next - it is what now stands between the boot
  and the point where the title uploads its atlases and draws its first visible frame.
- The per-frame census had already used its budget by frame 49, so the later frames still have no census;
  the census cap needs re-arming (frame-keyed, larger cap) with the next run.

### Run 68: the arena relaxation did not fire, and the frame-145 census settles the question

- The arena overlap stop persists (same guard, a fresh guest address). The acceptance added in this run did
  **not** trigger (`WOL_COMMAND_ARENA_RESIZE` absent), so the path taken is not the one relaxed - the other
  arena site (`t2_command_arena_transfer`, nvn_commands.h:326) or a registration whose entry is already
  `used`/part of a live list. Next: log which site refuses and which flag blocks acceptance, then relax the
  right one (both sites carry the same message and the stop does not name its call site).
- The census now reaches frame 145 and reports `src=30 src-nonblack=0` with **no** live texture ever chosen:
  at frame 145 the title still has no content-bearing texture of its own. Together with the arena stop this
  says the boot is looping in a black state rather than progressing through its load, and that the draws it
  would use to show progress are the untranslated pairs.

## Status (latest measured run)

| Subsystem | State |
|-----------|-------|
| ARM64 / IL2CPP guest | runs on the device |
| Horizon SVC / IPC | game runtime reached |
| Mali-G57 / EGL context | created and used |
| NVN command record + replay | works; 146-147 consecutive presents |
| Command arenas | **unused-tail overlap solved with evidence** (see below) |
| GLSL ES translation | 1 of 3 frame pairs; compiles, links and draws with zero GL errors |
| Render targets | real GPU blit 1920x1080 -> 1280x720 |
| Present | 146-147 frames, all still black |
| Current stop | `NVN_GUEST_POINTER` in the game's own code (`main.text.seg+0xaf4684`, detail 0x0) |

### Command arena: what was measured

```
WOL_ARENA_OVERLAP owner=0x1000a7f010 pool=... old=0x107595c000 old_size=2097152 old_used=2097088
                 limit=2097152 new=0x1075b5bfc0 new_size=2083008 overlap=64 current=0 recording=1
                 generation=2 safe_end=0x1075b5bfc0 classification=UNUSED_TAIL
WOL_COMMAND_ARENA_RETIRE ... action=RETIRED_TAIL
```

The previous arena's `used` cursor ends exactly where the new arena begins, and no retained range or live
list reaches into the overlap, so the tail is retired and the new arena is registered. Everything else stays
fail-closed with the original `NVN_COMMAND_ARENA_OVERLAP`.

### The stop after the arena fix: a corrupted stack pointer, not a contract violation

Run 71 passes the arena step (evidence above) and then stops at
`NVN_GUEST_POINTER pc=main.text.seg+0xaf4684 detail=0x0`. The guest frame trace and a disassembly of that
address pin it down exactly:

```
GUEST_FRAMES lr=sdk.text.seg+0x8f52c <- sdk.text.seg+0x8b5e4 <- sdk.text.seg+0x894b0
             <- main.text.seg+0x13a4b94 <- sdk.text.seg+0x686a8 <- rtld.text.seg+0xac

main.text.seg+0xaf4670:
  af4670  csel x3, x10, xzr, ne
  af4674  mov  x2, sp        ; the caller passes its own stack pointer as an argument
  af4678  mov  x0, x8
  af467c  mov  x5, xzr
  af4680  blr  x9            ; call through the guest function pointer
  af4684  ldp  x29, x30, [sp, #64]   <-- fault, address 0x0 (sp no longer points at this frame)
  af4688  add  sp, sp, #0x50
  af468c  ret
```

So the game calls through a function pointer while handing over its own stack pointer, and the frame restore
after the call reads address 0. No guest signal is delivered around it (the log has none), so this is a
**guest stack switch** - a fiber/coroutine-style helper - whose continuation returns to the original frame
with a different stack pointer. The next diagnostic axis is therefore the bridge's handling of a guest stack
switch inside a callback: does the guest stack pointer survive `cotm_nvn_call_original`, and what does the
runtime do when the guest changes `sp` inside a nested call? That question is measured before anything is
changed, as with every other blocker in this project.

**Correction (runs 90-91, measured):** the reading above is wrong. `NVN_GUEST_POINTER` reports
`nvn_caller = f->lr` - the *return address* of the NVN call - as its `pc`, and the rejected pointer as its
`detail` (here 0x0). The instrumented run 90 resolved the rejection to this runtime's own diagnostic vtable
probe inside the command-memory callback path (see "Runs 90-91" below). The game's stack switching is not
involved and no guest signal or frame corruption exists at that address.

### A/B: the guest stack-switch stop is independent of the arena handling

`WOL_ARENA_KEEP_OLD=1` accepts the new arena **without** trimming the old entry (the old range stays
accounted, the new one is added beside it):

```
WOL_COMMAND_ARENA_DUP old=0x107595c000/2097152 kept=1 new=0x1075b5bfc0/2083008
STOP status=NVN_GUEST_POINTER pc=main.text.seg+0xaf4684 detail=0x0
```

Same frames (146), same stop, same guest address as the retired-tail run. So the later fault has nothing to
do with the arena fix; the arena acceptance is sound in both shapes and the default (retired tail, evidence
logged) stays. The stack-switch fault is a guest-side path, and the next diagnostic axis is what the host
environment makes of the guest's own stack switch - or, equally likely, the title's state machine reaching a
guard path because its draws still produce nothing (the two untranslated pairs).

**Correction (runs 90-91, measured):** neither candidate axis was the cause. The stop was produced by this
runtime's own diagnostic vtable probe inside the command-memory callback path; it is fixed and the run now
proceeds past it (600 frames, see "Runs 90-91").

Runs 71/72 end clean, no CPU_FAULT, device restored to the menu.

### Runs 90-91: the stop named by measurement - and it was the runtime's own probe

Review-driven instrumentation (P0), behaviour-preserving:

- `nvn_bridge.h` keeps the innermost NVN id, its eight arguments, the guest frame LR and SP per thread and
  threads them through nested dispatches;
- `nvn_pointer.h` prints `NVN_POINTER_REJECT` (address, size, permissions, current NVN function, all eight
  arguments, caller, thread, depth) plus a frame-pointer host backtrace before the stop;
- `nvn_command_callback.h` marks the callback boundary (`T2P_CB_CALL_BEGIN/END`).

Run 90 reproduced the identical stop and named its exact cause:

```
NVN_POINTER_REJECT address=0x0 size=0x30 perm=0x1 nvn=nvnCommandBufferSetRenderTargets id=0xa1
  caller=main.text.seg+0xaf4684 frame-lr=main.text.seg+0xaf4684 frame-sp=0x6cfa68d0
  a0x0=0x1000a7f010 a0x1=0x1 a0x2=0x6cfa68d0 a0x3=0x0 a0x4=0x1000a2cab8 a0x5=0x0 a0x6=0x0 a0x7=0x0
  thread=0x5 depth=0x1 context=-
  host-frame 1 from-stop=0x2a2c raw=0x55613dc8e4
```

Resolved with `addr2line` against the exact build, the host backtrace reads: `nvn_pointer <-
nvn_command_request_memory <- nvn_command_emit <- nvn_command_record_inner <- nvn_command_record <-
nvn_command_dispatch_locked <- cotm_nvn_dispatch <- cotm_nvn_entry`. The rejected read (`size=0x30`,
read) is the `T2P_CMDMEM_CALLBACK_TARGET` probe dereferencing word 0 of the title's callback object as a
vtable pointer; for West of Loathing that word is zero (the callback data equals the command-buffer object
address), so the probe - a diagnostic kept from the upstream lineage - fail-closed the run. The recorder
itself was healthy: the callback refilled memory (`generation 2 -> 3`) and the retired-tail arena acceptance
had already passed.

The fix guards the probe only: the second read runs only when word 0 is non-zero (a zero prints as
`vtable=0x0 slot4=none`). No pointer validation was weakened; every other rejection stays fail-closed.

Run 91 with the guard in place:

- presents **600 frames** (up from 146) and passes the previous stop region with no guest fault and no GL error;
- the title reads its asset bundles through RomFS, including the **191.088 MiB core** (`offset=0x4630d0
  size=0xbf15cfc`) and an 11.6 MiB companion, and creates **33 real textures** (1920x1080 / 1280x720 targets
  and small engine fills); no further texture is created in the measured log after the early frames;
- all 600 frames are still black; the run ends on the diagnostic memory floor
  (`T2_MEMORY_FLOOR available-MiB=31 floor-MiB=32`, VmRSS 712 MiB, swap ~462 MiB used), not on a game stop.

The next gates are unchanged: translate the two remaining program pairs (v189/v266 share vertex code
`d88c64a6`; fragments `f191`, `f268`) and explain the black state the title stays in after its initial reads.

### Decode progress on the two remaining pairs (private workspace evidence)

Both fragments were disassembled with the same toolchain as the first pair. Their structure, statement by
statement, is now known well enough to author the GLSL:

- **f191 (512 B)**: six `ipa` interpolant loads (r0, r1, r5, r6, r7, r8), one `texs` sample, then a chain of
  `fsetp`/`fadd`/`lop3`/`fmul` comparisons and multiplies, ending in `exit` - a tinted sprite with one
  conditional term. No `kil`, so it draws everywhere it is asked to.
- **f268 (1024 B)**: `ipa` loads, `fsetp`/`sel` select chains, `fmul`/`fadd`, **two** texture samples (a
  second TEX-family control word), `mov`/`iadd`/`lop3` and an **alpha `kil` discard** - the text/UI
  signature, consistent with the `g[]` global reads seen earlier.
- The shared vertex (`d88c64a6`, used with two control sections) reads three inputs sized 12 + 4 + 8 = the
  measured stride 24, and writes varyings 7 (clip position), 8 (colour.rgb + position.w), 9 and 10.

What is still missing before the GLSL can be written is the exact varying offset of each `ipa` operand (the
disassembler's operand text is not readable for those lines yet); that is the next mechanical decode step,
after which the pair is wired through the same hook as the first one.

### Runs 93-97: shader identity catalogue + diagnostic draws (2026-10-13 review, iteration 1)

The draw hook no longer matches fixed guest addresses: draws substitute translated GLSL by measured
**code SHA-256 + control SHA-256 identity** (`WOL_SHADER_MATCH` / `WOL_CAT_LINK` / `WOL_CAT_DRAW`),
and untranslated pairs draw an explicitly-marked TEST diagnostic output. What was measured:

- **Identity catalogue works on the device.** All six captured stage identities are recognised from the
  live bound objects: `f309b86a#0184`, `f08bad2f#a9b0` (and the `c3200708` variant), `v189(d88c64a6)`,
  `v266(d88c64a6)`, `f191-diag`, `f268-diag`. The measured **drawing pair is `f309b86a + f08bad2f`**
  (objects 0x100103f168 / 0x100103f298); `d88c64a6` belongs to the second pair. Same code with a
  different control section is a separate catalogue entry with its own measured hashes.
- **Draws execute.** `f309b86a#0184 + f08bad2f#a9b0` link as a real translation: 639
  `WOL_PAIR_DRAW_ISSUED`, glerror 0x0, target 32/1920x1080. `f191` and `f268` link as TEST fullscreen
  diagnostics (vertex `d88c64a6` is not translated yet): 852 `WOL_CAT_FULLSCREEN_DRAW`, glerror 0x0,
  target 280/1280x720 - every line marked `note=TEST-ONLY / not-a-translation`.
- **Presentation is still black** (run 97: 213/213 samples `nonblack=0`) and the run stops at a new
  gate: `NVN_TEXTURE_SWIZZLE_REQUIRED` (format 0x39) in the scene phase
  (`pc=main.text.seg+0xaf64a0`). The gate now logs `WOL_SWIZZLE_GATE format=... swizzle=... dims` for
  the next iteration.
- **Boot heartbeat** (`WOL_BOOT_TICK`, every 60 frames): after the initial load (25 RomFS reads /
  216 MB, 33 real textures) reads, textures, draws and thread count all freeze - the title is not
  progressing on its own after the bundles; longer runs need memory work, not more frames.
- **Downsample trace** (`WOL_DOWNSAMPLE_UNRESOLVED`, target=269): the destination is the live
  1920x1080 target (format 0x25); 33 live textures, 21 same-format, none "larger" - the current
  larger-source heuristic cannot resolve this operation; it needs its own decode.
- Diagnostic runs may raise the harness floor override (`WOL_TEST_FLOOR=26`) so the replay survives
  into the scene phase; the launcher default stays conservative (140 MiB).

Hades (the review's variant B) is parked with a precise answer: the earlier "suspicious AL2P"
classifications are an artifact of the vendored decode table - empty lookup slots return
`Opcode(0)=AL2P` for any instruction missing from the table, so four "missing opcodes" were being
counted on top of a mis-decode. Details and the partial smoke-test results are in
`docs/shader-draft/hades-evaluation.md`.

### Runs 99-100: the swizzle gate measured and resolved

Run 99 named the stop exactly: `WOL_SWIZZLE_GATE format=0x39 swizzle=4,3,2,5 256x256 levels=9
target=1 flags=0x0 caller=0x8afb4a0` - an NVIDIA A4B4G4R4 image whose guest swizzle exchanges B and
R (B,G,R,A). The format already had a decoder and upload path; what was missing was (a) the
capability gate accepting 0x39 with any per-channel choice and (b) the decode applying the guest
swizzle instead of assuming identity. Both are now implemented (`nvn_texture_formats.h`).

Run 100 (device-78) did not stop at all: the harness time governor terminated it while the title
was still loading (exit status 143). Measured: textures 33 -> 108 real textures (the boot heartbeat
shows the loading ADVANCING after the fix, not frozen), 763 translated pair draws + 1016 TEST
fullscreen draws, draws into the scene targets 30/31/269/280, no swizzle gate rejections. The
presented frames are still black (254/254 samples) with the loading unfinished at the budget end.

Next gates: give the title a longer bounded budget and watch the heartbeat until the load settles
(menu reachability), transcribe f191/f268 (variant A) to replace the TEST diagnostic pairs, and
decode the still-unresolved `target=269` operation (33 -> 110 live textures, 39 same-format, none
"larger" - the current heuristic cannot resolve it).

### Runs 101-102: longer budget, and where the time actually goes

Run 101 was rejected by the runtime's own validation (`INVALID_PROBE_TIME_BUDGET`, detail 0x708):
the diagnostic cap was 900 s. The cap is now deliberately raised to 1800 s (loader.c, with the
memory floor as the active guard).

Run 102 (device-79, 1800 s): **no stop** - the time governor ended it. The load kept advancing,
slowly: real textures 33 -> 108 (frame 240 tick) -> 124 total, including R8 256x256 glyph/font
textures (the title is past the first bundles); all three pairs draw (the second pair's
`v189/v266 + f191/f268-diag` draws are now active alongside the translated first pair). ~279
present samples, still black. Frame periods at the end are ~86 ms with long non-present stretches,
and the log ends in a repeating IPC poll loop (`handle=0x42e endpoint=0x3f command=0x7/0x8`) with
texture creation interleaved - the title is waiting/polling on a service, not crashed.

Next: identify what the `0x42e/0x3f` wait expects; slim the readback diagnostics out of the hot
path (review P1) so an hour-scale observation runs at real speed; continue the f191/f268
transcription (variant A).

### Runs 103-105: quiet hot path, the dump-file leak, and the HID stop (2026-10-13 second review)

Working the second review (P0: pixel route target->window texture->present; P0: hot-path
diagnostics; P0: downsample; P1: shaders):

- **Quiet hot path (`WOL_QUIET=1`, review P1)**: the per-draw texture content probes (full
  GPU->CPU readbacks while selecting sprite candidates and the periodic live-texture scan) are now
  env-gated. Measured effect: the same 1800 s budget presented **924 frames vs 279** in run 102 -
  the diagnostics were throttling the title as the review suspected.
- **Port hygiene: the diagnostic captures leaked.** Runs had accumulated **14 736 files** in the
  port directory; one quiet run then died at `NVN_CAPTURE_OPEN` with errno 28 (ENOSPC). Device
  cleaned (files + 49 per-run receipt directories; only the 18 real port files remain, 4.9 GB free).
  Every capture path (shader dumps, frame images, the per-frame receipt journal) now requires an
  explicit `WOL_DUMP=1`; normal runs write nothing.
- **New frontier: HID command 128.** With the quiet run the title reached frame ~900+ and stopped
  at `UNIMPLEMENTED_IPC_COMMAND` on `endpoint=0x2d (HID) command=0x80`. Per libnx, 128 =
  `SetNpadHandheldActivationMode` (u64 ARUID@0, u64 mode@8); commands 123/125/126/127/128/129
  (assignment single/merge, LR assignment, handheld mode set/get) are now implemented in
  `input.h`; the getter returns the stored 0-2 mode the SDK requires.
- **Pixel-route instrumentation (review P0 #1)**: `WOL_WINDOW_TEXTURE` names every swapchain window
  texture at creation; `WOL_PRESENT_SOURCE` names the texture actually presented each frame (guest
  address, GL name, id, dims); `WOL_PRESENT_TEST=1` writes a magenta 64x64 marker directly into the
  presenting texture (TEST-ONLY) so one run proves or breaks the whole target->window-texture->
  present->screen chain; `WOL_BLIT_CENSUS` already reports per-frame pixel counts at the blit.
- **Boot heartbeat fix**: the catalogue draw paths now increment `nvn_replay.draws`, so
  `WOL_BOOT_TICK draws=` reflects real draw calls (was always 0 on the experimental hook).

### Run 106: the pixel route is proven, and two quiet-mode faults found

- **HID unlocked**: with 123-129 implemented the title no longer stops at command 128; the run's
  only end was the diagnostic memory floor (`available 25 MiB vs floor 26`) at frame ~163.
- **Route proven end to end (review P0)**: `WOL_WINDOW_TEXTURE` shows the swapchain is textures
  1/2/3 = ids 30/31/32, all 1920x1080; `WOL_PRESENT_SOURCE` shows the present quad samples exactly
  those textures (rotating per frame). With `WOL_PRESENT_TEST=1` the magenta 64x64 marker written
  directly into each presenting texture appeared as **nonblack=4096 in all 163 present readback
  samples** - the render-target -> window-texture -> present -> readback chain works.
- **Fault 1 (fixed)**: under `WOL_QUIET=1` the translated pair drew with NO texture bound
  (`WOL_PAIR_TEX none=1`), so it painted black by design into the scene targets; quiet mode now
  binds the first non-null candidate handle without content readbacks.
- **Fault 2 (fixed)**: the Downsample record was clobbered by the generic payload overwrite (the
  payload became the first 16 bytes of view A instead of the two object words), which is why the
  replay probed view bytes as texture objects and the target=269 operation stayed unresolved. The
  record now keeps the two raw view pointers and the replay decodes the texture object inside each
  36-byte view (word scan against the live registry, offsets logged).
- **Memory is the endurance blocker** (review section 5): the run died at the floor with RSS
  ~742 MiB while the load was still advancing. The next diagnostic run lowers the harness floor to
  20 MiB (bounded, self-guarding) to observe how far the loading gets past frame 163.

### Run 107: the endurance run survives the full budget

With the harness floor at 20 MiB the title ran the entire 1800 s budget with **no stop** (governor
SIGTERM at the end): 420 presented frames (run 106: 163), real textures 33 -> 100 -> 128 -> 144
(sprite atlases arriving, e.g. 2048x1024 with 12 mip levels), draws counter live (420/840/...).
Two follow-ups found in this run:

- `WOL_PRESENT_TEST` is a value-check now (`=1`); the presence-based check meant the harness value
  `0` still enabled the marker, so run 107's present readbacks measured the marker again
  (nonblack=4096) instead of game content.
- The downsample view decode must read the views at RECORDING time: replay-side guest reads found
  nothing (the command arena is recycled by replay time, measured). The record now copies both
  36-byte views (payload 72 bytes) and the replay scans only the recorded bytes for registered
  texture objects.

Also fixed here: a leftover duplicated `if(!src||!dst)` and stray return in `wol_downsample_copy`
from the earlier trace edit.

### Run 108: honest content readback and the pair-draw question

With the marker genuinely off (`=1` value check) all 433 present readbacks are black again - the
title's own content does not reach the presented window textures 30/31/32 yet. Measured layout of
this run's draws: the translated pair issues ~1 draw per frame into each of 30/31/32
(145/144/144 = 433, one per present) plus most of its draws into 280/269/457. The downsample view
words now decode to `0x0000010d_d4f5544d` / `0x0000010e_d4f5544d` - the high halves are texture
ids 269/270; the view scanner gained an id-based lookup for that measured flavour (the low word
0xd4f5544d is a constant tag). Two faults of the quiet texture path were also confirmed fixed
(`WOL_PAIR_TEX quiet-slot=0` binds a real sampler handle).

Next instrumentation sent with run 109: `WOL_PAIR_TEST=1` paints the translated pair solid green
while keeping its real vertex - if the green reaches the presented texture, geometry and target
routing are fine and the remaining problem is texture/sampling; if not, the pair's geometry or
render-target attachment is the break.

### Run 109: view decode lands, the pair's geometry question narrows

- **Downsample views decoded**: `WOL_DOWNSAMPLE_VIEW a=texture(id=269) b=texture(id=270)` and
  `a=280 b=281` - the id-based lookup (high half of the view word) resolves both flavours, and
  **UNRESOLVED is now 0** for the whole run (was 433/run). The resolve blits now use decoded
  objects instead of the size heuristic.
- 977 presented frames (best yet), full 1800 s budget, no stop, 130 textures including a
  2048x2048 format-0x39 atlas (the swizzle gate accepts the big one).
- **Green pair test answered the texture question**: with the translated pair painted solid green
  (real vertex kept), all 977 present readbacks stayed black - so the pair's geometry or its
  render-target attachment is the break, not texture sampling. Run 110 therefore carries
  `WOL_PAIR_MATH=1`: the exact translated transform is replicated on the CPU per vertex and the
  clip-space result is printed, to tell an off-screen/clipped quad or a wrong constant bank from
  an attachment problem.
- Quiet texture pick upgraded from "first non-null" to metadata-based (largest level-1 texture
  that is not the current target) - no readbacks, closer to the probe-selected atlas.

### Run 110: the pair is clipped off-screen - the constant bank question sharpens

`WOL_PAIR_MATH` (CPU replication of the translated vertex transform, per vertex) answered run 109's
open question precisely: every vertex of the pair's quad comes out with **clip.w = -0.98 - a
negative homogeneous coordinate - so the hardware clips the whole triangle** (which is why a
solid-green fragment produced no pixels). The clip results are constant across the quad
(x = 0.98 + 1.0*px, y = 0, z ~ 0.98, w = -0.98), so the fed c3 bank is not the matrix the original
code multiplies with. The 144-byte bound range matches c3's read extent, so run 111 dumps the
actual floats: the full 36-word c3 bank (and the fragment bank) on the first draws, plus every
bound stage-0 slot with its first words - then the matrix can be identified offline by arithmetic
and the hand GLSL (or the bank choice) corrected 1:1. 210 presents, no stop, 144 textures.

### Run 111: the constant bank is two GL column-major matrices - the hand math is corrected

The bank dump settled it. c3[0..15] is an identity matrix and c3[16..31] is
`[2,0,0,0, 0,2,0,0, 0,0,-0.019802,0, -1,-1,-0.980198,1]` - **both in GL column-major order**, i.e.
the clip position is `M2 * (M1 * pos)` and for this draw equals `(2x-1, 2y-1, -0.98-0.0198z, 1)`:
a unit quad projected to the full viewport with **w = 1**. The earlier verbatim ALU transcription
of the vertex shader mixed the row/column roles (its last combination read `-0.98` into w), which
is exactly why every vertex came out with clip.w = -0.98 and the hardware clipped the quad away.

The hand vertex GLSL is now the honest two-matrix column-major transform (M1 at c3[0..15], M2 at
c3[16..31]), the CPU probe replicates the same math, and the same GLSL/register roles stay for the
varyings (v8 = (a_extra.x*c3[32]+c3[34], a_pos.z), v7 = gl_Position). Run 112 carries the fix with
the green fragment still on: if the unit quad now paints the window textures, the presentation
readback turns green and the geometry chapter is closed.

### Run 112: the quad is geometrically correct - the loss is now downstream of the draw

The fixed transform verified on the device: `WOL_PAIR_MATH v=0..3 clip=-1,-1 .. 1,1, z=-0.982,
w=1` - the unit quad exactly fills the viewport, still with the green fragment. But the run's 198
present readbacks are all black, while the pair issued 594 draws, one per frame into each window
texture (66/66/66 into 30/31/32). The draw therefore executes with correct clip coordinates and
the pixels still do not survive to the presentation sample. Run 113 adds the decisive probe:
immediately after each pair draw into a window texture, a center-pixel readback of the bound
target plus the render state that could swallow it (scissor box + enable, depth test + func,
viewport, FBO binding). If the center pixel is green at draw time, the loss is between the target
and the present (clear/ordering/binding); if it is black, the draw itself is being discarded.

### Run 113: the draw executes but its own target stays black

`WOL_PAIR_PIXELS` on every window-texture draw: `vp=0,0,1280,720 scissor=0 depth=0 fbo bound,
center = 0,0,0,0` - with the draw executing (glerror 0) and no scissor/depth interference, the
center pixel of the draw's own bound target is black immediately afterwards. So the primitives
produce no fragments at all, despite the verified clip coordinates. Run 114 bisects this with
`WOL_VS_TRIVIAL=1`: a matrix-free pass-through vertex (`gl_Position=(2x-1, 2y-1, 0, 1)`, no c3
uniform read at all) with the same green fragment and a five-point readback (center + four
corners). Green with the trivial vertex = the c3 data path at draw time is the fault; still black
= the draw plumbing itself (attributes/FBO attachment/program realization).

### Run 114: the bisection lands on the attribute plumbing - guest pointers feed the GPU nothing

With `WOL_VS_TRIVIAL=1` (matrix-free pass-through vertex, green fragment) all five readback points
are still 0,0,0,0. The c3 data path is NOT the fault; the difference that remains is the attribute
source. The fullscreen diagnostics - the only path that has ever left pixels (census 925 in target
280) - read from a **real GL buffer**, while the pair draw pointed the attributes **straight at
guest memory**. Hypothesis (run 115 carries the fix): the GPU fetch from those raw guest pointers
yields zeros, collapsing the quad to a single point (hence no fragments, clean glerror, and no
pixels anywhere - not even in 280/269). The pair draw now uploads the guest vertex bytes into a
stream VBO (`glBufferData` from the copied bytes) and reads the attributes from it - the same
mechanism the working fullscreen draw uses; the old direct-pointer path stays behind
`WOL_PAIR_DIRECT=1` for the A/B. Also staged: `WOL_PAIR_STATE` (color mask + blend) in case the
first fix is not sufficient.
