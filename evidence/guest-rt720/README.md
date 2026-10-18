# Guest-native initial-target dimensions: partial effect, not the M7 solution

These diagnostic runs preceded the owner's §15 revision. They are **not accepted optimization defaults**. No TV/handheld selector was introduced; the operation mode stays fixed handheld. Owner files and the corrected map section remain byte-identical.

## Versioned change

`WOL_GUEST_RT720=1`, otherwise OFF, verifies the complete mapped `main.text.seg` SHA-256 `df8a2524a65ec784f5781908be3734fa7c448f16c4c1029ee5b0fd4b63a0de84` and each original instruction before changing any instruction, at startup before guest threads. Disk executable untouched, instruction cache synchronized. Wrong identity/opcode/range refuses the entire patch. This changes exact guest instructions, **not** NVN descriptor metadata or host GL dimensions.

- `guest720a`, ELF `dcc3d6f1d377bb42af0f7be4c44e3ca7b09682cedc389a7479b387eb6846a11d`: seven dimension immediates in the measured initial NVN color/depth allocation owners. The first three swapchain images and their initial depth allocation really become 1280×720. Later camera/intermediate allocations stay 1920×1080.
- `guest720b`, ELF `068e6a193c33c539744aa1fdde91f31b5710718fcee5ef1b24e084ca90f00bb7`: same seven plus four immediates in the adjacent native dimension-query function `main+0xaeefe0` (`+0xaef090/094/0ac/0b4`). All original branches and return ABI preserved. **This still does not resize the dynamic 1080p camera targets.** It is not proof that this query controls all Unity Screen/RenderTexture consumers.
- `rt720-control1`: same `guest720b` ELF, patch OFF.
- `rt720-candidate2`: same `guest720b` ELF, patch ON.

## Complete game-idle frame windows

| Run | Presents/s | P95 ms | Process PSS MiB | SwapPSS MiB | Mali context commit MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial seven-site `guest720a` | 23.910 | 45.049 | 390.144 | 540.164 | 248.000 |
| Eleven-site `guest720b` | 23.996 | 45.303 | 404.616 | 524.469 | 235.008 |
| Same-ELF control OFF | 23.936 | 45.148 | 386.940 | 545.707 | 262.379 |
| Same-ELF candidate ON repeat | 23.520 | 45.767 | 371.054 | 553.836 | 237.324 |

Actual same-save/same-section process launches, periodic video checks retained; GPU timeline, upload skip, uniform cache and RomFS COW OFF. Not device-cold boots or swap-disabled trials. One same-ELF control and two candidates are **not a completed three-pairs acceptance study**. No FPS gain; the repeat is slower. Lower Mali observations are not an isolated whole-device RAM saving: process PSS+SwapPSS remains about 925–933 MiB and hundreds of MiB remain swapped. Never add driver commit to PSS as independent memory.

Visible spot-checks retain complete gulch player/environment, title/WANTED portrait/stencil, and five guide locations/three NEW labels. These are not battle/interior/reload/physical-button/audio acceptance or exhaustive pixel equivalence. All four receipts verify original save restoration, no cleanup warnings and restored Spruce captures. The experiment remains default OFF in the newer installed origin-observation build.

## New decision

Stop extending startup/display constants blindly. The owner updated `optimization-roadmap.md` to §15 while this work was in progress; changes `620a9b1` and `f79c12f` were fetched and fast-forwarded. Proceed with the separate read-only [actual RT origin audit](../rt-origin/README.md). Do not promote this patch as a coordinated 720p render graph or a no-swap fix.

Independent synthetic fixture stores the original and expected AArch64 words separately from the patch table, and asserts atomic refusal on every individual mismatching site, wrong SHA/NULL/truncated input, no unrelated byte changes and refusal to re-patch. Clean owner-local ARM64 source parity: 206 native files. Frozen per-run provenance and layouts are included; owner executable bytes are not.
