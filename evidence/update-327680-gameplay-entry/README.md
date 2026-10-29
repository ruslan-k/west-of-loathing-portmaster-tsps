# Reaching gameplay under instrumentation (v327680 candidate)

Attempt log for the census that must run on a loaded save, not on the title.

## Harness limit found

`WOL_PROBE_SECONDS=600 WOL_WATCHDOG_SECONDS=780` is refused at launch:
`WOL_WATCHDOG_REFUSED reason=invalid-input`, `status=64`, 370-byte log, no runtime
start. The accepted shape stays `probe 300 / watchdog 420`.

## Memory floor under tracing

First traced attempt died at 36.6 s with `STOP status=T2_MEMORY_FLOOR` (rc=26)
while the log had grown to 1.6 MB: RT-origin tracing plus the guest's own
footprint leaves no headroom. Launching the same candidate with
`T2_MEMORY_FLOOR_MIB=16` (diagnostic only; the CMA admission gate stays 65 536 kB)
lets the boot proceed: 314 `NVN_TEXTURE_REAL` allocations and a different screen.

## What the tap produced

User-confirmed entry is a single A on the title. After one A tap at 110 s:

- allocations 314, of which real 1920x1080 = **4** (three swapchain images + one
  depth), unchanged from the title census;
- 74 further lines mention `size=1920x1080` but are create requests, not
  `NVN_TEXTURE_REAL` allocations — counting them would inflate the result by 18x;
- the captured frame changed (574 colours, mean 215) versus the title
  (2073 colours) and versus the dark non-presenting state (426 colours,
  mean 4), so the tap was delivered and the UI moved to another screen.

## Next

Confirm which screen that is (no OCR on the host) and whether it is gameplay or
an intermediate menu; the dynamic 1080p camera targets only exist once a save is
actually loaded, and only then does the v23 `forceWidth/forceHeight` experiment
become measurable.

## Entry attempts with the traced candidate (`opt-origin-g8`)

With the diagnostic floor at 16 MiB the boot is healthy (306 -> 438
`NVN_TEXTURE_REAL` allocations). Taps were delivered on `/dev/input/event4`:

| Injected | Result |
| --- | --- |
| BTN_SOUTH (304) x2, 4 s apart | screen unchanged (distance 1.4 to the title), +118 streamed textures |
| BTN_EAST (305) x2 | same: title stays, only asset streaming grows |
| BTN_START (315) | run had already reached `TIME_LIMIT`; capture matched the post-exit Spruce frame |

`native/t2_face_position.h` documents that SDL "a" is **BTN_EAST** and that a
face swap flips A/B, so the evdev code for the in-game confirm button is not
simply "304". Before another entry attempt, read the guest-side input
diagnostic (`COTM_INPUT_DIAGNOSTIC=1`) to see which hid bit each injected code
actually produces, then tap the one that maps to Switch A.

Harness fix that removed a recurring false start: the probe now refreshes
`device-manifest.json` from the device before every run, so the identity assert
can no longer fail against a stale local copy.

## Owner instruction and a wedge

Owner states gameplay entry needs **several A presses**, not one. Injection of
306/307 and a six-press A run (`opt-input-map1`) could not be evaluated: the
device stopped answering (`ssh: No route to host`, ping down for 2.5 min) and
needs a physical power-cycle. That is the known memory-pressure wedge class, not
a port crash - it came after several traced runs with the diagnostic floor at
16 MiB.

Next entry attempt, after the power-cycle: one quiet run (no RT tracing), six A
presses (BTN_EAST 305) 2.5 s apart, then confirm the scene by frame match before
enabling any census.
