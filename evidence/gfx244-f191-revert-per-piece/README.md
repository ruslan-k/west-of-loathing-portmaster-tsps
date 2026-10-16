# gfx243 — f191 revert + per-piece UV with darkness metric and batch guard (build-243)

The user-visible round: WANTED poster figure, HUD control icons, the room's bed/gramophone
regression, the bird cage, and the farm player's missing body.

## What was wrong (measured)
1. build-237 flipped the f191 family default from halfgt (7) to halfcomp (8) during the
   farm experiments. The device-verified state (gfx254/257/259/261) is halfgt. Under
   halfcomp the WANTED poster figure regressed and the top-right control icons broke.
   -> reverted: `if(!o||!*o)uv2_mode=7;` (WOL_F191_UV=halfcomp keeps the variant).
2. One atlas serves pieces with OPPOSITE uv-scale needs: measured on texture 322 - the
   same texture had a piece with art at the raw coords (alpha 254 at raw vs 34 at half)
   and pieces with art only at the halved coords (211/9.0 vs ~0). A per-TEXTURE decision
   is therefore insufficient.
3. The first per-piece attempt (build-242) regressed the room: the bed and the gramophone
   disappeared. Two causes found and fixed in 243:
   a. the ink metric was a*(0.25+0.75*luma): white backgrounds score ~1.0 and DARK LINES
      score LOW, so on white-background sheets both sides scored alike (tie -> raw). The
      metric is now darkness-weighted: a*(0.2+0.8*(1-luma)) - lines positive, transparent
      zero, white low.
   b. draws that batch several quads span a huge uv area; a single union rect is invalid.
      build-243 adds a compactness guard: span > 0.6 falls back to the texture-level
      centre probe (cached), pieces with compact rects get the per-piece decision.

## Build-243 behaviour (measured on the device)
- WANTED poster figure: complete stick body (diamond torso, arms, legs) - see
  title-243-wanted-poster-complete.png (title screen after the revert).
- Room: the bed and the gramophone are back - room-243-bed-gramophone-back.png.
- The bird cage (lower-right foreground, dome cage + bird on a tripod): STILL renders as
  a dark blob, bars/bird missing - open item, next round (candidate: its draws are
  batched -> the guard sends them to the texture-level probe; the per-quad path or a
  draw split may be required). Reference: ref-room-wiki.png (wiki screenshot) and
  ref-cage-zoom.png.
- Farm player (cowlick, diamond torso): still unverified under 243 - the controlled
  session lost its input (stale buttons sock) and only captured the title. Old A/B:
  player-ref-vs-live.png (REF vs broken).

## Logs
- s242-decisions.txt: the failed per-piece attempt (build-242), 92 decisions.
- s243-decisions.txt: build-243, 71 decisions; compact pieces get piece:raw/piece:half
  (e.g. 322 half 16.20 vs raw 6.19), thin strips decided correctly (321: 45.72 vs 23.92
  on a 0.002-wide rect), batching draws routed to probe:* by the guard.
