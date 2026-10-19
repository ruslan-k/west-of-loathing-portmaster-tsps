# Scene coverage attempts — guide-map travel and the town approach (nav1–nav4)

Purpose (§16.3 step 3): extend beyond the gulch moving/map/pause coverage of `../accept-720/`
toward interior, dialogue and battle scenes. Profile: frozen ELF
`b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158`, `WOL_UPRENDER_720=1`, all
other experimentals OFF, stock clocks; owned probe runs (adaptive watchdog 5 s settled /
30 s transitions), saves restored and Spruce verified after every run. Route files are pinned
next to this README; each run's captures, receipt and log are in its subdirectory.

## Mapping facts measured (input-injection)

- ZL (`0x100`) opens/closes the guide map (every run).
- dpad moves the map selection ring; A (`0x1`) confirms/GO; B (`0x2`) closes menus.
- **L (`0x40`) opens the character sheet** (INFO/YOURSELF/FILTERS) — it is NOT a map selector
  despite the map's own "L SELECT" legend (nav2 lost the whole route to this).
- The ring path is deterministic: from the opening state (Thousand Snakes Gulch),
  right → down lands exactly on **The Town of Boring Springs** (nav1 and nav3 agree).

## Attempts

- **nav1** (`route-nav-town.json`): opened the map, moved right→down→right→down, pressed A with
  the ring in empty space (two moves past the town) → no travel; the map stayed open and the
  later "walks" only moved the ring. Lesson: capture-verify the ring position before GO.
- **nav2** (`route-nav-town2.json`): pressed L before A → the character sheet opened and
  consumed the rest of the route; no travel.
- **nav3** (`route-nav-town3.json`): right→down onto the Town, then A **immediately** → the map
  closed and the scene changed: the captures show a different, recognizable area — the
  **B.S. Horsery building (closed double doors)**, a windmill, cacti and an armadillo critter
  (the Boring Springs approach), ~294–341 k px different from both the gulch world and the
  map-over-gulch frames. A presses at the walk positions opened nothing in that run.
- **nav4** (`route-nav-town4.json`): repeats the successful travel, then walks toward the
  Horsery doors with six bounded A attempts — result: **pending at this checkpoint**.

## Status

Moving world + map/return + pause are covered by `../accept-720/`. The town approach was
reached in nav3. Interior/dialogue/battle remain **not yet captured**; if the nav4 door
attempts fail, the correct owner action per §16.3 is to supply a known interior/battle save
or route rather than widening blind input scripts.
