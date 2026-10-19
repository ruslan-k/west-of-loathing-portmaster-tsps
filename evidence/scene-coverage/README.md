# Scene coverage attempts — guide-map travel and the town approach (nav1–nav5b)

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
  map-over-gulch frames.
- **nav4** (`route-nav-town4.json`): repeated the travel, walked further (the **BAR** building
  comes into view; the player position changes across frames) and pressed A at six different
  positions — **no interior, dialogue or shop opened**; the doors stayed static.
- **nav5** (`route-nav-town5.json`): another door hunt; the run **died before any route input**
  with a runtime fail-closed guard stop (see below).
- **nav5b** (`route-nav-town5.json`, identical repeat): clean full-route run (no STOP, 173
  progress checks, 5,906 frames) — the nav5 guard stop **did not reproduce** (1/18 in this ELF
  series). The town center is now visible with more buildings (**B.S. HOTEL, HORSERY, BAR,
  TRADE, ALICE M.D. — CLOSED**), and `d1-interact` opened a real **text box**: “Nope. You're
  not allowed in Topeka anymore, remember? [By the way, you can use the ZL or - buttons to
  open your map and travel to new locations you've discovered.]” — the first interactive
  dialogue captured in these attempts (it also confirms ZL as the map/travel button in-game).

## nav5 runtime guard stop — fact sheet

- `STOP status=NVN_COMMAND_RECORD_SIZE pc=main.text.seg+0xaf2c0c detail=0x0` →
  `WOL_RUNTIME_EXIT status=24`. The guard lives in `native/nvn_commands.h`
  (`nvn_command_decode`: prefix must satisfy `80 <= bytes <= sizeof(*r)` and `bytes % 16 == 0`,
  and the decoded shape must equal the declared size; `detail=0x0` means the record prefix read
  as **bytes=0**).
- Timing: **~0.9 s after entering gameplay** (31 frames after the `game-idle` stage marker),
  before the first route action; final frame gaps were normal (28–29 ms), then frames stopped
  outright (a hard stop, not a decay).
- Memory at the moment was **not** under stress: Pss 492 MB, SwapPss 445 MB, MemAvailable
  73 MB, major faults flat (12,280), Mali commit 243 MB — measured by the 2 s ledger.
- The runtime log preserved the full `MOMO_THREAD` census (threads parked on
  `sdk.text.seg+0xa9d5c` keys) and the `NVN_COMMANDS_RECORDED` state of the active command
  buffer (handle 2105, 410 commands, `replay-pending=1`) at the failure.
- Two seconds before death the log shows SDK SVC bursts (`id=0x1a/0x1b`) from threads 0/5 —
  the command record/replay path was active when the decode hit the zero-size record.
- The 5 s settled watchdog caught the event and recorded `presentation-stall`
  (frame 2104, age 5.099 s). Its bounded proc diagnostics reported
  `diagnostic_error: /proc/<pid>/stat missing` — expected pairing, because the runtime had
  already exited; the log's STOP line + census are the primary evidence.
- Saves restored, Spruce recovered, zero cleanup warnings.
- History scan: this exact guard (`NVN_COMMAND_RECORD_SIZE`) appears in **none** of the
  collected repo logs or the spike run logs; related fail-closed NVN guards
  (`NVN_COMMAND_RECORD_STORAGE`, `NVN_COMMAND_ARENA_OVERLAP`, `NVN_TEXTURE_SWIZZLE_REQUIRED`,
  `NVN_GUEST_POINTER`) each appear a handful of times across the older history. It was the
  17th run of this exact ELF in the current series (16 clean); the identical repeat `nav5b`
  was clean as well — **not reproduced, rate 1/18**. Treat as a rare intermittent
  runtime-integrity event; if it recurs, instrument the command-record path
  (`T2_LIST_RANGES=verify` as the first falsification A/B against the ranges fast-path, which
  is active — `mode=ranges`).

## Status

Moving world + map/return + pause are covered by `../accept-720/`. The town approach and town
center were reached (nav3/nav4/nav5b: Horsery, BAR, TRADE, HOTEL, ALICE M.D.; player movement
confirmed), and one **sign/dialogue text box** was captured (nav5b `d1-interact`). **Interior
and battle are not yet captured** — the door-entry attempts failed, so per §16.3 the correct
next input is an owner-supplied known interior/battle save or route rather than wider blind
input scripts. The nav5 guard stop is a separate rare runtime-integrity observation
(not reproduced; see the fact sheet).
