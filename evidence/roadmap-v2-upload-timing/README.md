# Upload queue timing and a bounded saloon interaction route

## New timing evidence (not FPS)

`WOL_UPLOAD_TIMING=1` samples texture 460 at most 16 times, every 240 eligible uploads. Each sample drains prior GPU work, times the ordinary full-image upload, then drains upload retirement separately. This deliberately perturbs scheduling and must never be used as an FPS arm.

Eleven real device samples on ELF `a8f63d0313d9d0b0984d26004166b94d440443fbba33865908ec9c44e381a6d1`:

- Prior queue drain: median **11.401 ms**, P95 **11.855 ms**.
- Upload API call with prior queue drained: median **1.971 ms**, P95 **4.962 ms**, maximum **7.818 ms** (first sample).
- Following drain: median **0.087 ms**, P95 **0.112 ms**.

The full 3,686,400-byte upload remains real. These numbers do not prove asynchronous PBO speed-up: they show why the earlier ~5.8 ms caller span must not be interpreted as pure transfer cost. Queue backlog and transfer need separate attribution. `timing-summary.json` retains every sample; no shader, scene or global VM setting is changed by this diagnostic.

The conditional next experiment is therefore a **new default-off bounded unpack-PBO path**, with zero-time fence retirement, no reuse of in-flight slots, ordinary-upload fallback and comparisons to both normal and `WOL_REFRESH_DIRECT`. It is not the earlier VBO ring, immediate GPU blit or blind compositor async mode. See the separate PBO A/B report for its actual result; this document alone makes no performance claim.

## Gameplay classification

The owner-local basement save was preserved independently from the active owner save. Three accepted <=1500 ms left pulses visibly move the player from the stairs to the left of the room. Three subsequent A requests did **not** produce a visible battle, dialogue or room transition in the recorded KMS frames. This is movement/transport coverage, **not combat coverage**. Stop guessing this trigger; an owner-demonstrated interaction or verified pre-combat route is needed for that acceptance gate.

The final KMS frame is the real Spruce Recents menu. The receipt confirms exact PID/start-time cleanup, the original owner-save hashes, zero cleanup warnings and the nonblack-menu signal gate. No owner save contents are included here.

## Remaining safety gates

Cold startup without swap is not demonstrated. Earlier same-window startup samples reached approximately 33 MiB MemAvailable and 12 KiB CmaFree; other scene windows reached zero CmaFree. These are observations, not a disjoint physical-memory total. No complete, alias-free reclaimable Unity allocation has been proven, and no independent hard-recovery setup is validated. Global swapoff, arbitrary arena release and production async mode remain disabled; a dangerous launch is not substituted for the roadmap's recovery-safe acceptance condition.
