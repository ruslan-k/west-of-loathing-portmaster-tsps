# M1 / M5 measurements and staged M4 wave2

**Status:** measurement infrastructure exercised on TSPS; M5 read-only attribution
completed for these scenes, **allocator ownership/free-list analysis not completed**.
No new memory optimization is enabled. Accepted M4 section remains installed.
See [tooling/reproduction](../../docs/memory-benchmark.md).

## Artifacts and conditions

- Runtime SHA256: `4c7191b305c90024b23520af2887cc544a36c927307e3b2b330e92222913c51b`.
- Accepted M4 section SHA256: `a25600cebbd47376d9520d2c4d648463a78911224e8bc82e645dcab6223deb36`.
- Two cold-cache launches, same SHA-checked controlled save, same launcher
  settings. No clock, affinity or VM-policy writes by this benchmark (apart from
  the explicitly requested `drop_caches=3`). The normal launcher still manages
  its own CPU online-mask lifecycle. Real periodic readback remains enabled.
- Run A: startup, 30 s ready menu, CONTINUE, 30 s street, 20 s sheriff interior,
  20 s return to street. Run B repeats startup/menu/street only.
- Every named scene was checked in the actual KMS frames in `run-a/` and
  `run-b/`. Synthetic diagnostic Npad input is not a physical-pad test.
- Raw machine data is in the compressed per-phase JSON files; `analysis.json`
  preserves aggregate summaries and inter-phase identity differences. Source
  descriptor layout and exact ELF binding are in `layout.json`.
- Raw files retain `scene_verified=false` because the collector itself performs
  no scene recognition. Human/model review of actual frames is recorded
  separately in `scene-review.json`, not retroactively fabricated by the sampler.

## Measured results

All memory values below are MiB. End PSS+SwapPSS is process accounting, **not**
whole-device/GPU RAM. The two runs are repeat observations, not an optimization A/B.

| Phase | Run A PSS+SwapPSS | Run B PSS+SwapPSS | A / B presents/s |
|---|---:|---:|---:|
| Ready menu | 878.29 | 881.96 | 25.52 / 26.43 |
| Outdoor street | 910.50 | 910.24 | 24.86 / 26.17 |
| Sheriff interior | 900.72 | not sampled | 27.41 / — |
| Street after return | 896.74 | not sampled | 25.25 / — |

Status RSS and VmSwap are preserved independently:

| Phase | A mean status RSS / swap | B mean status RSS / swap |
|---|---:|---:|
| Menu | 689.60 / 416.24 | 683.08 / 426.24 |
| Street | 679.06 / 474.08 | 699.27 / 446.62 |

Startup observations:

- VmHWM: **753.28 / 760.45 MiB** (process-lifetime status counter).
- Sampled peak PSS+SwapPSS during startup: **878.13 / 886.66 MiB**.
- Minimum MemAvailable: **32.28 / 29.70 MiB**.
- Minimum CmaFree: **12 KiB / 0 KiB**.
- Startup major faults/s: **188.48** in run A; this is much higher than the
  steady street window (**4.73/s**). Run A's system swap-in/out was
  **3480.69 / 9965.14 KiB/s** during startup. These are system-wide counters.

The ~700–750 MiB / adequate-headroom / no-disk-swap target remains **unmet**.
Nothing in this phase establishes a new FPS or RAM gain. Final source adds clock
and online-mask fields to future snapshots; these first two runs did not have
in-window clock series. `run-b/clocks-after-cleanup.json` is explicitly a late,
idle observation, **not** evidence of sustained in-game frequencies.

## M5 attribution: what is now established

At the end of run A's street window:

- **250 live texture objects / 250 unique host resources**; estimated host image
  extent **196.83 MiB**. This is not an independently measured Mali allocation.
- Borrowed pool union reserves **655.97 MiB virtual**. All observed pool spans
  lie inside the guest heap; they are aliases, not an extra allocation to add.
- Pagemap counts approximately **201.95 MiB** of present-or-swapped virtual pages
  in that pool union, versus **900.92 MiB** across the guest heap reservation.
  About **699 MiB** of counted heap pages are outside those NVN pool spans.
  This identifies a priority for deeper owner/allocator tracing, not a safely
  reclaimable 699 MiB block. Pagemap counts are not unique physical memory.
- The largest anonymous smaps mapping accounts for **701.97 MiB PSS+SwapPSS**;
  a separate native anonymous mapping accounts for **64.10 MiB**. Their allocator
  ownership and live/free contents are not yet known.

