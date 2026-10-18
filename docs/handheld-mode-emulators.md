# Handheld-only Horizon mode — cross-emulator source audit

Reviewed: 2026-10-18. Applies to the owner-specific `West of Loathing` Switch ARM64/Unity runtime targeting TrimUI Smart Pro S. Follow [roadmap §13](optimization-roadmap.md#13-m7-permanently-handheld-horizon-profile-no-tv-mode--no-switch).

## Non-negotiable product requirement

**The only guest Switch operation mode is Handheld (`0`).** The default guest display resolution is **1280 × 720** through the corresponding applet interface. There is **no TV/docked option** in the game launcher, runtime flags, UI or Horizon state machine. Comparing a pre-change build to a fixed-handheld build is acceptable for development; exposing mode selection in either build is not required.

This requirement does not force every internal Unity render texture to be 720p; its current rendering still includes 1920×1080 NVN camera/intermediate targets. Also, it must not modify the unrelated Npad handheld *activation mode* (HID cmd 128/129).

## Independent source comparisons

### Ryujinx — common state getter and APM separation

Source: [`ICommonStateGetter.cs`](https://github.com/kotx/Ryujinx/blob/534f92506bf8c6aba29bb86917bf10954a360d8e/src/Ryujinx.HLE/HOS/Services/Am/AppletAE/AllSystemAppletProxiesService/SystemAppletProxy/ICommonStateGetter.cs)

- Command 5 `GetOperationMode()` reads shared `State.DockedMode` and writes **one byte**: `OperationMode.Docked` or `OperationMode.Handheld`.
- Command 6 `GetPerformanceMode()` is delegated to APM, **not** returned by reusing the u8 operation-mode payload.
- Command 60 `GetDefaultDisplayResolution()` writes **two u32s** from the queried display information; Ryujinx does **not** unconditionally return 1280×720 in this implementation.
- Commands 0/1 and 61 handle message/event state and default-display-resolution notifications.

**Lesson for WoL:** preserve the correctly sized reply structures and coherent focus/event handling. Replace the setting-dependent operation-mode policy with one immutable handheld result, but do not copy Ryujinx's display/host info API into GLES.

### Skyline — explicit handheld resolution in AM service

Source: [`ICommonStateGetter.cpp`](https://github.com/msummers10/skyline/blob/master/app/src/main/cpp/skyline/services/am/controller/ICommonStateGetter.cpp) and [service header](https://github.com/msummers10/skyline/blob/master/app/src/main/cpp/skyline/services/am/controller/ICommonStateGetter.h).

- Constructor initializes `operationMode` from app settings.
- Command 5 returns the stored operation mode (`Handheld = 0`, `Docked = 1`).
- Command 6 returns a u32 performance-mode value from the operation mode (Skyline-specific simplification).
- Command 60 returns `1280,720` for handheld, `1920,1080` for docked.
- Message/notification logic is a separate queue; the constructor queues an initial focus-state message, not an obligatory dock-state change.

**Lesson for WoL:** implement fixed handheld `0` and `1280,720` at a single AM state-service boundary and keep events intact. Do **not** import the configurable `operationMode` or docked branch.

### ScarletNX — minimal C/Horizon HLE implementation

Source: [`src/nx/hle/services/am.c`](https://github.com/scarletnx/ScarletNX/blob/main/src/nx/hle/services/am.c), [`am.swipc`](https://github.com/scarletnx/ScarletNX/blob/main/src/nx/hle/services/am.swipc).

- `nn_am_service_ICommonStateGetter_GetOperationMode` assigns `*mode = g_opt_docked ? 1 : 0` (`u8`).
- `GetDefaultDisplayResolution` assigns `*width = g_opt_docked ? 1920 : 1280` and `*height = g_opt_docked ? 1080 : 720` (two 32-bit fields).
- `GetPerformanceMode` has a separate `u32` reply, implemented from the docked option.
- Change-event and applet-message behavior are separate from these getters.

**Lesson for WoL:** ScarletNX's simple C service is the closest architectural reference. Replace its configurable ternary with constant `0` and `1280,720` after verifying the reconstructed Horizon runtime's own IPC structures.

### Historical yuzu and ReverseNX: how games discover mode

- An [older yuzu AM change](https://ni.4a.si/anonymous/yuzu/commit/?id=a5e9745380bf9e247d34c42009cd9eb66f4e97a8) linked `GetOperationMode` and `GetPerformanceMode` to its `use_docked_mode` setting. This is historical evidence of the API contract, not a recommendation to add such a setting.
- [ReverseNX hooks](https://github.com/masagrator/SaltyNX/blob/master/saltysd_core/source/ReverseNX.cpp) intercept `nn::oe::GetOperationMode`, `GetPerformanceMode`, `GetDefaultDisplayResolution` and change notification paths. Some games discover the mode indirectly through default resolution rather than the operation-mode value alone.

**Lesson for WoL:** only changing the visible window or `vi` `ListDisplays` maximum layer dimensions is insufficient to establish handheld mode. Match the actual `nn::oe`/AM getter chain used by this Unity SDK.

## Suggested WoL target behavior (conceptual, NOT a pasted implementation)

| Horizon-visible interface | Always-on response | Validation gate |
| --- | --- | --- |
| `ICommonStateGetter::GetOperationMode` (cmd 5) | `u8 = 0` | Correct CMIF/domain endpoint and u8 output |
| `ICommonStateGetter::GetDefaultDisplayResolution` (cmd 60) | `u32 width = 1280; u32 height = 720` | Correct command version, IPC result layout and output sizes |
| `ICommonStateGetter::GetPerformanceMode` (cmd 6) | Handheld-compatible APM profile | Verify the distinct u32 APM enum; do not infer CPU/GPU Linux clocks |
| `ICommonStateGetter` message/event handlers | Normal initial/focus messages and valid handles, **no dock/undock changes** | Avoid fake transitions and spurious resolution events |
| `vi` layer maximum / SDL/KMSDRM output | Existing supported max layer descriptor; output stays 1280×720 | Capability limit is not proof of mode |
| HID Npad handheld activation commands 128/129 | Existing independent controller semantics | Do not wire into Switch OperationMode |
| Other `omm` or SDK mode endpoints | Add only if actual guest trace confirms usage | ABI/firmware/version-specific; do not invent a service |

### Implementation order

1. Inspect the original manifest-pinned upstream GPL service dispatch, not only `runtime/wol-adapter.patch`, because the patch has no explicit AM/oe OperationMode override and the inherited service may already answer handheld.
2. Capture only bounded read-only startup/Unity-init traces of the values genuinely returned to the game. This tracing can use `WOL_MODE_TRACE=1` since it is **diagnostic logging only**; there must be **no runtime mode selection flag**.
3. If the inherited responses already equal `0` / `1280,720`, leave rendering behavior unchanged and enforce them with data-free tests. Otherwise implement immutable handheld replies on the observed, version-correct AM/oe service path.
4. Test A/B with *different pinned builds*, not `auto|docked` variants. Record actual `NVN_TEXTURE_REAL` RT dimensions, host KMS 1280×720, GPU commit, PSS/SwapPSS, frame P50/P95/P99 and scenes with map/stencil/characters. Restore the accepted build if regressions occur.
5. If guest-reported handheld and default-resolution 720p are correct but Unity keeps creating 1920×1080 internal images, inspect Unity quality/render target creation; the mode itself is no longer the missing lever. Do **not** reintroduce docked to fix this.

**Measured-device status:** not yet verified in this review. The stable 30+ FPS and swap-disabled cold-start goals remain unmet. This file is an engineering reference and does not change the runtime or launcher.

## Source licensing

Ryujinx, Skyline and ScarletNX have different upstream licenses and architectures. These examples explain observed API behavior; no third-party implementation source is incorporated here. Any future source reuse must be checked against the applicable upstream license and provenance before modifying the existing GPL overlay.
