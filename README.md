# West of Loathing — native Unity port for TrimUI Smart Pro (SpruceOS)

A native arm64 build of *West of Loathing* made from the Steam release (Unity 2019.4.41f2) and run
on the device's own Mali-G57 through SDL2 + KMSDRM. No emulation, no Wine, no Switch runtime: the
game's managed assemblies are compiled to IL2CPP for Android arm64 with the matching Unity player,
and a small host binary (`ua_host`) provides display, input, audio and file paths.

Included add-on: **Reckonin' at Gun Manor** — enter it from the stagecoach in **Dirtwater**.

## Status

- 46–60 fps at 1280×720 (16.6–21.5 ms average frame, p99 ≈ 23 ms), RSS 590–700 MB.
- Sound through ALSA (`plughw:0,0`), native gamepad, Steam-format saves.
- Store checks (DLC entitlement, ownership) are satisfied at the managed level — see
  [`docs/technical.md`](docs/technical.md).

## Install

Copy `port/` to `/mnt/SDCARD/Roms/PORTS/`; the launcher appears in the SpruceOS Ports menu as
**West of Loathing**. Game data is not distributed here — build it with `build.sh` and lay it out as

```
/mnt/SDCARD/Roms/PORTS/westofloathing/
  ua_host                 host runtime (arm64)
  WestofLoathing.apk      data container (Game_Data/ + manifest)
  lib/libil2cpp.so        compiled game assemblies
  Game_Data/StreamingAssets/{core,house,main_scene,...}
  data/external/          saves (save-*.json, permaflags-*.json)
```

## Build

Needs an x86_64 Linux host, the game's Steam install, and the `portmaster-unity` toolkit
(Unity 2019.4.41f2 editor + Android player, IL2CPP, Mono.Cecil).

```sh
UNITY_DATA="/path/West of Loathing_Data" ./build.sh   # patches -> IL2CPP -> apk
DEVICE=tsps ./package.sh                              # copy to the handheld
```

About five minutes on 8 cores: IL2CPP ≈ 225 s, packing ≈ 22 s.

## Saves

Copy `save-*.json` and `permaflags-*.json` from Steam (`~/.config/unity3d/Asymmetric Software/West
of Loathing` or `userdata/<id>/597220`) into `westofloathing/data/external/`. A save copied with its
original timestamp may not appear in the list — re-stamp the name (`save-<name>-<fresh ticks>.json`).

## Licence

Port code: GPL-3.0 (`LICENSE`). Game data, art and text belong to Asymmetric Publications; nothing
from the game is distributed in this repository.