Endpoint lifecycle differences:

| Transition | Newly live texture IDs | No-longer-live texture IDs | Pool-span changes |
|---|---:|---:|---:|
| Menu → street | 74 | 41 | 0 |
| Street → sheriff | 17 | 21 | 0 |
| Sheriff → street | 20 | 5 | 0 |

Live texture counts: **217 → 250 → 246 → 261**. Texture finalization demonstrably
happens; pool reservations persist in these observations. Created-object totals
must not be interpreted as simultaneously live memory. One round trip is
insufficient to distinguish retained caches from leaks, especially with a moving
camera/visibility set. No forced unload or decommit was attempted.

## Staged wave2 (not deployed)

The prior broad >=512 DXT estimate was too permissive. An explicit world-only
allowlist plus direct UI-reference exclusion selects **53** additional textures,
keeping the exact 100 accepted M4 overrides. Expected payload saving versus M4:
**19,660,800 bytes / 18.75 MiB**, not a measured physical-RAM saving.

- Candidate texture payload: **376,016,436 bytes**.
- Candidate bundle: **143,296,805 bytes**.
- Candidate owner section SHA256:
  `0deca8e9ab2c0723e3891c3404a35e3cdb19d369875586830d385e7e1fff902c`.
- Verification checks all **53,965 objects**: 53 intended texture changes,
  53 exact dependent Sprite pixel-metadata adjustments, **53,859 other objects
  byte-identical to M4**. All 53 new pixel slices are byte-identical to the
  corresponding original mip level.
- Selection, audit, complete repack decision manifest and verification receipt
  are under `staged-wave2/`. Bundles/sections/pixels remain local owner data.
- No staged candidate was installed, so no visual acceptance, memory gain or
  speedup is claimed. Current working section is still accepted M4.

## Verification and cleanup

- **16 new data-free tests passed** (15 profiling/benchmark tests plus one
  world-selection test). Added to CI. Regression cases include exact ELF
  matching, pool-union overlap, reused object IDs, accounting disagreement,
  frame-counter gaps, framebuffer retry and rejection of black PNG captures.
  Failure-injection tests also cover archive ENOSPC, observer-shutdown errors and
  the active/unowned-runtime case: preserve the owner backup and explicitly mark
  pending recovery rather than overwriting files a live game can still write.
- Existing synthetic ARM64 build passed with warnings as errors; baseline suite
  **22 tests, 5 owner-input-dependent skips**, no failures after installing the
  documented QEMU/lz4 dependencies in the build container.
- Existing mesh-UV and pl:u service regression commands passed. Generic unittest
  discovery over every tools/test_*.py is not valid: historical standalone
  scripts require explicit source arguments. No blanket discovery pass is claimed.
- Run A's initial cleanup capture raced framebuffer availability; owner save and
  process cleanup had succeeded, then a fresh capture verified Spruce.
- Run B exposed a second pitfall: kmsgrab may return success for a black frame,
  and the idle screen then shows Spruce's clock. Final capture checks reject
  black output; synthetic **B** dismissed the screensaver without changing idle
  settings or launching a game. The final actual PORTS menu was reviewed.
- Both owner-save manifests were restored exactly; no wol-horizon test process
  remained. `receipt.json` files distinguish initial capture from recovered
  visible cleanup. MainUI and the principal supervisor were left running.

## Independent review status

**NOT CLEARED.** The first external source review identified teardown exception
safety; it was corrected and covered by failure-injection tests. Its suggestion
to restore over a still-running game was rejected as unsafe; the tool now
explicitly preserves the owner backup and reports pending recovery instead.
Reapproval did not produce a usable verdict: a CLI call exhausted its reasoning
budget, and direct retries were rejected by the workspace region requirement.
No account privacy setting was changed. See `review-status.json`. Local tests
and CI results are separate from independent review; this remains an experimental
checkpoint, not a release or independently cleared optimization.

## Open items

- M5 deeper attribution: identify the non-pool heap owners, AssetBundle and
  allocator retention, free-list/active-byte accounting; repeat scene cycles.
- M6 side-cache and direct compressed GPU uploads remain unimplemented.
- M7/M9 remain deferred research, not proven universal impossibilities; see the
  narrower interpretation in `docs/memory-benchmark.md`.
- M8 remains blocked until wholly free page ownership can be established.
- Map layout, combat/later-location regression and long-session leak/no-swap
  acceptance are outside this measurement pass and remain unverified.
