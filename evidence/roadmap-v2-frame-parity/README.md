# Frame parity — map and title screens, independent of the optimization arms

Roadmap §8 asks for map marker/title positioning to be validated independently of the
optimization work, and §9.3/§9.5 accept a GPU/visual-coherence check for the post-copy
mechanism. This report answers both from *already published* device captures: no new
run, no changed default, no re-used stale evidence.

Tool: [`tools/wol_frame_parity.py`](../../tools/wol_frame_parity.py) (stdlib PNG decode,
no game data). Raw per-pair reports are the JSON files in this directory.

## Method (and why the naive pixel-difference count is the wrong metric)

Every pixel pair is scored by the maximum per-channel delta. A **raw "differing pixels"
count is dominated by ±1 LSB dither**, which is itself random between two runs of the
*same* arm, so a raw count can label a scene as different while the picture is identical.

Two independent tests are used instead:

1. **Amplitude**: mean max-channel delta and the share of pixels above a visible
   threshold (8 levels), compared against the same-arm repeat spread.
2. **Stable-content mask**: pixels that are byte-identical across *all* control repeats.
   Anything that already varies between control repeats is animation/dither and is
   excluded explicitly rather than averaged into the verdict. The test then asks whether
   the treatment arm changes any pixel the control arm reproduces deterministically.

## Result — no parity break on content the control arm reproduces

| scene set | stable content | same-arm baseline (mean / >8) | postcopy arm on stable content (mean / >8) | verdict |
| --- | --- | --- | --- | --- |
| map, group run (`texture-id all`) | 99.475 % | 0.2112 / 0.1632 % | 0.1581 / 0.0998 % | no break |
| map, sand run (`texture-id 469`) | 93.735 % | 3.7156 / 4.3623 % | 1.7883 / 1.4523 % | no break |
| title, group run | 89.975 % | 7.5365 / 7.5559 % | 3.2492 / 2.5398 % | no break |
| title, sand run | 87.764 % | 10.2443 / 9.1082 % | 2.5169 / 1.9778 % | no break |

In all four sets the treatment arm's difference **on reproducible content is smaller than
two control runs differ from each other**. The group map set is the strongest: 99.475 % of
the frame is byte-reproducible across three control runs, and on that content the
post-copy frames differ by 0.10–0.16 levels mean with 691–920 pixels above threshold,
against a control-repeat baseline of 0.2112 levels and 0.1632 %.

The strongest deviations are small and localised, not re-layouts: on the group map the
largest clusters are text/detail areas of the drawn map (for example a 331×95 region with
3,135 changed pixels, maximum delta 26, mean 1.58) — a sub-visible shading difference
consistent with the compressed-texture round trip, not a moved or missing marker, glyph
or panel. Relocating the treatment crop by ±1–3 px does not recover the match (best-shift
match 40–80 % versus 83–100 % at zero shift), so the difference is not a positioning
offset either.

## Honest limits

- **Whole-frame raw amplitude does exceed the within-arm range** in the sand and group
  sets (for example group map: between-arm max 0.3544 mean vs within-arm max 0.2327). The
  excess sits on pixels that the control arm itself does not reproduce (animated scene
  content, dither), which is why the raw rule still prints `review`. The stable-content
  result above is the parity statement; the raw number is retained for transparency.
- The title/pause screens contain animation (same-arm baseline up to 10.2 mean levels), so
  they are a weak parity scene. The map frame in the group run is the discriminating one.
- The PBO set has one frame per arm, so no stable mask and no within-arm baseline can be
  built; those three pairs are reported as raw pairs only and carry no parity verdict.
- This validates rendering parity and marker/title **stability across arms**. It is not an
  external reference comparison against the original console/PC build, and it does not
  establish combat, travel, audio or physical-button coverage.
