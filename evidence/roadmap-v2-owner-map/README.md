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

## 5. Conclusion and what would settle it

**Measured:** the port draws the guide screen the game asks for; the single destination is the
game's own content in this save, not a dropped or misplaced draw, and no input scrolls a hidden
list. The discrepancy is between the save's five marked locations and the guide's one
destination.

**Not proven:** whether the real game's guide should list more at this exact progress. The
tutorial is unfinished, and the guide may legitimately gate travel until the tutorial chapter
ends or until the horse is actually called (the quest item `bag of homing oats` is present).
That is a game-content question, and the evidence here cannot decide it.

**Discriminating next steps:** (a) a reference frame of the same guide at the same progress
from the real game, or (b) call the horse with the homing oats and re-open the guide — if
destinations appear, the guide gates on the horse being present and there is no defect.
