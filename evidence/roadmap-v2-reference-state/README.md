# Reference state check against the owner's own desktop saves

The owner pointed out that this machine hosts the desktop Steam build of West of Loathing
(app 597220, `~/.local/share/Steam/steamapps/common/West of Loathing`) and their own real-game
saves (`~/.config/unity3d/Asymmetric Software/West of Loathing`). Those saves are an independent
reference for what the game's state looks like at each progress point, and they settle one half of
the guide question without touching the port at all.

## Save format is the same as the port's

Both the desktop saves and the port's save are `PLAYER{flags,dailyflags,items,gear,effects,skills,
stores,properties}` plus a top-level `WAA_ID`. Same field names, same file naming
(`save-<name>-<id>.json`, `permaflags*.json`). The desktop build therefore reads a save written by
the Switch build (verified below) — which is what makes a same-save reference test possible.

## What the owner's saves show about the map state

Progression across the owner's own save history (read-only, analysed locally, saves not committed):

| played | location | `map_*` flags | notes |
| --- | --- | --- | --- |
| 00:00 | — | 0 | fresh profile |
| 00:28 (`tut_main`) | house | **5** — `bsmain,bsgulch,bsmine,bscemetery,bsfricker` | `unvisited = bsfricker,bscemetery,bsgulch` |
| 00:59 (`tut_main`) | house | 5 | `unvisited` empty |
| 01:24 | `house_lab` | 3 (different map: `cemetery1,dirtwater,railcamp`) | tutorial finished |
| 02:27 … 09:59 | many | 7 → 15 → 17 → 23 → 28 → 33 → 37 → 38 → 42 → 46 → 49 → 51 | `unvisited_map_locations` shrinks as locations are visited |
| 10:52 | `cemetery1` | 51 | current profile |

The port's save (`4a86756d8bf5e115…`, `tut_gulch`, played 05:10) carries **exactly the same five
`bs*` flags** as the owner's own tutorial-stage save, with `unvisited = bsfricker,bsmine,bscemetery`
and an unfinished tutorial. So the map state on the device is an ordinary early-game state, not a
field the port mangled, and the YouTube reference frame the owner supplied is from a mature profile
(the later saves here reach 51 locations, which is the density the reference frame shows).

## What this does not settle

Whether the *real* game, on this save, lists more than one destination in the guide. The desktop
build was started several times with the port's save: it registers it (its own permaflags writes
`"LAST_SAVED":"save-Wynona Carson-639274980123448959"`), the title screen shows CONTINUE /
character / SWITCH CHARACTER / NEW GAME / OPTIONS / QUIT — but the in-game menu could not be driven
to the map screen from this session (the headless X instance ignores synthetic input without a
window manager; in the Steam/gamescope session an injected Return reached the game while pointer
clicks did not). Forcing it would have meant editing the owner's Steam configuration or their
permaflags, which was not done.

Prepared for a one-minute check by the owner:
`~/Downloads/WoL-reference-test/` — the port's save (sha256 `4a86756d…`, identical to the
device-restored owner save) plus `README.txt` with the copy step, the pre-test backup path
(`…/scratch/wol-desktop-saves-backup-20261016-235036`) and the question being asked.
