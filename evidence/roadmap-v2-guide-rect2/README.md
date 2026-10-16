# Guide list band with a screen-rect draw filter

Purpose: enumerate every draw whose transformed box intersects the guide's locations-list band,
so a missing entry cannot hide behind the aggregate counters.

Method: `WOL_RECT_TRACE=460,485,690,595` (the band around the single visible entry) is forwarded
by `session.py` for one guide opening on the restored owner save; `runtime.log.gz` is the
complete trace. The earlier run with a 20 000-hit cap
([`../roadmap-v2-guide-rect/`](../roadmap-v2-guide-rect/README.md)) exhausted its budget at frame
1 770, before the guide opened at frame 2 285 — hence the higher cap here.

Result: 93 706 log lines, 26 550 rect hits, 6 581 of them inside the guide period, resolving to
**two** text-pair elements in the band:

- `f=f191-draft v=v189(d88c64a6) screen=503,470,600,504 count=6` — 408 occurrences (once per
  guide frame);
- `f=f191-draft v=v189(d88c64a6) screen≈463,410,640,587 count=6` — one element per frame, with
  sub-pixel bbox jitter (the second list line / its frame), plus
- fullscreen compositor passes (`screen=0,0,1280,720`) and a handful of `top-f-uvraw` UI draws.

No third, fourth or fifth list row is drawn in that band. Combined with
[`../roadmap-v2-guide-diag/`](../roadmap-v2-guide-diag/README.md), the port renders every guide
element the game issues on this save.

Receipt: owner save restored to `4a86756d8bf5e115…`, exact PID/start-time cleanup, real Spruce
menu verified, no cleanup warnings, no GL errors.
