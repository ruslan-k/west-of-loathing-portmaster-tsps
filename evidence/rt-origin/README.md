# §15 M7 — read-only NVN origin and Unity configuration checkpoint

**Current plan read:** owner roadmap revisions `620a9b1` / `f79c12f`. This is the first §15.2 observation checkpoint, **not completed root-cause/render-graph acceptance**. Neither >30 gameplay presents/s nor a recovery-safe no-swap cold boot is achieved.

## Real API trace

`WOL_RT_ORIGIN=1` observes the original guest NVN `TextureInitialize` and `TextureFinalize` boundary, before GL-worker routing. It records object, original caller/module/offset, guest thread, monotonic timestamp, requested width/height/format/target/levels/samples/flags/pool/offset, and up to eight saved frame-return addresses. It changes no API arguments, pixels, modes, synchronization or saved data. Default OFF; 512 total event cap. Guest stack reads are aligned, forward-only, within 1 MiB of this call's SP, protected by a **nonblocking** regions lock and read through `/proc/self/mem` to avoid a diagnostic dereference fault. Unreadable/busy observations refuse rather than stopping the game. No speculative unwind scan.

Owned `rtorigin1` uses ELF `5bb707bb513f516bb79d738d8ed95b669736108433ab4706e8ca150c1a29b908`, exact overlay/source parity **207 native files**. `WOL_GUEST_RT720=0`, COW/uniform cache/upload skip/GPU elapsed timeline OFF. Thus this is the original-dimensions path, not the earlier trial accidentally left enabled.

The trace recorded **512 events: 365 initialize requests and 147 finalize requests**, all initialize descriptors readable. It **hit the cap**: later lifetimes are incomplete. Among these requests, **13 are 1920×1080** (constructor events, not 13 simultaneously live independent allocations):

| Owner boundary | Requested family | Observed requests | What the chain proves |
| --- | --- | ---: | --- |
| `main+0xaef720/764/7a8` | RGBA `format=0x25`, target 1, samples 0 | 3 | Initial rotating window images; parents `aeee84 → aee60c → c7be6c → c7bd10…` |
| `main+0xaf8524` | Depth/stencil `format=0x35`, target 1, samples 0 | 1 | Initial companion depth; parents `9f6b80 → aef80c → aeee84…` |
| `main+0xaf6518` | RGBA, target 5, samples 2 | 3 | Dynamic texture owner via `af8120 → c8b574 → c8f708 → c89de4 → 8396fc` |
| `main+0xaf6518` | RGBA, target 1, samples 0 | 3 | Same render-thread queue path; object addresses may be reused across lifetimes |
| `main+0xaf6518` | Depth/stencil, target 5, samples 2 | 3 | Companion owner via `af85b4 → c8b574 → c8f708…` |

Offline inspection confirms `c8b574` follows a virtual resource-creation call inside a queued render-command dispatcher, and `c8f708` lies in its drain loop. This call chain **crosses Unity's render-thread queue**, so naming it as an `UpRender` IL2CPP callsite would be false. A raw final parent address outside a known module is retained as unknown, not assigned a fabricated function. The full data-free index is `origin-index.json`.

Existing `WOL_PRESENT_SOURCE` joins the initial objects to the three rotating 1080p presentation inputs; `WOL_DOWNSAMPLE_VIEW` names the intermediate source/destination objects. Neither those joins nor aggregate residency logs supply the complete viewport/scissor/MSAA resolve/CPU-copy/first-sample graph. That portion of §15 remains open, as do saloon/battle/reload lifetimes.

## New configuration lead — actual Switch data, separate desktop consumer audit

Read-only inspection of legitimate owner data found startup `Data/level0` object **29**, a 76-byte MonoBehaviour referencing script **165** in `globalgamemanagers.assets`; that script resolves to **UpRender**, Assembly-CSharp.dll. Its first serialized settings decode to **forceWidth=1920, forceHeight=1080**, with UI camera reference `(0,12)`.

The legitimate **desktop** assembly's `UpRender.UpdateTexture` independently shows how `forceHeight` is a minimum height, not a maximum: when screen height is lower, render width is grown to preserve screen aspect and render height becomes `forceHeight`; the resulting dimensions feed `new RenderTexture(..., depth=24, ...)`. At 1280×720 and a 1080 minimum this arithmetic produces 1920×1080. This explains why simply shrinking the startup swapchain can leave a separate 1080p family — **but is still a candidate causal explanation, not proof of identical native Switch method instructions**. No setting or owner section was modified. `config-origin.json` contains only hashes, object IDs and settings metadata, not asset/assembly bytes.

Next exact proof: join the native producer of the render-thread creation command to the serialized UpRender owner, or resolve its native IL2CPP method and demonstrate the same minimum-height branch. Only after that gate, make a narrow owner-side setting/consumer variant with color/depth/viewport/copy/UV contracts checked together. Do not patch every 1080 constant or bypass host_scaled CPU-view guards. The earlier startup/query experiment in `../guest-rt720/` is explicitly not this proof.

## Verified and not verified

- Real KMS gulch frame shows complete character/environment; guide/title/pause captures are retained. Original corrected-map section hash `49bd16718ed0dc46f16599255791c7603e8aa2b5f04898784a39d6cacb9d0722` unchanged.
- Runtime analyzer reports zero GL errors. Exact owned runtime stopped; save hashes restored; receipt has `cleanup_verified=true`, no warnings; real restored KMS image shows Spruce. Independent fresh SSH process check: no `wol-horizon`, one MainUI.
- Current memory/helper suite: **42 tests pass**. Additional staged-selection/sprite/map/frame-parity suite: **24 pass**. Guest-frame walker fixture proves limits, unreadable/cyclic/misaligned refusal and no fixture writes. Clean ARM64 build and byte-exact native source/overlay reproduction pass.
- This is diagnostic observation, not an FPS optimization; trace overhead is not independently calibrated. No no-swap/physical-button/audio/endurance acceptance. No speculative freeing, `MADV_DONTNEED`, async completion or TV-mode switch.
