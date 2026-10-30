# Technical notes

Everything below was verified on the device (TrimUI Smart Pro, SpruceOS, Mali-G57, GLES 3.2).

## 1. Source

Steam install, Unity **2019.4.41f2** (`UnityPlayer.so` → `2019.4.41f2_6b23d448b533`). The game ships
its content as assets bundles in `West of Loathing_Data/StreamingAssets`:

| file | size | note |
|---|---|---|
| `core` | 187,391,253 | base game |
| `house` | 57,615,719 | **Gun Manor DLC** |
| `main_scene` | 12,245,045 | 9 custom shaders, GLES programs missing |

The old 2018 Android port used Unity 2017.4 data; the 2019 Steam data is what this port builds from.

## 2. Pipeline

```sh
pmunity convert       # Unity data -> Android layout (textures -> ASTC, dimensions and mips kept)
dlcpatch              # managed patches (Mono.Cecil), see §3
asmpatch              # Rewired platform + StreamingAssets path
stubasm Kartridge     # empty assembly the Android data step expects
il2cpp                # 2019.4.41f2 editor -> libil2cpp.so (arm64, metadata v24, 20 data files)
android-data --pack   # Game_Data + apk
```

`libil2cpp.so` is 54 MiB. Timings: convert 8.7 s, IL2CPP 221–227 s, pack 21–26 s.

## 3. Managed patches (`tools/dlcpatch`)

One Mono.Cecil pass per assembly — a second pass over an already written assembly produces a
zero-byte file.

`com.rlabrecque.steamworks.net.dll` (stub Steam client, 9 methods):

- `GetDLCCount` → 1, `BIsDlcInstalled` / `BIsSubscribed` / `BIsSubscribedApp` / `BIsAppInstalled` → true
- `BGetDLCDataByIndex` → returns true, fills app id, `available = true`, name `Reckonin' at Gun Manor`

`Assembly-CSharp.dll`:

- `DLC.FHasDlc(string)` → true. This is the gate the save loader asks; the stub client never fires
  Steam's `DlcInstalled_t` callback, so without it a save made with the add-on refuses to load with
  "Requires DLC … content isn't loaded".
- `Rewired.Utils.ExternalTools.LinuxInput_*` stubbed — the Linux input path throws a
  `NullReferenceException` inside IL2CPP's `MethodBodyWriter`.
- `AssetBundleManager.FTryLoadAssetBundleInternal` → loads from `Game_Data/StreamingAssets/`
  beside the APK.

## 4. Runtime (`ua_host`)

- Display: SDL2 KMSDRM, 1280×720@60, swap interval 1; no X, no compositor.
- Input: SDL gamepad (X360 profile), mapped by the launcher's `SDL_GAMECONTROLLERCONFIG`.
- Audio: Unity 2019+ does not use OpenSL ES. `org.fmod.FMODAudioDevice` mixes inside
  `runtime/jni/up_input.c:fmod_thread()` and hands PCM to `UPC.on_audio`; `ua_host` sets
  `cfg.on_audio` and writes to `aplay -q -t raw -f S16_LE -r 48000 -c 2 -D plughw:0,0`, unbuffered.
  Two sinks at once leave ALSA in `PREPARED` and silence the game — keep exactly one
  (`UA_AUDIO_SINK=pipe`).
- Saves and settings: `data/external/` (the game's persistent data path).

## 5. Shaders and textures

`main_scene` carries 9 custom shaders without GLES programs. Re-saving the bundle with UnityPy and
its textures breaks bootstrap (`no instance of WestOfLoathing was found`); rewriting **only** the
shader objects (`platforms: [9, 15, 18]`) keeps all 593 GameObjects / 885 MonoBehaviours and works.
Texture conversion must not rescale sprites — `scale=0.5` decouples atlas coordinates from metadata
("0 sprites follow their scaled textures"); ASTC at original size is correct.

## 6. Benchmarks

| state | fps | frame avg | p99 | RSS |
|---|---|---|---|---|
| character creation | 51.6 | 19.4 ms | — | 705–718 MB |
| after scene load (pre-fix) | 43.5 | 23.0 ms | 359 ms | — |
| textures + shaders fixed | 50–54 | 18–20 ms | ~23 ms | 665–676 MB |
| with audio fixed | 60.1 | 16.6 ms | 20.4 ms | 590 MB |
| Dirtwater (DLC town) | 46.5 | 21.5 ms | 23.5 ms | 693 MB |

Scene loads drop to ~20 fps with p99 ≈ 190 ms — that is loading, not gameplay.

## 7. Build-host pitfalls

- `/home` is a symlink to `/var/home` here; the IL2CPP tooling mounts the real path but runs
  commands with the argument as written. Pass realpaths and set
  `PMUNITY_IL2CPP_HOME=/var/home/<user>/.cache/pmunity/il2cpp`.
- A truncated Unity editor cache keeps its `.complete` marker: symptom is
  `Cannot open assembly '…/net471/UnityLinker.exe'`. Delete `editor/` and re-download.
- `android-data` fails silently on assemblies missing from `Managed/` (the Steam data lists
  `Kartridge.dll`); the message goes to `<out>/make_android_data.log`.
