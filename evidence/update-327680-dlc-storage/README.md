# v327680: genuine DLC storage reaches the running game

Follow-up to [the earlier checkpoint](../update-327680-checkpoint/README.md). This is a measured **Horizon/NVN diagnostic candidate, not a release**. The separate working native-Unity installation and its saves were not replaced.

## Fixed boundary

The guest previously completed `aoc:u` enumeration and stopped at FSP202 / `OpenDataStorageByDataId`. The new endpoint serves the original DLC's **own root RomFS**, not the program RomFS or a fabricated directory:

- Recognized program/image contract only; data ID `0x010031b00a4e9001`.
- Validate request length/alignment, storage ID, PID/handles/objects and buffers before opening the child endpoint.
- Open `wol-house.romfs` read-only, reject symlinks/non-regular files/wrong size, and reuse the existing bounded storage reader.
- DLC storage byte zero is the raw image's byte zero. Do not add the program section's `ROMFS_OFFSET`; do not run program overlays or its large-read COW mapper on DLC storage.
- Keep the existing program storage's prefix, bounds, COW and overlays unchanged. No entitlement or progression flags are edited by the controller.

Only `filesystem.h` and `ipc.h` differ from the preceding aoc-w3 frozen native tree. Rendering, texture data, clocks and VM/swap policy were not changed for this run.

## Artifact and owner payload identity

- aoc-w4 ELF: AArch64, 2,006,600 bytes, GLIBC ceiling 2.27.
- ELF SHA-256: `6003b1c86bf7acb6efa646a9a02e959c5bf94c7cb2eaf1144960fdd3a3ba4944`.
- Overlay SHA-256: `fd1fb91a2a99bade070856365b0218a6cec8b6dc2dbd76b9ad4db96a680b6ad1`.
- Clean overlay application and frozen build match all 210 native files; see `overlay-parity.json`.
- Program section SHA-256: `ecab0ad27889a320ae6965413a06b1d99af4aef1cda65c7665ea6015788a13d0`.
- Separate DLC root: 58,907,880 bytes, SHA-256 `e04ecb656771280d4847c7af527871f8714b0f68103772c2db9cd9ed3fcec7e7`.

The raw DLC is an **additional owner-supplied runtime input**, named `wol-house.romfs` beside the candidate executable. Extract it from the original owned DLC data NCA with `hactool --disablekeywarns -k "$KEYSET" --romfs="$NEW_OUT/wol-house.romfs" "$DLC_NCA"`. Use a new output path; independently unpack the image and compare both `house` and `house.manifest` before deployment. `house-romfs-identity.json` records the verified round trip. The launcher/harness preflight independently checks deployed bytes and SHA-256; the native open guard checks type and size, not cryptographic authenticity. A printed pinned image hash is not a disk-hash check.

No executable, raw RomFS, NCA/NSZ, shader blob, save, key or pseudo-device-ID bytes are included here.

## Actual device result

- AOC count/list/preparation/base-ID requests complete.
- FSP202 opens the separate storage. The SDK reads its real header and file tables, then requests **58,817,355 bytes at offset512**, exactly the original `house` bundle's full byte range. See `dlc-service-extract.log` and `runtime.log.xz`.
- The game itself changes `dlc_house` from `"0"` to `"1"`; other DLC flags remain zero. The pre-run backup is hash-checked and only filtered flag values/hashes are published in `dlc-flags.json`.
- Title → Continue → farm works. `farm.png` shows coherent player/NPC bodies and HUD. `inventory.png` and `options.png` show readable game UI.
- The 540-second runtime budget ends at `TIME_LIMIT`, exit22; watchdog reports542.123s. This is not a spontaneous guest crash or another service stop.
- Cleanup verifies no candidate runtime/pending handoff, CPU values/modes restored and all131 checked production hashes unchanged. `recovered.png` was inspected and shows Spruce home. An independent census agrees.

This establishes original payload → native recognition → actual bundle reads. It **does not** establish rendered Gun Manor, normal quest entry, DLC combat, audio, save/reload or full-play acceptance.

## Remaining inventory diagnosis

The center list still has no visible rows: x520..920/y80..670 is exactly white, 236,000 pixels, RGB min=max255 and standard deviation zero. Item details do render. No speculative shader correction was bundled with the storage fix.

Owned diagnostic input now separates two controls: Plus (`0x400`) opens inventory; shoulder R (`0x80`) opens Options rather than changing the inventory filter. ZR (`0x200`) did not open inventory. These are injected-input observations, **not physical-control acceptance**. The circular R/down hint may refer to the right stick; a separate category-change test is still needed before blaming the renderer. Earlier mixed-owner-input navigation is not used as mapping evidence.

The compositor probe is capped by draw class and can exhaust its samples before later UI. Missing late receipts are unknown, not proof that item draws were absent.

## Resources and tests

- 190 observations: MemAvailable minimum32,756KiB; CmaFree reaches0; minimum SwapFree948,872KiB. This run remains swap-heavy and is **not** a headroom/endurance result.
- Current-boot kernel log covers the run interval and contains no matching OOM kill, allocation-failure or GPU-fault lines; see `kernel-window.json`. Low CMA is still an unresolved margin risk.
- Fresh suites: **105 runtime/memory tests**, **13 package/bounded-run/image tests**, **24 additional metadata/parity tests**, all passing with zero skips. The new compiled-C regression exercises real dispatch/source selection, malformed requests, missing/short/symlink/FIFO input and distinct program/DLC byte-zero contracts.
- One extra-suite invocation initially used the wrong Python import path. Rerunning the CI form with `PYTHONPATH=tools` passed; no application code was changed to hide the setup error.

`run.json` binds the artifact, stop, raw-log identity, reads, memory and pixel measurements. `runtime.log.xz` decompresses byte-exactly to1,373,411 bytes with SHA-256 `2514247e7962de67bc5821a20aa21428fd8183d99025482c183157a6d59b93a9`. The copied local-only controllers require the private owner workspace/manifest and are not a portable public launcher API. No independent model-review approval or release promotion is claimed.
