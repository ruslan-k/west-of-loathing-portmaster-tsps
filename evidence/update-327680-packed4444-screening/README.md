# Native 4444 screening: current title has no eligible source format

## Outcome

`pq5-4444` reached a visible West of Loathing title with Continue/New Game/Options.
The runtime ended on its diagnostic `TIME_LIMIT` (rc 22, 301.996 s), not a crash.
Gameplay was not entered. This is screening, **not a matched performance A/B**.

Exact runtime: `packed-w7`, 2,006,656 bytes,
SHA256 `a6b44dcdec6bb9ec9e8df77f40ab735427e2afcdf5adc68618fba76cdc49ccc2`.
The overlay only removes the packed4444-specific compile-time guards; the option
remains default-off. No other placeholder feature was enabled.

## Live proof

- The process environment contains `WOL_PACKED4444=1`, `AW_RELEASE=1`,
  `WOL_CMA_MIN_KB=65536`, `T2_READBACK_OFF=2`.
- Exact-source sizeof/offsetof and ELF BSS validation produced `layout.json`.
  The read-only descriptor observation is bound to PID/start ticks, boot ID and ELF.
  It took 0.105 s; it is unlocked best-effort, not an atomic GPU snapshot.
- 287 live objects: 0x25=168, 0x35=4, 0x1=19, 0x6=2, 0x42=6, 0x44=88.
- **0 objects of format 0x39; 0 with host_upload_type 0x8033.**
- The title screenshot proves actual pixels. No claim is made about gameplay formats.
- Calculated descriptor extent is 280,029,808 bytes, **not measured Mali allocation**.
  Do not add it to RSS or call it working set.

## Corrections to the earlier analysis

The estimate “130 native-4444 textures, recover 29.5 MB” came from joining process-local
texture IDs across historical logs. That does not describe this run and is withdrawn.
It is neither a measured saving nor a valid upper bound for this scene.

`AW_RELEASE=1` makes `diag_printf` return without emitting. Zero `WOL_PACKED4444`,
`NVN_TEXTURE_REAL`, `NVN_PROFILE` or residency lines is not evidence of an uncalled
path, missing textures, or zero presents. The earlier present-path/CMA diagnosis
based on missing profile lines is unproven; the approved CMA threshold is retained.

Native UNORM4444 repacking is value-preserving (`n * 17` in RGBA8), not new lossy
quantization. Upload type alone does not establish the driver's internal allocation.
ASTC 4x4 is 1 byte/pixel before mip/alignment overhead, not 1/8 of RGBA8.

## Memory and cleanup

See `summary.json` for sampled minima and final process accounting. These are not
matched-scene deltas or evidence that the flag reduced memory. Cold/aliased guest
pages and swapped accounting must not be treated as required active RAM.

Cleanup verified 131 production hashes unchanged, CPU state restored, no candidate
runtime and no pending principal handoff. `recovered.png` shows Spruce's main screen
(not the Ports submenu). The native Unity production port was not replaced.

## Checks

- Applied overlay versus frozen build source: 210 native files, zero mismatches.
- Runtime memory suite: 107 tests passed.
- Packed4444 fixture: all 84,934,656 source-word/swizzle combinations passed,
  plus default-off, enabled, immutable and invalid-option cases. The fixture now
  includes the real `aw_release.h` dependency instead of an undeclared logger.

No owner game payload, keys, runtime executable, or save files are included here.
