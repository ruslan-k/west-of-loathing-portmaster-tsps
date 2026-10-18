# Component-only UpRender profile and a present-progress gate

## Why this is a separate profile

The original [UpRender repetition](../uprender-owner/README.md) found a repeated
local FPS gain but also one frozen 1080 control. A2's clean save/Spruce cleanup
was **not** successful gameplay: it stopped at frame 1481 and all seven route
screenshots were identical. Its cause is unknown; removing observations is an
isolation step, not a claim that observations caused the stall.

The `upscope2` build separates the camera-setting change from extended
constructor and queued-resource probes:

- `WOL_UPRENDER_TRACE=0 WOL_UPRENDER_720=0`: none of the five UpRender/queue
  sites is intercepted.
- `WOL_UPRENDER_TRACE=0 WOL_UPRENDER_720=1`: intercept **only Awake**, verify
  original dimensions and change the two component fields before allocation.
  No constructor, return or render-thread virtual-call observation is installed.
- `WOL_UPRENDER_TRACE=1`: explicitly restores all five bounded observation sites
  for diagnostics. It is no longer implied by the size flag.
- The full original main.text SHA and exact intercepted instruction still gate
  every enabled variant. All settings/observations remain default OFF.

Frozen build `wol-horizon-build-upscope2`, ARM64 ELF
`273b4638cae6dd4d0cbe7d1b4a91eac9e3f68c6b758fb7ef2729a2c28e31af13`.
The prior `37178b7a…` ELF was hash-verified into the device backup before activation.
The source overlay and 209-file frozen-build parity are retained here; no owner
executable, metadata, serialized asset or private save is published.

## Progress watchdog

The roadmap probe now has an opt-in `--present-watchdog 5` gate. During bounded
menu/game-idle/map waits and after injected actions it checks recent actual
MOMO_FRAME timestamps from a bounded log tail. It requires the enabled frame
clock and the same monotonic time domain. PID liveness, ongoing audio/HID or a
nonblack/stationary image do not count as presentation progress.

A stale/missing marker aborts the route, records an explicit failure, and
attempts owned-PID/start-time-verified proc/thread diagnostics before normal
save/process/Spruce cleanup. Optional `--stall-gdb` collects a bounded stack-only
backtrace on an actual stall, suppressing argument contents; it is never invoked
in a healthy timing window. The diagnostic failure itself must not mask the
original stall or bypass cleanup. Unit tests cover recent, missing, stale and
future-clock cases, and the adapter fixture proves that a size-only variant
cannot intercept UpdateTexture or queued-create.

The probe script was backed up before replacement, and both the probe and new
watchdog helper were independently hash-read back on the device. A watchdog
budget is a diagnostic stopping rule, not a root-cause or long-term stability
proof. GDB collection is not claimed exercised unless a stall receipt says so.

## Matched device protocol and limits

`upscope-a1` is size OFF; `upscope-b1` is size ON. Both explicitly set
`WOL_UPRENDER_TRACE=0 WOL_RT_ORIGIN=0`, use the same frozen ELF, original protected
section/save, sampler, real periodic readback, frame clock, governor and route.
`WOL_GPU_RESIDENCY=1` remains read-only. Other experimental fast paths are OFF.
No swap or CPU/GPU policy is changed. The probe's watchdog and optional
stall-only diagnostics are identical in both arms.

Measured same-profile result: **23.549 → 33.564 presents/s**, P95
**45.798 → 32.425 ms**, Mali commit **261.660 → 221.566 MiB**.
Game PSS is **377.845 → 392.198 MiB** and SwapPSS **550.789 → 537.852 MiB**;
no total-working-set or no-swap success follows. The lower-observation candidate
keeps the local FPS effect without queued-create/constructor interceptions.
This one bounded pair does not prove the older freeze fixed or identify its cause.

Both runs pass 87 progress checks, carry no stall/failure receipt, preserve the
same section/save/non-treatment environment and have zero analyzer GL errors.
The OFF log has no UpRender interception events; ON logs exactly the Awake
settings change and `trace=0 hooks=1`. Actual candidate KMS frames show complete
gulch body/UI, genuine map and restored Spruce. Both save/cleanup receipts are
clean. The saved A2 trace also replays as a 5.811-second stall at idle+3s in
`watchdog-replay.json`; no GDB stall branch was needed in these healthy runs.

Results are in `summary.json`, receipts, effective environments, compressed logs
and actual KMS captures. Do not mix this lower-observation profile with earlier
arms to invent a three-pairs dataset. Runtime presents are not independent
panel FPS; a short successful route is not physical input/audio, battle/interior,
long-duration, allocator-reclaim or no-swap acceptance. No default is promoted.
