# Final validation and remaining acceptance gates

## Standards / safety review

- Clean overlay application matches all 199 native files of the measured PBO build. The ARM64 runtime compiled with warnings-as-errors; source/binary identities are archived with the actual device runs.
- No game/console binary, save, ASTC payload cache, extracted shader binary or raw texture pixels are included. Compressed logs, screenshots, exact hashes and authored source/tests are retained.
- Experimental post-copy ASTC and PBO remain default-off. PBO's fence/context/buffer lifetime and ordinary fallback are exercised with actual overlay C helpers, not a reimplementation.
- Ordinary launch no longer exposes the diagnostic input-injection socket by default. A hash-verified backup and independent installed-file readback precede the repeated title test.
- Two legacy source-contract test fixtures were brought up to the real helper boundaries without removing their contract: RGBA8 checks the exact ordinary upload wrapper arguments; multistream fixtures supply and exercise the actual optional census dependency rather than suppressing warnings.

## Executed tests

`tests.json` records actual successful execution:

- 39 data-free unittest cases, including the memory/overlay/hazard suite and staged selection/Sprite metadata tests.
- 11 legacy source-contract CLI programs, supplied with the frozen native directory/header each requires.
- 22 standalone ARM64 trap/IPC/preparation unittest cases.

Generic `unittest discover -s tools -p 'test_*.py'` is not the test contract for the legacy CLI programs: it imports them with `discover` as a path. Those invocation errors were diagnosed, then every CLI was executed with its actual required source arguments. The unrelated old raw `dtime5-runtime.log` remains outside this checkpoint.

## Spec review — what is still not accepted

The roadmap's finite source/ledger, copy counterexample, SDK allocation trace, real-content ASTC and conditional PBO experiments have measured results. They are not a full release certificate:

- Combat, complete world/interior travel, save/load/reload, late-game and physical-button/audio coverage remain unverified; the bounded basement interaction route did not trigger a battle.
- Map-marker/title parity needs independent scene/reference validation.
- SDK allocation identity does not prove inner Unity free-list ownership, last page access or safe reclamation.
- Sustained 30+ presents/s and P95 ≤33.33 ms are unmet in the saved comparable windows.
- No recovery-safe swap-disabled cold boot has been demonstrated. Swap configuration, global VM settings and unsafe page-release mechanisms remain unchanged.

The latest ordinary title and final real Spruce menu are captured in [clean-title](../roadmap-v2-clean-title/README.md). The remaining gates require a verified pre-combat/travel route or owner demonstration, physical input/audio evidence and a validated no-swap recovery setup; they are explicitly blocked/unmet rather than marked complete.
