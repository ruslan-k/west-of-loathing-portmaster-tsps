# port/

What goes on the SD card:

```
port/
  West of Loathing.sh     launcher (SpruceOS Ports menu)
  westofloathing/         game directory, filled from the build output
```

`westofloathing/` after `build.sh` + `package.sh`:

```
ua_host                   host runtime (arm64)
WestofLoathing.apk        data container: Game_Data/ + manifest
lib/libil2cpp.so          compiled game assemblies
Game_Data/StreamingAssets core, house (DLC), main_scene, …
data/external/            saves and settings — do not replace when updating
```

The launcher switches the panel to KMSDRM, stops MainUI so it does not hold the display and the
ALSA device, runs `ua_host`, and brings MainUI back on exit. Its log is `westofloathing/log.txt`.

Environment: `SDL_AUDIODRIVER=alsa`, `AUDIODEV=plughw:0,0`, `UA_AUDIO_SINK=pipe` (one sink only —
two leave ALSA in `PREPARED` and the game goes silent).
