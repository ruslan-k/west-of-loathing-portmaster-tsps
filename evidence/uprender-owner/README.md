# UpRender: native Switch producer identified; component-settings experiment

## Scope and evidence boundary

This follows optimization-roadmap §15, not another AM/window-size override.
The public material contains native offsets, input hashes, settings metadata,
GPL adapter changes, tests, runtime receipts and KMS screenshots. The original
Switch executable, metadata file, serialized assets and native/IL dumps stay
owner-local. Desktop IL is not used as authority for the Switch ABI.

## Producer proof

`tools/wol_il2cpp23_owner.py` is a read-only, fail-closed v23 parser. It joins
method indexes to the unique validated 64-bit code-registration pointer table
and field indexes to the unique validated per-type field-offset table. It
refuses other metadata versions, malformed ranges, missing/ambiguous tables
and non-contiguous method indexes. An independent synthetic fixture exercises
the method/field join, no-field sentinel and refusal paths.

Pinned owner results are in `owner-map.json` and `rendertexture-map.json`:

- UpRender type index 2200, `Awake` main+0x513df8,
  `UpdateTexture` main+0x513eb4.
- `forceWidth` is an instance int at +32; `forceHeight` is at +36.
- Owner-only native analysis shows these fields flow directly into w1/w2
  at main+0x514838, calling the metadata-resolved
  `UnityEngine.RenderTexture::.ctor` main+0x6e7ca8 with depth=24.
- The live OFF control observes one component, two constructor calls at
  **1920×1080**, and the returned RenderTexture objects/native cached pointers.
  This is an actual game-side producer, not an NVN queue-drain backtrace.
- The compiled Switch method uses the component dimensions directly here;
  the desktop implementation's minimum-height/aspect logic must not be
  transferred to this binary by assumption.

The separate queued-create probe at main+0xc8b570 observes backend GPU-resource
objects. Their pointers are **not equal** to the RenderTexture cached native
pointers; a direct cross-queue pointer-identity join is not claimed. Whole-game
NVN origin logs remain capped at 512 events and do not prove a full lifetime
or consumer graph. Native dimensions and real GL allocations are separate
observations, both retained in the run evidence.

## Narrow variant and safeguards

Both controls and candidates use the same `uprender1` ELF:
`37178b7a723b5f9d477f7af2f2ee77e49c42f33c38dd49dd098442d6b495eab5`.
The entire untouched main.text is SHA-256 checked before installing any of the
five exact-instruction observations; the constructor/prologue/ADRP/BLR
instructions are replayed with their original stack and link semantics.
Standalone compiled tests exercise this replay and unchanged surrounding bytes.

- `WOL_UPRENDER_TRACE=1` observes; no component setting is changed.
- `WOL_UPRENDER_720=1` additionally changes **only eight process-local bytes**
  (+32/+36) during this component's Awake, before the first UpdateTexture.
  The pair must be exactly 1920/1080; writable accessible aligned ownership
  is checked before committing 1280/720. Unknown settings refuse without a
  partial dimension write. The flag implies observation and defaults OFF.
- The setting change occurs before allocation so Unity owns subsequent
  RenderTexture construction, camera setup and dependent state. There are no
  host-descriptor lies, shared shader changes or global constant substitutions.
- Original game files, SDK startup sizes, protected section, saves, swap policy,
  GPU clocks and handheld-only operation are unchanged.
- `WOL_GUEST_RT720=1` is explicitly incompatible with this experiment, preventing
  the earlier startup-buffer trial from being accidentally combined with it.

No experimental fast path is promoted by installing this diagnostic ELF.
Ordinary launches do not enable either new flag.

## Run protocol

`upowner-a1` is the 1080 control, `upowner-b1` the component-settings candidate.
The principal/session and roadmap probe take the same original save through
CONTINUE, stationary gulch, right/left, map, return, pause and unpause; those
phase names are requests, not automatic scene classifications. Every run owns
its PID/start ticks, restores the exact original save, ends with a real KMS
Spruce capture, and records effective flags. These are synthetic diagnostic
Npad actions, not physical-button, audio or owner-play acceptance.

