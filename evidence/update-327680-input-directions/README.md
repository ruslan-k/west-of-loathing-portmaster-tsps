# v327680 — Npad stick direction bits (build sticks-w5)

Diagnostic checkpoint, not a release. Scope: the isolated update candidate
`/mnt/SDCARD/Roms/PORTS/wol-update-probe-20261028`. Production native Unity install and its
saves were not touched.

## Defect and fix

The pinned SDK's `nn::hid::detail::GetNpadStates` (sdk+0x208a40) copies the padded
`NpadButton` word straight out of the shared ring; it does not derive stick directions. The
provider published analog axes but left pseudo-button bits 16..23 clear, so a guest that reads
directions (rather than raw axes) saw a centred stick.

`native/input_ring.h` / `native/input_host.h` now synthesise both sticks' direction bits at
publication time (threshold 16384, half range), preserving raw axes, the 0x28-byte sample ABI
and every other button bit. Covered by `tools/test_wol_memory_stick_directions.py`
(observed red before the patch, green after). Runtime suite: 106 tests OK.

Artifact `sticks-w5`: 2006616 B, AArch64, max GLIBC 2.27,
SHA256 `783ebb5116290d02ee2f2d8536cf47fc98943ed8daba8f2991e2fb184da6314c`.
Source/overlay/frozen parity 210; only native delta from aoc-w4 is those two input headers.
Previous aoc-w4 ELF (`6003b1c8…`) and its manifest were backed up before activation.

## Device result (run `sticks-a1`)

- Title → ordinary Continue → farm reached; inventory opens with `Plus` (0x400) in the default
  Handheld profile (styles 7, IDs [32, 0], FullKey entry 0 and Handheld entry 8 both connected).
- Transport now correct: one calibrated right-stick pulse (event4 ABS_RY +32767 for 350 ms,
  axis restored to 0) reached both live rings as `buttons=8388608` (bit 23, R-down) with
  `ry=-32767`. Before the fix the same pulse produced `buttons=0`
  (`input-c5-right-baseline-npad.json`, `sticks-a1-right-after-observer.log`).
- **The filter hypothesis is falsified.** The matched frame after the pulse is pixel-identical
  inside the list region (520,80)-(920,670): min/max 255, stddev 0.0, 0 non-white pixels in both
  frames, and the header band is unchanged. Delivering the missing direction bits is necessary
  for SDK correctness but does not populate the inventory list.
- Run ended by `TIME_LIMIT` (rc=22, 543.371 s), not a crash. Cleanup verified: `MainUI` back,
  no runtime or `/tmp/cmd_to_run.sh` handoff, CPU restored, 131 production hashes unchanged,
  Spruce home inspected on KMS.

## Consequence for the remaining work

The blank centre panel is a draw/clip/state defect in the inventory pass chain, not an input
mapping defect. Next step is the per-draw receipt on that panel (mask word, blend, scissor and
the fragment-bank guard for the list rows), not further stick or button experiments.
