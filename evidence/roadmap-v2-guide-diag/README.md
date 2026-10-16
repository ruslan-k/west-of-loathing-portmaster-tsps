# Guide screen with per-draw tracing (`WOL_DRAW_TRACE=1`)

Purpose: decide whether the port drops location rows on the guide screen, by counting what the
game actually asks to draw.

Method: the route opens the guide once (`ZL`, 180 ms) on the owner's restored save
(`4a86756d8bf5e115…`, features off, runtime `0cca40eca762c984…`) with the runtime's verbose
draw trace enabled through `session.py` (`--draw-trace` on the probe). Owner save, section,
launcher and layout hashes are in `receipt.json`; the effective environment is in
`effective-env.json`; the log is the complete `runtime.log.gz`.

Result: 2635 frames, 658 628 log lines, 109 314 traced draws.

| screen window (by frame index) | frames | draws/frame | of which text pair `v189(d88c64a6)/f191-draft` | `placeholder-skip`/frame |
| --- | --- | --- | --- | --- |
| world (game-idle → guide-open) | 702 | 43.0 | 9.0 | 20.0 |
| guide (guide-open → end) | 554 | 36.0 | 18.6 (24 distinct text draws per median frame) | 14.9 |

The guide frame's 24 distinct text draws resolve into one large hand-drawn title draw
(522 vertices), a few medium blocks and small strings — the shape and number expected for the
~11 text elements that are visible on the captured frame (`guide-open.png`), including a single
two-line location entry. There is no surplus of text draws that four hidden labels could use,
and the skipped-program rate is not guide-specific (it is *lower* than on the world screen).

Caveat: a mutually exclusive alternative would be location labels drawn as part of a texture
rather than as text draws; the frame itself shows no blank paper areas where labels would sit,
and the separate rect-filtered run
([`../roadmap-v2-guide-rect2/`](../roadmap-v2-guide-rect2/README.md)) enumerates every draw whose
box intersects the list band, with the same conclusion.
