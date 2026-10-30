# West of Loathing TSPS — non-negotiable update + DLC release gate

**Date:** 2026-10-30. **Source review:** GitHub main `df6af1170e460fd93dd363db5bdac377fa2640f0`. This is an acceptance contract, **not** a claim that either candidate has passed it. Proprietary game/image, DLC and saves stay in the owner's private workspace and are not committed.

## 1. Hard product requirement (fail closed)

A candidate is **INELIGIBLE** as the finished PortMaster game unless **both** are present and tested:

1. **Required game update:** the owner-requested **Nintendo Switch title update `v327680`** (exact original guest-version identity for Horizon), or a separately owner-approved *verified function/content equivalent* updated PC edition. **Do not equate** Switch's numeric content version with the PC application's `1.11...` marketing/build version; different platforms use different numbering and may have different security/content revisions. A Linux build without independently established update provenance is **not a substitute**.
2. **Reckonin' at Gun Manor DLC:** actual title entitlement/access, normal quest entry through the ghost carriage in Dirtwater, scene/encounters/dialogue/items, persistence and complete save→restart→load, not just an asset-file count or a diagnostic duplicate save that starts inside Gun Manor.

The **strict route** that preserves the literal Switch `v327680` payload is Horizon plus the owner's matching DLC. Any non-Switch engine route is a **conditional research candidate**, not an accepted solution, until the update-equivalence and DLC gates are met. If exact same Switch program version is required byte-for-byte, a PC build can never be certified as that executable and should not be promoted.

## 2. Current evidence matrix (do not conflate results)

| Evidence class | Horizon/NVN→GLES v327680 | Installed native Unity/Mono |
|---|---|---|
| Updated game identity | Explicit `image-update-fixed` includes v327680 module sizes; baseline vs update mapping difference independently explained in [B0/B1](../evidence/horizon-hd1-2026-10-30/B0-B1-RESULT.md) | Built from owner Linux Mono data; pinned Unity **2017.4.19f1**, but **no source game content release version or per-file update parity receipt** in `port/westofloathing/runtime-manifest.json` |
| DLC preparation | GPL overlay has `WOL_AOC_HOUSE_BEGIN` (AOC count/list/prepare, program content conditional on merged RomFS hash), separate `wol-house.romfs` FSP storage, data ID `0x010031b00a4e9001`, and synthetic tests `test_wol_memory_aoc*.py` | Packer includes owner-supplied base and house assets and preserves guarded DLC entitlement. Test duplicate save reached Gun Manor in KMS; regular quest entry unverified |
| DLC content file identity | `wol_house_romfs_open` expects **58,907,880 bytes** and a regular file; at this code boundary size alone is checked, **not a full content SHA-256**. Merged program RomFS gated on `ecab0ad27889a320ae6965413a06b1d99af4aef1cda65c7665ea6015788a13d0` | Aligned APK, original eight StreamingAssets files verified against the owner's earlier converted package; **not proof of update v327680 parity** |
| Current measured performance | H2: valid baseline **42.90 ms** (~23.3 runtime FPS) in its own diagnostics, old matched E1c ~40.4 ms (~24.7). Stale-pixel `WOL_REFRESH_OFF=1` 37.37 ms (~26.8) **INVALID**, not a shipped win | [Track A3](../evidence/unity-trackA-2026-10-30/README.md) principal handoff 90 s **41.4–41.6 host FPS** with audio, **VmSwap=0**, but no moving gameplay, normal DLC, save/load or endurance; cannot assert game-wide 30 FPS |
| Release eligibility now | **FAIL: DLC normal entry + end-to-end coverage and ≥30 FPS unknown/failing** | **FAIL: required update equivalence unverified; DLC normal entry, moving gameplay and endurance unverified** |

**External version information (do not overwrite owner proofs):** official Steam announcements list a PC patch `1.11.11.11.11.1` on 2025-10-16; Linux/GOG listings show a Linux release labeled `1.11.11.11.11`. Therefore a Linux donor is **not automatically** the latest patched PC content, much less Nintendo `v327680`. These numbers are discovery context, not local checksums or content parity.

