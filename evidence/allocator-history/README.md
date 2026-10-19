# SDK allocator history, actual-screen readiness and lifetime audit

## Corrections to the previous census

The `allocmin-b1`/`b2` requested phases were NOT gameplay. Independent review of
actual KMS images shows the developer splash in `title` and `world`, and the fully
loaded title in `map` and `return`. `scene-reclassification.json` preserves image
hashes and scores of a deterministic actual-title/gameplay-HUD classifier, tested
against the earlier verified UpRender frames. A non-black KMS signal and continued
presents did not prove that CONTINUE was accepted. The old fixed 65s title delay
sent CONTINUE before title readiness under the allocator-tracing overhead.

A second issue: SDK `Reallocate(NULL,n)` internally enters the instrumented
Allocate, which the old runtime tracked again at the outer Reallocate return.
This created duplicate live slots and later duplicate/unmatched free events despite
`incomplete=0`. The existing pointer-keyed host parser masked the insertion but
could not repair a later stale free. The old claim of **complete gameplay allocation
attribution is withdrawn**, not reused as a reclaim proof. Original raw evidence is
preserved. The older FPS results have their own real frames; no new battle or FPS
acceptance is inferred here.

## Actual changes

- `wol_screen_gate.py`: bounded standard-library RGB8 PNG decode (byte-exact against
  Pillow on a real KMS proof frame), known title-sign match and separate gameplay-HUD
  gear match, pinned to already-public proof screenshots. It rejects splash and Spruce.
- `wol_device_session.py`: wait up to 300s for a KMS-verified title before CONTINUE;
  persist observation scores instead of treating an elapsed delay as ready.
- `wol_roadmap_probe.py`: wait for a known gameplay HUD after CONTINUE (up to 180s);
  only then create `game-idle`. Record generic failures as failures even when cleanup
  succeeds. Independent full-screen review still decides exact scene identity.
- Runtime `graphics_trace.h`: unique live pointer on nested realloc; SDK instruction
  replay and returns unchanged. New compiled C fixture reproduces this case. Lowered
  threshold now admits 16 KiB, with unchanged hard slot/event caps.
- `wol_allocator_pages.py` / `--allocation-pages`: disjoint page unions for currently
  tracked requests, historical-only requests and unseen pages inside >=32 MiB readable
  guest-heap VMAs. Sequential log/pagemap snapshots, explicit incompleteness, no guest
  content reading or page mutation. Historical-only is **not** allocator-free.
- `wol_sdk_heap_census.py` / `--sdk-heap`: read-only bounded SDK span-table walk.
  Offsets are established from the actual pinned SDK `TlsHeapCentral::WalkAllocatedPtrs_`
  at +0x8148c and `FreePages` at +0x7d37c, not guesses from malloc sizes. State 1 is
  allocated (size-class 0 = large, other = small), state 2 is a free span. Measure
  present/swapped pages per span and repeat-check descriptors. A free snapshot remains
  **not safe to reclaim** without allocator locking, metadata/alias and GPU-lifetime proof.

## Artifacts and runs

- `allochist64`: pre-readiness-fix diagnostic on old ELF `84819832...`, original 64 KiB
  trace. Saves restored and Spruce recovered, but images remain splash/title. Its history
  classifier correctly flags lifetime inconsistency. In its requested game-idle window,
  large arena page-union swap was ~28.7 MiB live / 18.7 MiB historical-not-live /
  235.9 MiB unseen. This is title-state diagnostic evidence, NOT a gameplay free-space
  result. Sampling took ~2.6–3.8s and is excluded from performance claims.
- Corrected runtime `allocfix16`: ELF
  `b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158`,
  overlay `54eb28d27d713e7dc79c823ce5dd050264e399cfeeb7c8f6cc6ba693505eb9bf`,
  209-file source parity. Installed after independent backup/hash read-back.
  The first corrected run `allocfix16` failed in the harness before title readiness:
  six initial `kmsgrab` attempts found no active framebuffer, so the helper aborted.
  Save restoration and actual Spruce recovery succeeded; a secondary cleanup diagnostic
  lacked the not-yet-recorded runtime hash. Both harness issues are corrected: tolerate
  missing initial scanout under the common 300s deadline, and pin artifact hashes before
  waiting for readiness. No gameplay/memory win is inferred from this failed attempt.
  `allocfix16b` is the replacement owned run. It reached the real title, gulch gameplay,
  actual five-marker map and world return, and restored unchanged owner saves + visible
  Spruce without cleanup warnings. Its 16 KiB trace reached **8,192 events and explicit
  incomplete=1**; it is NOT a complete live-allocation census. A one-off extra bounded
  A request (`boot-advance`) was sent during this diagnostic and is preserved, so this
  is not a standardized performance arm. Do not lower the trace again without a bounded
  inner-allocator owner join, per the new roadmap §16.
- SDK metadata spans use state **3**, explicitly written by Init at SDK +0x7d978.
  The first SDK observer correctly refused the unknown state; the corrected observer
  accepts 3 as non-free metadata/other, still rejects unknown states, and never treats
  it as state-2 free ownership. Its data-free regression reproduces the refusal first.
- `sdkbase1`: same ELF, all allocation/UpRender tracing and size change OFF. Independent
  KMS title/HUD gates reached gameplay; the map and return are captured. Both SDK samples
  have an unchanged header and zero descriptors changed at reread. Sequential snapshot
  costs were **4.939 / 2.975 s**; this is a heavy diagnostic, NOT a timing/control arm.
  State-1 large spans account for **280.09 / 294.81 MiB swapped**, while state-2 spans
  retain **41.48 / 32.33 MiB present** and **96.69 / 101.06 MiB swapped** at game-idle /
  precleanup. State-2 is an SDK classification, NOT a proven safe release contract:
  locks, aliases and GPU/after-frame lifetime are not established. No page is discarded.
  `sdk-summary.json` preserves all state counts and raw snapshot SHA256; large JSON
  snapshots are byte-exact gzip-compressed. Source and saved-run identity remain pinned.

The old directly hooked request census cannot exclude current SDK-owned pages: actual
SDK spans and old hook requests measure different things, and the old captures were
not gameplay. This closes the instrumentation correction, not inner Unity/GC liveness.
The updated roadmap **§16 at 78167a9 takes priority**: stop expanding this diagnostic,
proceed with 720p trace-off acceptance, and park unsafe memory release/no-swap claims.

## Validation

83 memory/helper tests pass locally, including bounded A/B protocol/host-input guards,
adaptive 5s-settled/30s-transition
budgets, checks during input-helper waits, exact helper cleanup, SDK metadata-state 3,
initial missing-framebuffer retry and exact PID refusal, real-image positive/negative readiness
fixtures, compiled original SDK instruction replay + nested realloc uniqueness,
page-union/freed/reused/short-read/overflow guards and span-pointer/extent/state bounds.
No swap/DVFS/default policy changed. No page discard or guest code call was introduced.
