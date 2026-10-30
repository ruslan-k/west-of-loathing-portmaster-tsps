# Host-side conversion: route B builds in seconds, not hours (2026-10-30)

The device setup repeats work the host can do. All three steps run here, on the Steam data
(Unity 2019.4.41f2), and the handheld only installs the result.

| step | command | measured |
|---|---|---|
| 3 convert | `pmunity convert <data> --config convert.json --set quality.profile=handheld` | **8.7 s** |
| 2 IL2CPP | `pmunity il2cpp <data> lib/arm64-v8a --abi arm64-v8a --pkg <player>` | **227 s** (warm caches) |
| 4 pack | `pmunity android-data --src <converted> --il2cpp <il2cpp> --pack all --streaming-assets both` | **26 s** |

Result: `libil2cpp.so` 54.0 MiB (metadata v24), `WestofLoathing.apk` 264 MiB, `Game_Data` 248 MiB —
527 MiB installed, versus "one to a few hours" for the on-device compile.

## Why `android-data` exited 1 with no message

It raises `SystemExit('MonoManager lists assemblies missing from Managed/: [...]')` and the message
lands in `<out>/make_android_data.log`, not stdout. The Steam build's `globalgamemanagers` names
`Kartridge.dll`, which the Steam install does not ship (Kartridge is dead). `--drop-missing-assembly`
cannot help with `--il2cpp`: with IL2CPP the accepted set is `il2cpp.json`'s own assembly list, so the
name must exist **at IL2CPP time**.

Fix: an empty assembly named `Kartridge` (tools/stubasm) placed in `Managed/` before
`pmunity il2cpp`. The game code has no references to it — `Assembly-CSharp` only carries the
`PLATFORMKARTRIDGE` define and one string — so the stub is never called, but the name resolves.

## Patch set that goes into the IL2CPP build

Applied in **one** Cecil pass (tools/dlcpatch), because a second pass over an assembly Cecil already
wrote yields a 0-byte file:

- `com.rlabrecque.steamworks.net.dll`: `SteamApps.GetDLCCount` → 1, `BIsDlcInstalled` → true (DLC);
- `Assembly-CSharp.dll`: `Rewired.Utils.ExternalTools.LinuxInput_*` stubbed (IL2CPP 2019.4 otherwise
  aborts with `NullReferenceException` in `MethodBodyWriter.GetMethodCallExpression`).

`asmpatch` adds `rewired-android` (platform Linux → Android) and `streaming-assets`
(`AssetBundleManager` → `Game_Data/StreamingAssets/`); its output cannot be patched again, so the
order is asmpatch first, then dlcpatch on a full `Managed` copy that includes asmpatch's files.

## Installed layout

`ports/wol-il2cpp/` = launcher + `wol-il2cpp/` with `lib/{libmain.so,libunity.so,libil2cpp.so}`,
`WestofLoathing.apk`, `Game_Data/`, `assets/`, `android_package.json`, `plugins.map` and the
`.setup_done` marker, so the setup has nothing left to do.
