# Route B build log — portmaster-unity on the Steam 2019.4 build (2026-10-30)

Goal: replace the 24 fps Switch runtime with a native port of the Steam build (Unity 2019.4.41f2, DLC
`house` included), following wild1walker/portmaster-cuphead.

## Verified so far

- `pmunity version` / `port check` on the Steam folder: **Unity 2019.4.41f2, Mono, .NET 4.x**,
  route **android** recommended; textures nearly all plain (1× DXT1, 1× RGB24), single scene,
  1024×768, gamma.
- Toolchain notes from the check: Rewired (source edition) needs `rewired-android`; StreamingAssets is
  read through `System.IO` (needs `streaming-assets` + `android_data.streaming_assets = both`);
  `libsteam_api`/`steam_api`/`sdkencryptedappticket` have built-in stubs (SteamAPI_Init fails, game
  continues); `Kartridge.dll` is listed in MonoManager but absent (store plugin).
- DLC gate confirmed in the managed code: `Assembly-CSharp.dll` calls Steamworks
  `GetDLCCount` / `BGetDLCDataByIndex` / `BIsDlcInstalled`, so with the Steam stub the game will report
  "DLC not installed" unless patched (the Cuphead `dlc-from-steam-install` analogue).
- `runtime/build.sh ARCH=armhf` built `ua_host` (5.9 MB, ELF 32-bit ARM, includes `steamstub`).
- Unity's Android player 2019.4.41f2 downloaded from Unity's public CDN (351,918,328 B) and unpacked
  (`Data/`, `Variations/`).
- `tools/asmpatch` builds when a real .NET SDK is used: `out/any/asmpatch.dll` +
  `out/linux-arm64/asmpatch` (built inside the `build` distrobox, SDK 8.0.129).

## Environment blockers found (host, not game)

1. `tools/port/build_pybundle.sh` requests `--platform manylinux_2_28_aarch64` only; `astc_encoder_py`
   publishes `manylinux2014_aarch64`, so the download failed. Added the second platform tag.
2. `tpk_ar==0.2.4` is **sdist-only** on PyPI, so `pip download --only-binary` can never satisfy it; it
   has to be wheeled in the manylinux container (same as UnityPy). Local patch: removed it from the
   pip list and added a `manylinux_2_28_aarch64` wheel build for it.
3. The host `python3` resolves to the Hermes venv (no pip); the script must run with `PATH=/usr/bin:…`.
4. `dotnet` is not on the host (`~/.dotnet` holds only sentinels); the SDK exists in the `build`
   distrobox.
5. `android-data --pack apk` exits 1 silently: the `android-build` distrobox has java but no
   `aapt2`/`zipalign`/`apksigner`.
6. `android-data --pack none|obb` prints "121 files planned" and exits 1 with an 8 KB output tree —
   consistent with `android_data.asmpatch = "auto"` aborting when the patch tool is missing; must be
   retried now that asmpatch builds.

## State at the end of this session

- `wol-pybundle` is building the aarch64 wheel set in `quay.io/pypa/manylinux_2_28_aarch64` (arm64
  emulation); `tools/port/out/python.tar.gz` not produced yet.
- No candidate has been deployed; the device still runs the previously accepted Horizon build and the
  Unity 2017 port. Nothing on the device was modified in this session.
- Repository state: `main` at `bf94f17` plus this file.

## Next steps (in order)

1. Finish `python.tar.gz`, then `pmunity port package wol` → complete port dir with `ua_host`,
   `pmunity`, `pybundle`, `asmpatch`.
2. Retry `android-data` with asmpatch available (`--pack obb`), or install aapt2/zipalign/apksigner and
   use `--pack apk`.
3. Add the DLC entitlement patch (Steam DLC → owned) before the first gameplay test.
4. Deploy to `/mnt/SDCARD/Roms/PORTS/wol-pc2019/`, run through the principal handoff, measure frame time
   and hitches, verify Gun Manor entry and save/load.
