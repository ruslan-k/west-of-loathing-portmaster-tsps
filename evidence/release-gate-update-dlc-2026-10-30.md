# Release gate — update v327680 + DLC (evidence collected 2026-10-30)

## What is on disk (owner downloads, untouched)

| Component | Title ID | Bytes | SHA-256 (first 16) |
|---|---|---:|---|
| Base | `010031B00A4E8000` | 189,489,662 | `661fadace6651945` |
| Update v327680 | `010031B00A4E8800` | 191,276,836 | `30a49313f16ab3eb` |
| DLC Reckonin' at Gun Manor | `010031B00A4E9001` | 54,075,853 | `87fec07678047df4` |

## What the Horizon probe image mounts

On the device (`/mnt/SDCARD/Roms/PORTS/wol-update-probe-20261028`):

| File | Bytes | SHA-256 (first 16) | Meaning |
|---|---:|---|---|
| `main.text.seg` | 35,439,544 | `f8400de0…` (pinned) | v327680 program, Unity 2019.4 |
| `wol-romfs.section` | 271,164,164 | `ecab0ad27889a320` | merged **update + house (DLC)** RomFS |
| `wol-house.romfs` | 58,907,880 | `e04ecb656771280d` | DLC payload |

The runtime advertises the DLC only for that exact merged section hash
(`ipc.h`, `WOL_AOC_HOUSE` block, gated on `ecab0ad2…`). The device hash matches, and the guest
received an installed add-on at runtime:

```
WOL_AOC_CONTENT command=2 installed=1 index=1 returned=1 source=verified-merged-section
WOL_AOC_CONTENT command=3 installed=1 index=1 returned=1 source=verified-merged-section
WOL_AOC_CONTENT command=7 installed=1 index=1 returned=1 source=verified-merged-section
```

8 such receipts in `baseline-da-on2` (`evidence/horizon-h2-2026-10-30/`). So update **and** DLC are
wired into the image and reported to the game as owned.

## Not yet confirmed

- Entering Gun Manor from the world map (needs a play test).
- 30 fps during movement and inside the DLC: the current build is 42.9 ms / ~23 fps.

## Negative result recorded today (render scale)

`WOL_UPRENDER24_SCALE=1` now genuinely rewrites the guest's Screen answers
(`site=width screen=1280 used=960`, `site=height screen=720 used=540`, 45 receipts), but both arms
(`sc2`, `sc2b`) exit before gameplay:

```
T2_MEMORY_FLOOR_HIT available-MiB=22 floor-MiB=24 swap-free-MiB=1632 action=exit
WOL_RUNTIME_EXIT status=26
```

No `NVN_PROFILE` window was produced, so the resolution lever gives **no fps number** and cannot be
evaluated until the memory floor stops being hit. It is not a path to 30 fps on its own.
