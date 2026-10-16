# CPU placement A/B (roadmap section 4): guest logical CPUs 0–2 on host CPUs 4–6

Isolated one-variable A/B of the implemented guest-ABI-preserving host CPU remap
(`WOL_CPU_OFFSET=4`: guest logical IDs/masks unchanged, physical execution moved from the
1.416 GHz cluster to the 1.992 GHz cluster; receipt line
`WOL_CPU_MAP logical=0,1,2 physical=4,5,6 guest-masks=unchanged no-clock-change`).

## Runs (same build `982cb51b…`, layout, save, harness)

Order intentionally alternated (control → remap → remap → control):

| Run | Env | menu elapsed ms | game elapsed ms |
| --- | --- | --- | --- |
| `cpuctl` | — | 38.34 | 36.72 |
| `cpuremap` | `WOL_CPU_OFFSET=4` | 38.82 | 37.63 |
| `cpuremap2` | `WOL_CPU_OFFSET=4` | 37.20 | 37.22 |
| `cpuctl2` | — | 38.61 | 37.20 |

## Conclusion

No repeatable >noise gain in either direction: game elapsed means 36.96 ms (control) vs
37.42 ms (remap), menu 38.47 vs 38.01 ms — both within the ±1–1.5 ms run-to-run envelope
recorded across today's runs. The remap stays an opt-in flag and is not proposed as a default.
Per-thread CPU distributions and temperature/power instrumentation were not collected; a
slower-clock/energy variant remains a separate experiment per the roadmap.

Artifacts: `cpuctl-*`, `cpuremap-*`, `cpuremap2-*`, `cpuctl2-*` (analysis + receipts).
