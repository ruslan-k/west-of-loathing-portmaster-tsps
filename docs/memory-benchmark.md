# M1/M5: read-only memory benchmark and staged M4 wave2

## Scope and safety

This phase implements the measurement part of M1 and the **read-only first phase
of M5**. It does not claim the full resource plan or allocator analysis is done.
It does not optimize RAM by itself. The accepted M4 owner section and runtime
are unchanged. M4 wave2 remains staged locally, not deployed.

Tools:

- `tools/wol_memory_layout.py`: extracts the actual struct declarations from an
  exact build's `source/native`, compiles `sizeof`/`offsetof`, cross-checks table
  extents against ELF symbols and binds the output to the full executable SHA256.
- `tools/wol_memory_profile.py`: reads `/proc` accounting, **host descriptor BSS
  only**, and pagemap flags. No guest heap bytes or texture pixels are read.
- `tools/wol_memory_benchmark.py`: startup monitor, bounded named phase windows,
  complete page/descriptor snapshots and endpoint lifecycle differences. Its
  device runner wraps the existing principal-flow session harness.
- `tools/wol_m4_stage_wave2.py` and `tools/verify_wol_wave2.py`: conservative
  staging and full-object offline acceptance test for an optional second wave.

The proposed in-runtime `WOL_MEM_PROFILER` flag is not added. This implementation
uses an **external observer**, avoiding a runtime change and keeping profiling
off the game's hot path. A missing/mismatched ELF layout refuses descriptor
reads instead of guessing offsets. Pagemap access failure is explicit.

## What the tools measure (and do not measure)

- Status RSS / VmSwap / VmHWM remain separate from rollup PSS / SwapPSS. This
  kernel's accounting disagreement is retained in raw data, not normalized away.
- Startup is observed from first discovery of `comm=wol-horizon`, about once a
  second. Its maximum is a **sampled peak**; VmHWM has process-lifetime scope.
  Allocations before discovery or between samples may be missed.
- MemAvailable, CmaFree, process major faults, and system-wide swap-in/out are
  collected. System swap traffic is not attributed solely to the game.
- Borrowed pool ranges are unioned, not added per resource. They alias the guest
  heap and must **not** be added to PSS or to heap pagemap counts.
- Pagemap present/swapped/unmapped describes virtual page state, not allocator
  ownership, reachability, unique physical pages, or free-list availability.
  `unmapped` does not establish that Unity's reserved block is safely releasable.
- Texture lifetime uses monotonic runtime object IDs, not reusable descriptor
  addresses. Endpoint differences miss create+delete activity between snapshots.
- Unique GL image extent is a format/dimension estimate, not measured Mali heap.
  No GPU RAM or overall no-swap budget is established.
- Unity native/managed active bytes, allocator free lists, AssetBundle cache
  ownership and safe decommit ranges remain **unknown**. No `madvise`, forced GC,
  `UnloadUnusedAssets`, pool retirement, clock changes or heap-budget changes.

## Reproduce on this owner workspace

Generate a layout from the **same build** as the installed executable:

```sh
python3 tools/wol_memory_layout.py \
  /mnt/external/Hermes/spikes/wol-switch/wol-horizon-build-astc1 \
  "$TMPDIR/wol-memory-layout.json"
```

Copy `wol_memory_profile.py`, `wol_memory_benchmark.py` and the generated JSON
to the device staging directory. The existing session harness is device-local
`/mnt/UDISK/session.py`; it performs the standard Spruce principal/menu handoff,
65-second startup wait and opt-in diagnostic Npad input. Its SHA is recorded.
The runner currently consumes that harness's state file at
`/mnt/UDISK/wol-goal-20261015/session.json`; it is not a universal game launcher.

```sh
python3 /mnt/UDISK/wol_memory_benchmark.py run \
  --label UNIQUE_LABEL \
  --layout /mnt/UDISK/m5-layout.json \
  --control-save /mnt/UDISK/wol-goal-20261015/copy-off-a1-saves-before \
  --out /mnt/UDISK/UNIQUE_OUTPUT \
  --seconds 30 --cold
```

