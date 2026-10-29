# Update v327680: Screen sites are not the 1080p source

Run: `up24-screen1` on candidate `wol-update-probe-20261028`, ELF
`54e2eff61e9815773b4bf0551daec8a0caac650932d559bf8b88619668d3500a`,
`WOL_UPRENDER24_720=1 WOL_UPRENDER24_TRACE=1 WOL_PRESENT_TRACE=1`,
probe 300 s, watchdog 420 s.

## Measured

- `WOL_UPRENDER24 site=aspect owner=0x3b60a5d80 loaded=16x9 used=16x9 written=0`
  — the component's `+0x20` pair is the aspect ratio, not a resolution.
- `site=width owner=0x3b60a5d80 screen=1280 used=1280`
- `site=height owner=0x3b60a5d80 screen=720 used=720`
  — `UnityEngine.Screen::get_width/height` already return **1280x720** at this
  call site, so the rewrite had nothing to change (`written=0`). The 1080p
  camera target is therefore not derived from Screen here.
- Present path unchanged: `src=1920x1080 crop=0,0,1280,720 scaled=0`.
- Run ended at 49.6 s with `STOP status=T2_MEMORY_FLOOR` (rc=26). This is the
  runtime memory floor, not a logic failure: the launch started at
  `CmaFree 126 240 kB` and the guest consumed the headroom within a minute.
- Cleanup: `production_hashes_unchanged: 131`, no runtime process, MainUI back.

## Conclusion

The Screen hook is a dead lever and is not enabled. The 1080p source sits in
the component's own serialized settings or in a producer reached before
`UpRender.UpdateTexture`'s build site (which never fired at the title).
Next diagnostic: read-only `WOL_RT_ORIGIN` / `WOL_GPU_RESIDENCY` census of the
1920x1080 NVN allocations to obtain the real producer call path.

Candidate was returned to the last working ELF
`b506d04e4cd7e4e02d5d85c6c161e00a65692e9dec6875f04d0b72cb7c19641b`.
