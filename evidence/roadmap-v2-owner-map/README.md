# Guide screen investigation — "only Thousand Snakes Gulch in the locations list"

Owner report: after taming the horse in the gulch, the guide/map should offer travel to more
locations, but the locations list shows only Thousand Snakes Gulch. The guide was open on the
device, so it was measured directly rather than reproduced from scratch.

## 1. What the screen actually shows (OCR of the live frame, `map-now-1.png`)

| region | text |
| --- | --- |
| title, large hand-drawn | `MAKE YOUR OWN DAMNED` / `GUIDE TO` / `BORING` `SPRINGS` / `AND ITS ENVIRONS!` |
| top-left | `EXIT` |
| locations list band (x≈470–630, y≈500–570) | `Thousand` / `Snakes Gulch` — one entry |
| bottom bar | `SELECT` `GO` |
| bottom-right small element | an unreadable drawn numeral/mark (OCR: `06810`/`91890` — stylised, not reliable text) |

The screen is complete and legible: no blank rows, no black panels, no missing glyph blocks,
zero GL errors in the run.

## 2. Navigation probes — the list does not move (13 presses)

| input | result on the list |
| --- | --- |
| d-pad down ×6 | first press shifts the entry ~9 px, then invariant |
| d-pad right ×2, left ×2, up ×1 | name unchanged, list unchanged |
| analog stick down ×3, up ×3 | name unchanged, list unchanged |
| analog stick right, left | name unchanged, list unchanged |

Per-press pixel change is only ~0.3–0.5 % and always lands on the same three animated
drawing patches (x≈420–545 / 220–344 / 489–614), never on the list rows, and repeated presses
converge to zero change. So neither input scrolls a longer list: **the game offers exactly one
destination here.**

## 3. What the save knows (this is the discrepancy)

Owner save `4a86756d8bf5e115…` (progress preserved; the guide's own run restored this hash):

- `map_bsmain=1`, `map_bsgulch=1`, `map_bsfricker=1`, `map_bsmine=1`, `map_bscemetery=1` — five
  locations marked on the map;
- `unvisited_map_locations = bsfricker,bsmine,bscemetery` — three of them explicitly "known but
  not visited";
- horse progress: `tut_horse4`, `crazyhorseeyes`, `crazyhorsenose`, and the quest item
  `bag of homing oats`;
- `tut_mapreminder=1` — the game just told the player to use the map;
- `travelfrom=tut_main`, `travelto=tut_gulch` — fast travel between home and the gulch exists;
- `finishedtutorial` **absent** — this is still the tutorial chapter;
- `new_map_locations` absent (it is absent in every archived tutorial save too, including the
  horsery save).

Archived tutorial saves for comparison: `tut_main`, `tut_saloonbasement`, `tut_horsery`,
`tut_gulch` all carry `unvisited_map_locations` with 3–4 entries, so the map has held several
locations since the start of the tutorial.

## 4. Is the port dropping rows? — measured, not guessed

Two instrumented sessions opened the guide with the runtime's own diagnostics:

- `roadmap-v2-guide-diag` (`WOL_DRAW_TRACE=1`): the guide frame issues 24 text draws
  (`v189(d88c64a6)/f191-draft`, 36 draws/frame total) versus 9 text draws/frame on the world
  screen. The visible guide screen contains ~11 text elements (4 title pieces, EXIT, 2 list
  lines, SELECT, GO, plus the small numeral), i.e. the draw count matches a screen with exactly
  one two-line entry — there is no surplus of text draws that could account for four hidden
  labels, and `WOL_PROGRAM_BOUND action=placeholder-skip` runs at 14.9/frame against 20.0/frame
  on the world screen (the same accepted background rate, not a guide-specific drop).
- `roadmap-v2-guide-rect2` (`WOL_RECT_TRACE=460,485,690,595`, the list band): 6,581 traced draws
  during the guide period resolve to exactly two text-pair elements inside the band
  (`screen=503,470,600,504` and `screen≈463,410,640,587`, the latter one element per frame with
  sub-pixel jitter) plus fullscreen compositor passes. No third, fourth or fifth row is drawn.

Method note: the first attempt (`roadmap-v2-guide-rect`) exhausted its 20,000-hit cap at frame
1,770, *before* the guide opened at frame 2,285, so that trace says nothing about the guide —
kept here as the reason the cap is now raised.

## 5. Conclusion — CORRECTED 2026-10-16 after the owner's reference frame

**The earlier conclusion below was wrong and is kept only as the record of the mistake.** The
owner supplied a reference frame of the same screen showing five destinations and the drawn map;
measured against it at identical coordinates, the device frame is missing the whole panel
interior (see the region table and the UV-gate A/B further down), so the screen is *not*
"rendered exactly as the game asks".

### Measured against the reference (dark-pixel share, same coordinates)

| region | reference | device |
| --- | --- | --- |
| (B) EXIT / compass / title / bottom bar / ©1890 | 16.4 / 19.9 / 24.5 / 17.3 / 14.6 % | 19.7 / 18.7 / 23.4 / 18.3 / 16.4 % |
| Thousand Snakes Gulch (doodle+label) | 23.7 % | **0.00 %** |
| Orehole Mine + NEW | 31.6 % | **1.76 %** |
| Boring Springs Boneyard | 21.5 % | **0.00 %** |
| The Town of Boring Springs | 18.4 % | **4.48 %** |
| The Fricker Gang's Hideout | 15.0 % | **3.09 %** |
| map centre | 1.48 % | 0.00 % |

Every element drawn by the port's *translated* pair reproduces (within 1–3 points of ink); the
panel's artwork and four of five labels do not. The panel interior is plain paper (min 247, five
colours) where the reference has min 0 and 256 colours. The single visible label sits at
x471–631/y470–575, which matches no label position in the reference (its gulch label is at
x378–515/y290–343): a different layout, not a shifted copy. Inside the panel the device frame
does contain 579/1033/1164 dark pixels in the mine/town/fricker regions (drawn by the draft pairs
`top-f-uvraw/top-v-draft` texture 6936 and `f191-draft` texture 269) and zero in the gulch region,
and the `top-f-uvraw` boxes on this screen are absurd (`x=-1500…1611`, 3111 px wide) while the same
pair draws the world scene correctly.