Fixed flags: `WOL_UPRENDER_TRACE=1 WOL_RT_ORIGIN=1 WOL_GPU_RESIDENCY=1`,
`WOL_GUEST_RT720=0 WOL_ROMFS_COW=0 WOL_UPLOAD_SKIP=0 WOL_UNIFORM_CACHE=0`,
`WOL_COPY_EQUAL=0 WOL_COPY_AUDIT=0 WOL_GPU_TIMELINE=0`.
Only `WOL_UPRENDER_720` changes between arms. Both retain real periodic
presentation readback, the lightweight memory sampler and per-present clock.
No VM/DVFS setting is changed. See effective-env and receipts for the complete
launcher-resolved environment and same-section/save identities.

`summary.json` uses consecutive MOMO_FRAME timestamps within phase-local
windows, excluding the first two seconds; it reports **runtime presents**,
not independently measured panel FPS. PSS, SwapPSS, Mali commit and CMA overlap;
none is summed into a fictitious physical RAM total. `target-census.json`
separates NVN-request records from real GL creation records, repeated creations
from live storage, and truncation from absence.

## First measured A/B (exploratory, not promotion)

- Gulch runtime presents/s: **24.019 → 32.638**; P95 **44.960 → 33.438 ms**.
- Same-scene Mali commit median: **253.344 → 232.023 MiB**.
- Game PSS median: **390.033 → 379.466 MiB**; SwapPSS:
  **537.770 → 551.668 MiB**. No no-swap/total working-set win is established.
- The two observed constructors change from 1920×1080 to 1280×720.
  Capped NVN origin traces show 1080p create events **13 → 4**; nine
  dynamic color/depth/MSAA requests move to 720p. The three initial
  SDK/window color images plus one depth image remain 1080p intentionally.
  These are event counts, not nine independently live allocations.
- Same ELF, protected section, original save and non-treatment environment;
  zero analyzer GL errors; both receipts prove save restoration and visible
  Spruce recovery. The true map opens in both arms. Spot-reviewed world,
  title/WANTED and map frames show no obvious layout/body/stencil regression.
  Different antialiasing, animation phase and movement sampling mean this
  is **not** a claim of byte-exact pixel parity.
- This first pair passes an origin/causal-mechanism gate, not release acceptance.
  P95 remains slightly above 33.33 ms. Alternating repetition, moving/interior/
  battle/load scenes, physical controls/audio, complete consumer mapping and
  recovery-safe no-swap cold start remain open. Both new flags stay OFF.

## Alternating repetition: three candidates, one failed control

The complete A1/B1/A2/B2/A3/B3 attempt set is preserved, including its failure;
see `repeat-verdict.json` and the report's `performance` section. Identity and
non-treatment environment match across all six attempts, and every attempt's
original save and visible Spruce recovery are verified. This does **not** make
every gameplay attempt successful.

- Valid 1080 controls A1/A3: **24.019 / 24.226 presents/s**, P95
  **44.960 / 44.293 ms**.
- 720 candidates B1/B2/B3: **32.638 / 33.348 / 33.878 presents/s**, P95
  **33.438 / 32.157 / 31.904 ms**. The gain repeats in stationary gulch;
  B1 still misses the 33.33-ms tail threshold.
- **A2 is invalid for performance and route acceptance.** Frame progress stops
  at 1481 before the idle window. World/right/left/map/return/pause/unpause
  screenshots have the same SHA-256; the requested map never appears.
  Audio/HID logging continues, so process liveness and clean final restoration
  concealed a frozen render/gameplay path. No live stacks were captured and
  root cause is unknown. Do not attribute it to the observer or count it as
  successful just because this is the control arm.
- Candidate game SwapPSS medians remain **532.668–551.668 MiB**. Lower Mali
  commit is real but no no-swap/total-working-set acceptance follows.
- `performance_summary` now explicitly excludes missing/short frame windows
  without inventing zero FPS; regression coverage tests this distinction.

Verdict: repeatable local FPS effect, **not** three complete valid pairs or a
stable production profile. Before promotion, isolate the component-only Awake
setting from the extended constructor/queue probes and run trace-off controls
and candidates. Retain a progress watchdog/diagnostic capture on a new stall.
Broader scene coverage and the independent memory-owner proof remain open.

## Reproduce the metadata join (owner-local inputs)

```sh
python3 tools/wol_il2cpp23_owner.py \
  --metadata "$OWNER_METADATA" --image "$OWNER_IMAGE" \
  --ro-va 0x13ce000 --data-va 0x1d47000 --type UpRender
PYTHONPATH=tools python3 -m unittest -v \
  test_wol_memory_il2cpp_owner test_wol_memory_uprender
```

The offsets above are valid only for the input identities in the reports;
never reuse them blindly for a different game build.