## 3. Owner-local immutable content provenance manifest — prerequisite, not a new tool rewrite

For **each candidate** produce a private, structured, reproducible record with:
- Platform/store, title/application/content ID, visible version and authoritative owner-local source for base, update and DLC. For Horizon record NPDM/title ID `0x010031b00a4e8000`, source version `v327680`, installed update NCA metadata, module `rtld/main/subsdk0/sdk` SHA/length, merged program RomFS SHA+length, DLC ID `0x010031b00a4e9001`, `wol-house.romfs` SHA-256+length; for Unity record game build/patch version from original game metadata and the actual `core`, `main_scene`, `house`, `Assembly-CSharp.dll`, relevant StreamingAssets and converted output hashes.
- Distinguish **raw original** game files from converted/copied artifacts; original SHA and output SHA in distinct fields. Store file paths owner-local; repository receives only legal metadata/evidence and **no proprietary data**.
- Exact donor Unity 2017.4.19f1 and host SHA; all successful DLC checks must refer to **the same manifest/build**, not a previous binary or a diagnostic save from a different version.
- When evaluating PC→Switch *functional equivalence*, produce a source-independent **feature/content delta checklist** for all required update behaviors and DLC areas, including known fixes: do not claim byte-equivalence between unrelated platforms. If no reliable mapping for a required update change exists, mark `UPDATE_EQUIVALENCE_UNVERIFIED`, not `PASS`.
- Validate ROMFS/house file size, data IDs and SHA before principal launch. The existing Horizon `wol-house.romfs` open test checks regular-file/size only; add a **bounded offline manifest verification**, not a per-frame hash.

## 4. Required DLC gameplay acceptance (on device)

- Verify base game boot, menu → normal gameplay and **update-specific content/behavior** of the supplied version (not just startup). Preserve original inputs.
- From ordinary progress reach **Dirtwater**; identify ghost carriage using normal game rules and DLC entitlement; open Gun Manor **without** save editing or teleport/scene forcing.
- Exercise at least one real Manor exploration, encounter/combat, dialogue/puzzle, item/state mutation, exit/re-entry; make diagnostic duplicate saves, exit completely to Spruce, cold start, load and verify state. A standalone Gun Manor KMS image is **supporting evidence**, not acceptance.
- Verify other update/DLC-dependent scenes, control mappings, audio, textures, text, cutscenes and return to original save/menu. All test data uses a **separate nonproduction save namespace**.
- Test wrong/missing/short/hash-mismatched DLC files and wrong-version update fail safely, without falling back silently to base-only play.
- Capture real physical distinct frame intervals in **moving open-world, indoor, combat and Manor** phases. Reference target: ≥30 distinct FPS with individual-frame p95 ≤33.333 ms on agreed representative moving scenes; long-term thermal memory, audio, controller and save integrity.

## 5. Branch selection decision

**Gate U+D first, FPS second:**
- **Unity PC route may advance** only if the owner's current donor is proved to include the required update content (or the exactly requested patched release is successfully converted) **and** normal Gun Manor gameplay/save load pass. The 41.4-FPS *90-second host receipt* alone qualifies neither.
- **Horizon strict v327680 route** retains exact update provenance and DLC AOC/FSP plumbing. First complete private content manifest + normal DLC proof. Only then invest in a *one-hypothesis* GPU/renderer alternative; H2 full-copy/stale-pixel results show that mere refresh suppression is not shippable.
- **No total runtime rewrite or language switch** before an architecture-level CPU/GPU bottleneck and a concrete compatibility/asset/ABI plan show greater expected return than the above controlled branches.

**Shipping labels:** `UPDATE_VERIFIED`, `DLC_CONTENT_VERIFIED`, `DLC_NORMAL_ENTRY_VERIFIED`, `SAVE_RELOAD_VERIFIED`, `GAMEPLAY_FPS_VERIFIED`, `AUDIO_INPUT_VERIFIED`, `MEMORY_ENDURANCE_VERIFIED`. Release requires **every** label, for the **same** candidate/manifests. Anything else: **candidate only**, never “fully playable updated+DLC”.
