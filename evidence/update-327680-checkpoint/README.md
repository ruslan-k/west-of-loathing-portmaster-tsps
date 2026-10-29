# Update v327680 diagnostic checkpoint — not a release

The working native-Unity installation and its saves were not replaced. These runs use a separate Horizon/NVN candidate with isolated saves. The current candidate is **not playable**: enabling genuine DLC enumeration exposes an unimplemented FSP command 202 before the title screen.

## Source and artifact identities

- Farm/body baseline: mesh-u2 ELF SHA-256 `1723e4a9f3bb03dc29fa3fba72432b4dc71c5f5d8d75c4db84c7edaf09cb062c`, 2,002,472 bytes.
- Current DLC-service checkpoint: aoc-w3 ELF SHA-256 `d1ee2e4e63e12e40a4dc8d13254f0c6729d1471708bf14c0c9b8f94621d94170`, 2,006,560 bytes, AArch64, GLIBC ceiling 2.27.
- Source/overlay/frozen-build parity: 210 native files. The only native change between these two frozen builds is `ipc.h`.
- Current merged update + exact DLC section SHA-256 `ecab0ad27889a320ae6965413a06b1d99af4aef1cda65c7665ea6015788a13d0`. Current game payloads are pristine. Earlier `promoted-*` runs are historical experiments, not the installed asset profile.
- Correct patch base is the neutralized pristine upstream. Reconstructing mesh-u2 from it reproduces the prior overlay byte-for-byte. A separate review snapshot was initially mistaken for that base: aoc-w1 failed patch application and was never deployed.

The commit publishes redistributable source, authored tests, measurements and screenshots only. No executable, game/console container, extracted shader blob, key, save file or pseudo-device-ID bytes are included.

## What the frames establish

- Real KMS farm frames show connected player/NPC torsos; the player is clear of the hay in the torso proof.
- Ordinary farm → living room → farm transitions render coherent bodies, furniture, fireplace and UI.
- Mother dialogue and book reward are readable and upright. Returning through the game's Main Menu writes the lab save; a fresh process reloads the book into its actual item-description UI. This is process-cold reload, not a reboot/cache-flush test.
- Inventory remains unresolved. Item descriptions render but the central list region is empty. In inventory-c1, x520..920/y80..670 is exactly white: 236,000 pixels, RGB minimum/maximum 255 and zero standard deviation. The lab save contains multiple items. Filter behavior and missing draw/clip paths still need separate tests; no speculative shader fix was applied.
- Real pad events overlapped part of inventory-c1. Navigation in that interval is not attributed to the diagnostic input worker. The owner subsequently reconfirmed autonomous testing. A socket receipt alone never establishes physical-control acceptance.

## DLC: observed progression and remaining blocker

`aoc:u` previously returned zero regardless of the verified installed content. The new handler is restricted to the exact owned merged-image contract and preserves the base/unrecognized-image no-DLC path. It validates request sizes, PID form, handles/objects/buffers and list bounds. The parser retains CMIF alignment slack: the actual SDK list request has 16 logical input bytes but `data_size=32`; the compiled regression includes that observed shape.

- aoc-w2: real count returned 1, then the list request hit the overly narrow size guard (`INVALID_AOC_REQUEST`, exit24). This was a guard stop, not a guest crash.
- aoc-w3: real count/list returned one installed index1; PrepareAddOnContent and GetAddOnContentBaseId also completed.
- The next actual request is `fsp-srv` command202 / OpenDataStorageByDataId, data16, no PID. It remains unsupported: `UNIMPLEMENTED_IPC_COMMAND`, detail `0xca`, exit20, runtime elapsed21.539s.
- `dlc_house` remained0. No permaflags or quest progression were manually changed to fake recognition.
- The original DLC NCA's raw RomFS has now been extracted locally: 58,907,880 bytes, SHA-256 `e04ecb656771280d4847c7af527871f8714b0f68103772c2db9cd9ed3fcec7e7`. A hactool round trip proves its root contains the exact `house` and `house.manifest`, byte-equal to the supplied DLC. Only the identity receipt is published. The raw image has **not** yet been wired into the runtime or deployed.

DLC evidence gates remain distinct: original payload → native recognition → actual bundle reads → rendered playable DLC → normal quest entry and save/reload. Count/list alone is not DLC gameplay acceptance.

## Resource measurements

Measurements below use the exact baseline ELF's `nvn_present.frames` counter. They count present-path iterations, not independently observed panel refresh. No per-frame P95/P99 was measured. RSS/PSS/Mali/CMA overlap and must not be added.

- Farm, clean20.111s endpoint window: 22.326 presents/s, 1.662 CPU cores, status RSS689.141MiB, PSS306.428MiB, SwapPSS900.219MiB, matching Mali commit417.324MiB, MemAvailable64.363MiB.
- Living room, clean20.150s endpoint window: 26.452 presents/s, 1.687 CPU cores, PSS293.293MiB, SwapPSS911.547MiB, Mali430.945MiB, MemAvailable53.070MiB.
- A separate continuously sampled farm interval had about20KiB/s swap-in and no swap-out. Occupied swap is not proof of ongoing thrashing.
- GPU150→600MHz screening: 22.044→23.315 presents/s. The restored control lasted only4s; this is an incomplete screening, not an accepted optimization. The original governor was restored.
- Three drawn1920×1080 color backbuffers coexist with1280×720 RTs. Reducing those buffers has not been implemented or measured on this revision. Old revision-specific UpRender offsets were not enabled.
- Present state `proved=1`, `sampled_pixels=0`: repeated readback is not the demonstrated current bottleneck.

No persistent clock, VM/swap policy, resolution, texture or renderer-backend optimization was promoted.

## Tests and cleanup

Fresh pre-publication checks: 104 runtime/memory tests, 13 package/bounded-run/image-preparation tests, and24 additional metadata/parity tests pass. The AOC test compiles the actual marked C handler and checks valid replies, pagination/base fallback, actual32-byte list shape and malformed requests. Prior build/fixture failures are retained separately from final passing results.

perf-a1, accept-b1, cold-b2 and inventory-c1 ended at explicit TIME_LIMIT, not a spontaneous crash. aoc-w2/w3 ended at their documented service guards. Their cleanup receipts verify CPU restoration, no candidate runtime/pending handoff and131 checked production hashes unchanged. Recovery PNGs are actual KMS captures; current inventory/AOC recovery frames were inspected and show Spruce home.

`runs.json` is the programmatically enumerated historical run index. Each compressed runtime log is byte-exact and has an uncompressed size/SHA-256 in that index. Not every older run is a successful visual acceptance; read its STOP, ownership and cleanup evidence. Helper refusals and sampler failures are not reclassified as guest failures.

The scripts are the actual local-only controllers used for these runs, not a new portable public launch API. Their paths intentionally identify the isolated workspace/candidate; they must not be pointed at the production installation.

Independent model review did not produce an accepted verdict in the earlier attempts, and a standalone Codex CLI is unavailable here. This checkpoint is not independently review-approved and is not a release promotion.