### A/B against the UV gates (owner save restored, same route)

| arm | gulch | mine | boneyard | town | fricker | centre | title |
| --- | --- | --- | --- | --- | --- | --- | --- |
| default | 0.00 % | 1.76 % | 0.00 % | 4.48 % | 3.09 % | 0.00 % | 23.99 % |
| `WOL_TOP_UV=raw` | 0.00 % | 1.76 % | 0.00 % | 4.50 % | 3.09 % | 0.00 % | 23.99 % |
| `WOL_TOP_UV=legacy` | 0.00 % | 1.76 % | 0.00 % | 4.48 % | 1.38 % | 0.00 % | 23.99 % |

Neither gate restores the panel content — see [`../roadmap-v2-guide-uvab/`](../roadmap-v2-guide-uvab/README.md).

### Still open

Whether the game under the port issues five label draws whose fragments fail, or fewer. The rect
filter used here (`count<=96`, single-quad text) reliably catches single-quad text elements — it
found the visible label once per frame and no label-sized draw at any reference label position —
but it cannot see a multi-quad label. **Next step:** rebuild with the size filter removed and list
every draw in the panel band with its pair, bbox and texture; that names either the missing label
class or proves the game issues one label, and the measured `top-f-uvraw` scale anomaly is the
first thing to compare against the working world-screen draws of the same pair.

## 5b. The superseded conclusion (recorded, not deleted)

**Claimed then, now withdrawn:** "the port draws the guide screen the game asks for; the single
destination is the game's own content in this save". The premise it rested on was a rect trace
whose band `460,485,690,595` covered only the one visible label — the reference's other labels sit
outside that band (x>690, or y<485) — and a text-draw count that assumed the visible ~11 text
elements, an assumption the reference frame disproves. The save's five `map_*` flags, three
`unvisited_map_locations` and the reference frame all point the other way.
