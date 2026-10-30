# Current port layout — West of Loathing

Target: **TrimUI Smart Pro S, SpruceOS, ARM64**. This is the promoted Unity/Mono build, not the old Switch runtime.

```text
West of Loathing.sh
westofloathing/
  ua_host                    native ARM64 host with legacy-FMOD audio output
  bounded_run.py             optional explicitly requested diagnostic deadline
  lib/
    libil2cpp.so              generic Mono bridge, not game code
    libmonobdwgc-2.0.so       generic ARM64 Mono runtime
    libMonoPosixHelper.so
  licenses/
  runtime-manifest.json      SHA-256 and upstream identities
```

**Mandatory update + DLC release gate:** this installed Unity/Mono layout has sound and packaged Gun Manor assets, but its original owner Linux game's **content-update version** is not pinned or proven equivalent to the requested Switch `v327680`; ordinary Dirtwater→ghost-carriage→Gun Manor entry and cold save/reload have not passed. [Track A3](../evidence/unity-trackA-2026-10-30/README.md) measures 41.4–41.6 host FPS with audio over 90s, **not** updated+DLC gameplay. Do **not** represent this folder as a verified complete updated+DLC release until the [release gate](../docs/release-gate-update-dlc-2026-10-30.md) is fully met. The exact Switch v327680 binary and PC Mono data are not interchangeable.


## Owner-only files to add

Use the output of [`../tools/unity/prepare_packed.py`](../tools/unity/README.md) and the exact **Unity 2017.4.19f1 ARM64 IL2CPP player**:

- Copy the contents of the packer's `android/zip/` directory into `westofloathing/`: `WestOfLoathing.apk`, `android_package.json`, `plugins.map`, and the small loose Mono configuration tree `assets/`.
- Add `libmain.so` and `libunity.so` from `player/Variations/il2cpp/Release/Libs/arm64-v8a/` to `westofloathing/lib/`.
- Do not replace the included generic `libil2cpp.so` bridge with the player's IL2CPP library.
- Do not add old Switch `.seg`/RomFS files. There is no loose `Game_Data/StreamingAssets` copy: base and DLC bundles live inside the one aligned STORE APK.

The game/DLC files, Unity engine libraries and prepared APK are proprietary owner-local inputs and must not be committed or distributed through this repository.

## Install and update

Copy **West of Loathing.sh** and **westofloathing/** to `/mnt/SDCARD/Roms/PORTS/`. Launch **West of Loathing** from the Spruce Ports menu. This launcher deliberately targets the verified TSPS/Spruce library/display/audio path; it is not advertised as a universal firmware launcher.

Saves: `westofloathing/data/external/`. Preferences/cache: `westofloathing/data/`; configuration: `westofloathing/home/`. Preserve both `data/` and `home/` across updates. Logs: `westofloathing/logs/latest.log`.

The device promotion renamed the accepted folder rather than recreating it. Older builds/launchers were removed only after their save files were preserved separately under `/mnt/SDCARD/Saves/West of Loathing/legacy-before-unity-promotion/`. Legacy Switch saves were not merged into or substituted for the current Unity progress.

## Verified scope / limits

Title, base interiors and Gun Manor rendered on real TSPS KMS; audible output is owner-confirmed after the audio-only runtime fix. The post-rename launcher and file/save hashes are checked without starting a new game session. Normal DLC quest entry, full cold save/load and endurance remain separate acceptance gates. Memory pressure and prior unexplained unattended progression are not claimed solved.

Controls retain the accepted native TRIMUI Player1 map; A/B follow in-game prompts, D-pad/sticks are native, Start maps to Escape. No additional keyboard mapper is started. A complete button-by-button physical audit is still open.
