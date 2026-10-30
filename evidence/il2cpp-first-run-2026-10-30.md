# First working IL2CPP run on TSPS (2026-10-30)

Port: `/mnt/SDCARD/Roms/PORTS/wol-il2cpp` (route `il2cpp-arm64`, player Unity 2019.4.41f2).
Launcher: `Ports → West of Loathing IL2CPP` (standalone, no PortMaster `control.txt`).
Build inputs: Steam Linux build 2019.4.41f2 + asmpatch `rewired-android` + `streaming-assets`
+ `tools/dlcpatch` (DLC entitlement, Steamworks gates, Rewired `LinuxInput_*` stubs)
+ `tools/stubasm` `Kartridge.dll`.

## Measured on device (log.txt, `UA_FPS=10`)

```
[fps] 51.6 fps, frame 19.4 avg / 49.5 p99 / 745.1 worst ms, hitch 4, rss 718 MB   (character creator)
[fps]  8.8 fps, frame 113.8 avg / 7419.0 p99                                      (scene load stall)
[fps] 43.5 fps, frame 23.0 avg / 359.6 p99 / 612.0 worst ms, hitch 8, rss 705 MB  (after load)
pageflip: 0   InvalidOperationException: 0   MemAvailable: 72 MB
```

Display path: SDL KMSDRM, EGL 1.4 Valhall r32p0, Mali-G57, GLES 3.2, 1280×720@60, swap interval 1.
Input: `X360 Controller` enumerated as Android device 1.

## Faults fixed on the way

1. `InvalidOperationException: Steamworks is not initialized` at
   `SteamUtils.IsSteamRunningOnSteamDeck → Controls.UpdatePlatformControls` and at
   `SetPlatformConstantsOnPlayer → TitleStateWaa.OnPush`. Fix: no-op
   `InteropHelp.TestIfAvailableClient/Server`, stub `SteamUtils.IsSteamRunningOnSteamDeck` and
   `IsSteamInBigPictureMode` (5 methods total in one Cecil pass with the DLC patch).
2. `ERROR: Could not queue pageflip: -16` (×82) — **not** a runtime bug: it appears only when two
   `ua_host` instances / a menu session fight for DRM. A single launch has `pageflip: 0`.
3. The stock PortMaster launcher dies before the game because the card has no `control.txt`
   (`get_controls`/`directory` never resolve). The standalone launcher replaces it.

## Still open

- fps in the world and in the DLC location (Gun Manor), hitches during combat.
- Save + cold load.
- Memory headroom: 72 MB of 963 MB free with RSS ~705 MB — an OOM risk on long sessions.
