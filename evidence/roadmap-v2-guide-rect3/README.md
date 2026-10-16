# Guide screen, rect trace over the whole map panel (rect 300,240 → 1010,660)

Purpose: enumerate every draw inside the guide's map panel, not just the list band, after the
owner's reference frame showed that the earlier band `460,485,690,595` covered only the single
visible label.

Method: owner save restored (`4a86756d8bf5e115…`), runtime `0cca40eca762c984…`, features off, one
`ZL` press, `WOL_RECT_TRACE=300,240,1010,660` with a 100,000-hit budget, no draw trace. Receipt
and the complete `runtime.log.gz` are here; cleanup verified, no warnings, owner save restored.

Result: 149,404 log lines, 2,726 frames, 9,083 rect hits during the guide period (555 frames).
Grouped by draw pair (fragment/vertex), with the bound texture:

| pair | hits in panel | texture | notable transformed boxes |
| --- | --- | --- | --- |
| `f08bad2f#a9b0 / f309b86a#0184` (translated) | 3,081 | 269/457/7506/7507 | full screen 0,0,1280,720 |
| `f191-draft / v189(d88c64a6)` | 2,808 | 269 | 282,0,998,720 · 253,15,740,714 · 400,439,1535,985 · 256,-66,895,700 · 503,470,600,504 |
| `top-f-uvraw / top-v-draft` | 2,639 | 6936 | **-1500,513,1611,568** · **-1305,431,1523,482** · 398,507,1037,720 · 745…850 small elements |
| `f268-draft / v266(d88c64a6)` | 555 | 457 | full screen (linked `mode=TEST-DIAGNOSTIC-COLOR note=not-a-translation`) |

Filtering out full-screen compositor passes, the panel contains: one recurring large `f191` element
(`262,18,580,710`, once per frame), the single label quad (`503,470,600,504`, once per frame), a
set of absurd-width `top-f-uvraw` strips whose x range spans 2,800–3,100 px (once per frame each),
and small `top-f-uvraw` elements jittering around x745–850 / y465–660. No label-sized draw appears
at any of the reference's four other label positions.

Caveat stated in the runtime's own filter: `if(rt_conf==2 && avail>=32*4 && count<=96 && rt_hits<rt_lim)`
— a draw with more than 96 vertices is **not** traced, so multi-quad text and large meshes cannot
be ruled out from this log. That is what the next rebuild removes.

Reference frame used for the regional comparison: `img_ebee2fb95f01.jpg` (identical to
`img_4165f7264621.jpg`, both 1280×719, sha256
`b060b177255940178418e126629a24316fed577036b9371195c5998a715d31c4`), plus the owner's second send
`img_31a2990e8de3.png` (2096×1178, sha256
`62bf40610faed4e67b46f771f56df63536c7c3a67b7b559b1f746f3cf39f6edb`) — same screen, mean
per-channel difference 1.16 after rescaling, so the two sends are one image. The owner's frames are
not committed (owner content); a local-only copy for re-measurement sits next to this directory as
`../roadmap-v2-owner-map/reference-guide-owner.jpg` and is git-ignored.
