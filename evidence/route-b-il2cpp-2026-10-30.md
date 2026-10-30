# Route B, IL2CPP arm64 — first successful build (2026-10-30)

Follow-up to `route-b-build-log-2026-10-30.md`. The `android` route is impossible on TSPS
(`uname -m` = aarch64, no `/lib/ld-linux-armhf.so.3`), so the build went through
`pmunity il2cpp --abi arm64-v8a` instead.

## What now works

```
UnityLinker  -> OK
il2cpp.exe   -> OK (172 C++ translation units)
NDK compile  -> OK
libil2cpp.so -> 54.0 MiB, metadata version 24, 20 data files
```

Inputs: Steam `West of Loathing_Data` (Unity 2019.4.41f2, Mono), Android player package
2019.4.41f2 as `--pkg`, and two managed patches applied in one Cecil pass:

- `com.rlabrecque.steamworks.net.dll` — `SteamApps.GetDLCCount` → 1, `BIsDlcInstalled` → true
  (DLC entitlement without a Steam client);
- `Assembly-CSharp.dll` — `Rewired.Utils.ExternalTools.LinuxInput_*` bodies stubbed. IL2CPP 2019.4
  aborts on `LinuxInput_IsJoystickPreconfigured` with `NullReferenceException` in
  `MethodBodyWriter.GetMethodCallExpression`; the Android player never calls the Linux path.

## Traps found on this host (cost hours each)

- **`/home/ruslan` is a symlink to `/var/home/ruslan`.** `pmunity` mounts realpaths but runs commands
  with the paths as given, so every tool inside the container saw `No such file or directory`
  (`Cannot open assembly .../UnityLinker.exe`). Fix: pass realpaths everywhere and set
  `PMUNITY_IL2CPP_HOME=/var/home/ruslan/.cache/pmunity/il2cpp`.
- The toolchain cache can hold `editor/.complete` with a truncated tree (46 MB, no `UnityLinker.exe`);
  delete `editor/` to force a re-fetch (Unity Editor installer, 1.89 GB).
- Cecil **cannot write** an assembly that another Cecil pass already wrote (empty 0-byte file), and
  writing `Assembly-CSharp.dll` needs an `AssemblyResolver` pointing at the game's `Managed` folder
  (`AssemblyResolutionException: UnityEngine.CoreModule`). Both patches therefore go in one pass.
- `android-data --pack apk|obb` on the host still exits 1 right after "N files planned" (real log:
  `<out>/make_android_data.log`); host packaging is not a supported path — the port's own first-launch
  setup does the conversion.

## Next

Port `wol-il2cpp` (route `il2cpp-arm64`) packaged and deployed; the device's first-launch setup runs
the conversion and the on-device IL2CPP compile. Then: principal-handoff launch, frame time in motion,
hitches, RSS/swap, Gun Manor entry, save + cold load.