The runner refuses a non-idle device. It snapshots the **current** owner save,
compares every copied SHA256, installs the controlled save only for the test,
monitors startup, captures/measures ready menu, presses CONTINUE, then measures
the world. Every exit path attempts to stop only the owned PID+start-time,
restore/re-hash the owner save, and verify a real Spruce framebuffer. MainUI
existence can precede its first DRM framebuffer; bounded capture retries cover
that race. Repeated failure remains an error, not a successful cleanup receipt.
Secondary log/archive or observer-shutdown errors are recorded but do not skip
the safe save restoration. If a runtime remains alive or its ownership is
uncertain, the runner must **not overwrite live save files**: it preserves the
verified `owner-save/` backup, writes `owner_save_restore_pending=true` and
`cleanup_verified=false`, and reports the recovery path. Stop the game safely
before restoring that backup; never follow a reviewer suggestion to restore
over a still-running game.

For additional scene probes, `--gate` waits up to 240 s after the world sample
for `OUTPUT/interaction.done`, while checking the owned PID. Use the live
harness to enter an interior, capture and classify the frame, then attach:

```sh
python3 /mnt/UDISK/wol_memory_benchmark.py collect \
  --pid OWNED_PID --phase sheriff --seconds 20 \
  --layout /mnt/UDISK/m5-layout.json --out /mnt/UDISK/UNIQUE_OUTPUT
```

After returning outside, repeat as `--phase returned`, then create the gate's
completion marker. Do not treat an accepted input packet or screenshot filename
as scene proof. Machine output defaults to `scene_verified=false`; the evidence
report records which actual KMS frames were reviewed.

`owner-save/` and raw game/texture bytes stay local. Publish accounting,
descriptor metadata, filtered memory/frame receipts, reviewed screenshots,
source/tools, tests and reproduction commands only.

## Wave2 staging contract

The old suggestion of halving all remaining DXT >=512x512 was overbroad: DXT
format does not identify backgrounds. Wave2 adds an explicit world/background
allowlist, blocks direct serialized UI references and retains the exact 100
accepted M4 overrides. It selects **53 additional textures**, not an unreviewed
275-prop batch. Expected payload reduction versus M4 is **19,660,800 bytes =
18.75 MiB**. This is not a RAM saving measurement.

Offline verification compares **all 53,965 objects** against accepted M4:
53 textures have the expected dimensions and byte-exact original level-2 slices;
53 dependent Sprites have exactly the required pixel-metadata adjustment;
53,859 other serialized objects are byte-identical. Candidate bundle:
143,296,805 bytes; texture payload 376,016,436 bytes. The owner-data section is
staged locally with SHA256
`0deca8e9ab2c0723e3891c3404a35e3cdb19d369875586830d385e7e1fff902c`.
It is **not installed or visually/device validated**; no FPS/PSS improvement is
claimed.

## Prior research: conclusions must stay narrower than the probes

- M7's ListDisplays experiment was inert for this title. That rules out this
  particular display-service override, **not every possible guest render-scale
  or coordinated target-scaling solution**. M7 remains deferred, not completed.
- M9's tested format-56 bundles produced no demonstrated native ASTC upload;
  one size signature changed from BC to RGBA and the binary contains fallback
  strings. The probes did not establish an identity-bound path for every asset,
  and the earlier feature-query toggle did not establish actual shader/device
  support negotiation. They do **not prove ASTC is universally impossible**.
  M9 remains an unsuccessful/deferred probe, not a hard impossibility theorem.
- M6's side-cache path is independent of in-bundle M9 and remains unimplemented.
- M8 is blocked on trustworthy allocator ownership/free-list attribution. Do not
  decommit unknown heap pages based on pagemap, pool occupancy or a zero scan.

Measured phase results and remaining budget are in
[`evidence/memory-profile-m1m5/`](../evidence/memory-profile-m1m5/README.md).
