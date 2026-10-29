# v327680 — handheld vibration write route

Diagnostic checkpoint, not a release. Isolated candidate
`/mnt/SDCARD/Roms/PORTS/wol-update-probe-20261028`; production native Unity install and its
saves untouched (cleanup receipt: 131 production hashes unchanged, CPU restored, MainUI back).

## Defect

Run `rect-a1` stopped 129 s after launch:

```
STOP status=HID_VIBRATION_ROUTE_REQUIRED pc=sdk.text.seg+0x393e00 detail=0x12004
WOL_WATCHDOG_EXIT reason=runtime-exit rc=20 elapsed=129.488
```

`detail` is the logical Npad handle `0x12004` — style 4, player `0x20` (handheld), device 1.
The guest wrote vibration values for that handle **before** any `SendVibrationValues`
registration session existed, so `hid_vibration_side()` found nothing in the registration
tables and the fail-closed guard killed the whole runtime over a cosmetic rumble request.

The same title does register all four handles in other runs (`0x3`, `0x10003`, `0x2004`,
`0x12004` — see `vib-a2-vibration-registration.txt`), so this is an ordering race, not a
permanently missing code path.

## Fix

`native/input.h`, inside the existing write guard: when the handle is structurally valid and
carries the handheld player id `0x20`, it is accepted as implicitly mounted and logged
(`HID_VIBRATION_IMPLICIT_HANDHELD`, bounded to 4 lines). The value still reaches the pad only
through the normal mounted-handheld path, so no rumble is fabricated. **Every other
unregistered handle keeps failing closed** with `HID_VIBRATION_ROUTE_REQUIRED`.

Tests:
- `tools/test_wol_memory_vibration_implicit.py` — new, RED before the patch
  (`handheld=20`), GREEN after.
- `tools/test_wol_memory_vibration_info.py` — updated to the measured contract: `0x12004`
  write accepted, `0x103` still refused with rc 20.
- Full runtime suite: 107 tests OK.

Artifact `vib-w6`: 2 006 640 B, AArch64, max GLIBC 2.27,
SHA256 `150be7939f8b73d6b20060eda653e894d20848910d6bebbfdf2c80a35c93034a`,
source/overlay/frozen parity 210. Previous `sticks-w5` (`783ebb51…6314c`) backed up on device
before activation.

## Device runs

- `rect-b1` — never launched: CMA preflight refused (`free_kb=44532 < min_kb=65536`).
  Reversible one-shot reclaim (`sync`, `drop_caches`, `compact_memory`) moved CMA 2940 → 73392 KiB.
- `rect-b2` — launched, then stopped on `T2_MEMORY_FLOOR` at 33 s (available fell to 59 MB
  against the 24 MB floor) during load. No vibration stop.
- `vib-a2` — `vib-w6`, 542.475 s, ended by `TIME_LIMIT` (rc=22), **no STOP of any kind**;
  `HID_VIBRATION_IMPLICIT_HANDHELD` count 0 because this run registered the handles normally
  before writing. Cleanup passed.

So the crash class is removed and the runtime survives far past the 129 s failure point, but
the implicit branch itself was not exercised on device in this run, and farm/inventory
acceptance is still not reached: CMA and the memory floor dominate these attempts.

## Not addressed here

The blank inventory item list (draw/clip defect, see
`evidence/update-327680-input-directions/README.md`) and the DLC scene/audio/reload gates
remain open.
