# Native Unity promotion verification

The current accepted host is `2408581859254d93d7a0f2eca9828a63dfe21af63593f7013c3d3aeb20a21b50`. The owner confirmed audible sound. `owner-audio.log` contains actual selected output/PCM/shutdown lines from that live run; it is not synthesized audio or a claim about every track.

`verification.json` records the local clean-index test snapshot, owner-local rebuild proof, device migration identities and preservation counts. The maintained historical suites are reported separately from current port tests. Four local historical owner-input tests skipped because those inputs were absent from the clean worktree; the remaining tests actually ran. Native-probe build used the image's AArch64 cross compiler, not its native x86 gcc. A PATH/venv preflight error was corrected before the reported test run; no source change was made to hide it.

The checked-in packing tool was exercised again against existing converted owner data: 84 aligned STORE ZIP entries, all eight StreamingAssets files byte-identical, all 67 managed assembly references resolved. The rebuilt APK is an owner-local validation artifact, not a replacement for the accepted installed APK; .NET metadata/ZIP timestamps can change its whole-archive hash.

Device result: only `West of Loathing.sh` and `westofloathing/` remain as WoL Ports entries. Real KMS shows one menu entry after a non-confirming D-pad wake. The game was not auto-relaunched. Old runtime/launch scripts, caches and sections were removed from Ports and UDISK, while current progress, 35 archived legacy save files and 602 existing historical save snapshots were preserved. Source/research history is not erased.

No proprietary APK/Unity player/managed/game data, saves or raw decompilation are included here. Post-rename gameplay, normal DLC entry, cold save/load and long endurance remain unverified rather than inferred from file hashes.
