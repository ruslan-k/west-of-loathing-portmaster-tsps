# Bring-up verification

## Current native execution

`native-run-12.log` was produced by the repository's current static AArch64 binary under `qemu-aarch64-static`. Text/rodata/data regions have distinct guest permissions and matching host protections. Original rtld performs discovery/linking; the C execution image is not Python-pre-relocated.

The guest makes 42 intercepted SVC calls, reaches `sm:`, sends a CMIF Initialize request with process ID, receives a valid SFCO success reply, then requests `lm`. That service is not implemented; the process terminates with explicit `UNIMPLEMENTED_SERVICE`, exit 70. No Unity start, frame, sound, input or handheld performance is claimed.

`native-run-11.log` is the preceding successful SM initialization run before permission-region hardening. The extra QueryMemory calls in run 12 follow finer-grained segment regions; they are not a speed regression measurement.

## Tests

- Full local suite: 21 tests passed, no skips, with ignored local owner inputs.
- Data-free suite: 17 pass, four owner-dependent integration tests skip explicitly.
- C builds with `-static -O2 -Wall -Wextra -Werror`.
- Independent OpenCode review identified a valid read-only output-pointer defect. A regression test reproduced an opaque nested fault; `writable()` validation and segment permission splitting fixed it, and real guest startup was repeated.
- Re-review: `passed=true`, empty security-concern and logic-error lists. Non-blocking hardening remains for parser limits, malformed JSON reports and CI dependency pinning.

## Kernel trap ABI is not public SDK function ABI

A review questioned `GetInfo` returning its value in x1. We verified the exact owner's SDK wrapper at `sdk+0xa9e04..0xa9e18`: it saves the public out-pointer from x0 on the stack, executes SVC 0x29, retrieves the pointer into x2, stores returned x1 through it, restores the stack and returns. The correct trap return is therefore Result in x0 / value in x1. Replacing it with a host store through x0 inside the trap would confuse the layers. The independent reviewer retracted that finding after examining the evidence.

The fixture tests are explicitly synthetic ARM64 guest instructions, separate from the real owner-SDK execution log. Guest CPU masks, memory budgets and main-thread priority are declared settings of the experimental virtual kernel, not measurements of TSPS or QEMU's host.
