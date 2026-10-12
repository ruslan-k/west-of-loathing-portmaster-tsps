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
