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
