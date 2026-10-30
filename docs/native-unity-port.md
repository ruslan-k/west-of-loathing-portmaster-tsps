# Native Unity ARM64 port — verified capability versus required update/DLC (2026-10-30)

> **Release eligibility: INCOMPLETE** under the owner's new mandatory condition: requested Switch title update `v327680` (or an **explicitly approved, verified function/content-equivalent updated PC release**) **and** full `Reckonin' at Gun Manor` DLC. The installed game data comes from an owner Linux Mono build. The repository pins Unity **2017.4.19f1** and the host, **NOT the original Linux application's patch/content version**; that must be proven before this can be suggested as an updated-game replacement. The old KMS Gun Manor validation entered from a **diagnostic duplicate save**, not from ordinary Dirtwater progress. See [release gate](release-gate-update-dlc-2026-10-30.md) and [current roadmap §28](optimization-roadmap-active-native-unity-2026-10-29.md#28-mandatory-update-and-dlc--architecture-and-optimization-reset-2026-10-30).

> **New post-audio device measurement:** [`trackA3`](../evidence/unity-trackA-2026-10-30/README.md) started via genuine Spruce principal/menu handoff. It measured **41.4–41.6 host-reported FPS** over 90 s, audio FMOD→SDL/ALSA live, VmRSS ~636–649 MB, **VmSwap=0**, no hitches in last sampled windows, clean MainUI return; previous ~47 FPS was invalidated by an incorrect launch path. **Not tested:** moving gameplay, normal DLC entry, updated patch-version equivalence, save/cold-load or 45-minute endurance. Do not describe 41.4 as an accepted full updated+DLC game FPS benchmark.

## Architecture and provenance

This is the owner's Linux Mono build of West of Loathing, Unity **2017.4.19f1**, converted for the exact Android ARM64 player. The host runs Android/Bionic engine libraries through portmaster-unity and the game's managed code through generic ARM64 Mono. It does not execute the old Switch payload or require a Box64/Wine stack.

- portmaster-unity: `913debc122b8234a3db56939a4728d9438972ce2`.
- libhybris: `7079712a42ea2754adf747e70c6cc75764c8596e`.
- Cuphead generic Mono release: `2026.10.26.10`, asset SHA256 `1c05883bdcdeb7e31e558245ecdc9ca8d6cbf591972f3be138ff654fc252f7f3`.
- Shipped host after audio fix: 7770352 bytes, SHA256 `2408581859254d93d7a0f2eca9828a63dfe21af63593f7013c3d3aeb20a21b50`.
- Owner-local APK: 323222330 bytes, SHA256 `55b6dd588aedbe742819d33cb30b55683ffafca4a07436674d9068afcd3b2e53`; not published.

## Conversion and packing

Reuse upstream GLES/highp and ASTC 4x4 conversion, no dimension or mip reduction. Core has 4155 textures and house has 627 with original width/height/mip counts. A narrow two-node `main_scene` wrapper converts the shared-assets node with upstream steps and preserves other object bytes/node identities.

The aligned ZIP32 STORE APK has 84 entries. All eight archived StreamingAssets paths match the earlier converted loose package byte-for-byte. The final 67 managed assemblies have a closed dependency graph.

WoL calls `File.Exists` before `AssetBundle.LoadFromFileAsync` on the same streaming-assets path. For the archive layout, one guarded managed call-site delegates to `WoLPackedAssets.Exists`, which checks the real archive entry through the exact Unity-profile compression library. Missing/corrupt/empty entries still fail. The DLC entitlement branch is unchanged. Eleven actual-target Mono helper tests pass.

## Audio defect and fix

Unity selected Java `org.fmod.FMODAudioDevice`, not OpenSL ES. The pinned host did not set `cfg.on_audio`; the JNI producer intentionally discards PCM when that callback is absent. The new lazy SDL sink consumes unchanged interleaved S16 stereo at FMOD's rate (24000 Hz), bounds queued audio/waits, logs failures and closes after producer shutdown. No asset/codec/mixer/global-ALSA workaround was used.

Three wiring/build/lifecycle tests and ten real-SDL behavior tests pass, including on TSPS. A silent-only device preflight opened and drained real ALSA PCM. The owner then physically confirmed audible sound during the actual game. That run opened `/dev/snd/pcmC0D0p`, logged 8018432 total frames / 30328 nonzero blocks and shut down cleanly. The owner described the checks as fast; this is not a matched FPS benchmark.

## Real-device gates

- Title, creation and base interiors rendered in KMS captures.
- Gun Manor rendered from an isolated diagnostic duplicate save. This establishes actual DLC-bundle use, not the normal quest-entry sequence.
- Packed base/DLC runs ended cleanly at 76.29 / 133.03 seconds after their rendering gates. They were not endurance tests.
- Before the audio change, late DLC samples were mostly 32.5–32.7 fps, peak sampled RSS 710.71 MiB, swap 173.12 MiB. These are not a comparison against audio-enabled play.
- Audio-enabled owner play is physically confirmed. Its exact process was later stopped only because the owner requested rename/cleanup; the real Spruce frontend returned.

## Promotion

Canonical installed names: `/mnt/SDCARD/Roms/PORTS/West of Loathing.sh` and `/mnt/SDCARD/Roms/PORTS/westofloathing/`. The accepted directory was renamed, not recreated; runtime, APK, extracted managed cache, preferences and saves were checked for unchanged hashes. Normal game launch retains the accepted environment; the directory path changed and the optional diagnostic path was hardened (zero budget disables it, Python validates run IDs and handles early child exit without strippable integrity assertions).

Removed device alternatives: `wol-switch`, `wol-switch-327680`, `wol-unity`, abandoned transfer staging, and the Packed/Unity/update menu launchers. The superseded audio runtime backup and obsolete principal-test controller were also removed from the active port. Thirty-five old save files were first preserved outside Ports under `/mnt/SDCARD/Saves/West of Loathing/legacy-before-unity-promotion/` and copied to a hash-verified local archive. Legacy saves were not imported over current progress.

The checked-in `port/` contains only the new canonical layout and redistributable runtime; old source/evidence remains historical. Owner game/Unity data and saves stay excluded.

## Still open

Normal DLC unlock/entry, full cold save/load, full physical-button audit and sustained mixed-scene endurance are not certified. Swap/memory pressure and earlier unexplained unattended progression remain open. No new post-rename game session was started by the agent; structural/file identity verification is not described as new gameplay acceptance.
