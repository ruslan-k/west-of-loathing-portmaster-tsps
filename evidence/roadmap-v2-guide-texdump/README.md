# Guide screen: dump of the screen's own textures + the per-texture UV A/B

## Which draw classes belong to the guide screen

Comparing every (pair, vertex count, sampled texture) class of the world period against the guide
period in the same run (`roadmap-v2-guide-rect4`) gives the guide-only classes (per frame,
0.65 ≈ once per frame):

| class | per frame | note |
| --- | --- | --- |
| `f08bad2f#a9b0/f309b86a#0184` count=6 sampling 3618 / 3619 / 3620 | 0.65 each | the guide-only 960×540 → 480×270 → 240×135 target chain composited back with the translated pair |
| `f191-draft/v189` count=126 sampling 3233 | 0.65 | the one visible label (473,510→631,569) |
| `f191-draft/v189` count=108 sampling 3212, count=84 sampling 3233, count=60, count=12 sampling 43/3213/3223/3222, count=18 sampling 2932 | 0.65 each | the guide's own art/text draws; their transformed boxes span the whole screen (250,12→743,717 / 256,−66→895,700 / 400,439→1535,985) |
| `top-f-uvraw/top-v-draft` count=189 sampling 543 | 0.24 | guide-only scene-layer draw |

The world-scene classes (sampling 2935/2939/2941 with counts 828/963/750/576) appear in *both*
periods, i.e. the world keeps being drawn behind the panel.

## The guide's own textures, dumped

`WOL_TEXDUMP_GLNAME=139,166,165,153,147` during a guide run wrote five PAMs of the guide's own
atlas pages (GL names → nvn ids at that moment):

| dumped file | size | content |
| --- | --- | --- |
| `wol-gln-165-id24497-1024x1024.pam` | 1024×1024 | **the guide page as it exists in the port's GL state**: the title band ("MAKE YOUR OWN DAMNED GUIDE TO / BORING SPRINGS / AND ITS ENVIRONS!") plus the panel border lines — interior empty (mean luminance 245.9, 810 colours) |
| `wol-gln-139-id24495-238x238.pam` | 238×238 | mostly transparent (10.7 % alpha>0), no readable text |
| `wol-gln-153-id24505-256x256.pam` | 256×256 | mostly transparent (16.2 % alpha>0), no readable text |
| `wol-gln-166-id24496-300x300.pam` | 300×300 | 16 colours, 9.8 % alpha>0, no readable text |
| `wol-gln-139-id510-469x419.pam` | 469×419 | 6.2 % alpha>0, no readable text |

The page texture is the important one: the *game's own* rendered page, as produced by the port,
has an empty panel interior — so the missing map and labels are not a composited layer that fails
to reach the screen; the translated output itself is empty.

## A/B: per-texture UV fold for the guide's own ids

`WOL_F191_NOFOLDID` and `WOL_TOP_RAWID` set to the guide's atlas ids
(`3212,3213,3214,3223,3233,24495,24496,24497,24505,510`), one guide run, owner save restored:

| region | reference | default | nofold+rawid |
| --- | --- | --- | --- |
| gulch | 23.71 % | 0.00 % | 0.00 % |
| mine | 31.64 % | 1.76 % | 1.76 % |
| boneyard | 21.54 % | 0.00 % | 0.00 % |
| town | 18.39 % | 4.50 % | 4.53 % |
| fricker | 14.99 % | 3.09 % | 3.09 % |
| centre | 1.48 % | 0.00 % | 0.00 % |
| title | 25.94 % | 23.99 % | 23.99 % |
| panel interior | 9.95 % | 2.12 % | 2.12 % |

No change. Neither the global UV modes (previous commit) nor the per-texture fold lists recover the
panel, so the surviving candidate is the translation of the guide's own draw classes themselves.

## Next measurement (concrete)

Dump the vertex data, UVs and the c3 constant bank of the guide's own classes
(`WOL_VDATA=f191`/`=top` on the guide route, `WOL_VDATA_STRIDE` to isolate) and compare them with the
same pairs' draws that render correctly on the world screen. That distinguishes a broken transform
(positions/UVs send the quads off-panel or outside the atlas) from a broken sampler state, and both
are fixable inside the existing catalogue rather than by another global switch.
