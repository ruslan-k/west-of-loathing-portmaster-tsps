# B0 + B1 result — 2026-10-30 late

## B0 — overlay canonicalized, CI contract restored

`runtime/wol-adapter.patch` is regenerated from the neutralized baseline, so every file now has exactly
one section: **116 `--- a/` records, 116 unique** (was 125/116). `git apply` + byte parity against the
frozen tree verified, and locally:

```
tools/test_wol_memory_roadmap.py   9 tests, OK   (was: AssertionError 125 != 116)
tools/test_wol_da_split.py         OK, cannot skip (header is in-repo)
```

## B1 — closed: the rebuild used the base image table

`native/loader.c` includes `image_table.h`, which comes from the **image directory** argument of
`build_horizon.sh`, not from the recovered source. Every failing rebuild used
`spikes/wol-switch/wol-horizon-image` = **base** image:

| image | `rtld.text.seg` | `main.text.seg` |
|---|---:|---:|
| `spikes/.../wol-horizon-image` (used before) | 6,048 | 20,762,904 |
| `image-update-fixed` | 6,304 | 35,439,544 |
| device payload | 6,304 | 35,439,544 |

The fail-closed size guard was therefore working correctly; the candidate simply asserted the base
segment sizes against the v327680 update payload.

### Control rebuild (no H-D1), canonical overlay + `image-update-fixed`

```
ELF 0da0a5f478453fe4ab2caf0cf8e3c087dad19220ead1727242bd9870b392ffae
63 NVN_PROFILE lines, median 60-frame mean 40.98 ms, replay 24.77 ms
```

That is the accepted baseline (40.2–40.6 / 24.4–24.8), so the rebuilt ELF reaches verified moving
gameplay with the same image and returns to MainUI. **B1 exit met** for the control build.

## H-D1 — still no samples, but for a new and narrow reason

Candidate with the fixed ledger (separate enclosing-draw clocks, all 11 stages in the residual,
`_Static_assert(WOL_DA_STAGES==NPS_COUNT)`), built from the same canonical tree:

```
ELF 5566a5293eab7f506590cf6d97c7e94bbc70fd6a1460651bce0ca553895936a6
50 NVN_PROFILE lines, median 40.27 ms, replay 24.84 ms   (matches control: ledger is inert)
WOL_OP_V3 rows: 7760  -> env vars do reach the runtime
WOL_DA_CPU_SPLIT rows: 0, and no "enabled=1" banner
```

So the runtime starts, plays and counts draws, but `nvn_da_on()` never observes
`WOL_DA_CPU_SPLIT=1`. `WOL_OP_V3` is read with the same `getenv` pattern from the same process and
does work, and `update-launcher.sh` does not filter the environment, so the next check is the path
from `nvn_render_draw()` (dispatch at `nvn_render.h:4067`) to the wrapper at `nvn_render.h:3291-3298`,
not the launcher. Until that is settled there is **no stage attribution** and no H-D1 claim.

Device restored to `f5c6f6f2` (installed baseline) with matching `device-manifest.json`.
