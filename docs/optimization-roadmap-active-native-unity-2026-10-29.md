# West of Loathing on TrimUI Smart Pro S — active optimization roadmap (reviewed again 2026-10-30)

> **Status:** reviewed through WoL `38f05f66`; E1b's frame attribution defect and runtime-CMA pressure now drive the Horizon priority. No 30 FPS optimization accepted.  
> **Primary implementation:** **native Unity 2017.4.19f1 / Mono on AArch64** (the current playable/installed port).  
> **Secondary implementation:** **actively developed experimental** Switch **Horizon/NVN → GLES** v327680, **NOT** the installed production runtime.  
> **Reviewed repository snapshots (2026-10-29):** WoL `38f05f66a5ee14f75bd0fdf15bae9c88e00c419c` (13 commits after prior roadmap update); `wild1walker/portmaster-unity` `490c4d449c65dfba5288e37d1ce931d8d4972d04`, with the **actual installed host built from pinned upstream** `913debc122b8234a3db56939a4728d9438972ce2` and local `legacy-fmod-output.patch`; `wild1walker/portmaster-cuphead` `4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4`; `shirai91/nx2android` `6444d67694a4015003fc31c6c74f110fac43502a`. Pin these identities in any reproduction.  
> **Decision (current):** installed Unity/Mono retains its audio-enabled baseline N0–N14. Experimental Horizon v327680 must **repair existing E1 op profiler units and per-frame attribution** and **verify runtime CMA headroom** before an async-program or resolution optimization. See [current section 25](#25-2026-10-30-corrected-e1-and-horizon-priorities).

### Current audit: five more commits and a critical E1 correction

The isolated Horizon branch now has rolling `WOL_OP_SPLIT` measurements, target flags for the three seven-vertex draws, and the first async qualification stop. **E1 exists already**, but the recorded `handler=3.234` is **3.234 milliseconds per selected op**, not a 64-op sum to divide again to obtain 50.5 µs. The 64-op `gap` covers other operations and frame/list boundaries, **not necessarily GPU waiting**. The [E1 report](../evidence/update-327680-op-split/README.md) now contains a correction preserving its original logs. The async failure `NVN_PROGRAM_INVALID detail=0x0` does not yet prove a deleted/recycled program. Furthermore, `WOL_ASYNC_ACK` is checked by presence, and device telemetry reached `CmaFree=16 kB` post-launch with ~1.1 GiB `VmSwap`. **Prioritize validated timing, program-object provenance and memory safety, not guessed pin counts or 720p resizing.** Authoritative active Horizon plan: [section 25](#25-2026-10-30-corrected-e1-and-horizon-priorities).


**2026-10-30 latest developer update:** Horizon E1b's new per-class op timer is **not yet frame-correct**: it counts the first operation of a new frame in the previous bucket, and the published first 60-frame window averages **462.637 ms/frame** rather than the old steady ~43-ms gameplay. The H-M0 system sampler saw **66/95** CmaFree points below the 65,536 kB launch gate; no exact GPU allocation owner is proven. Recent async program pinning did **not** resolve NVN_PROGRAM_INVALID, and the 192 MiB CPU-shadow eviction test did **not** engage. The active next step is **H-E1c (frame-correct V3 profiling in real heavy gameplay) + passive H-M1 memory receipt**; details and hard gates in [§25](#25-current-horizon-v327680-re-audit--2026-10-30-head-38f05f66).

## 0. Executive decision

The current WoL `README.md` states that the **active** game is the native Unity/Mono implementation, using the owner's Linux Mono data, the exact 2017.4.19f1 Android ARM64 player, a generic Mono-to-IL2CPP bridge from `portmaster-unity`, a local SDL sink fix for the legacy Java FMOD path, and an owner-local, converted/packed APK. Title, character creation, base-game interiors, Gun Manor from a diagnostic duplicate save, and **physically audible** audio have been observed. It explicitly states that previous Switch/Horizon binaries and their old performance evidence are historical. Do **not** cross-apply the old 1080p window-image experiments to the currently installed Unity game.

**What is known now:** the native port rendered an earlier *pre-audio-change* DLC session at about **32.5–32.7 fps**, with sampled RSS up to **710.71 MiB** and swap up to **173.12 MiB**. These are not an audio-enabled A/B or full-game guarantee; no fixed 30-fps, no-swap, endurance, full normal DLC-entry or complete cold-save/reload acceptance exists. The verified source process preserved original texture dimensions and mip counts and used **ASTC 4×4 / GLES highp**. The owner separately confirmed audio and fast subjective rendering. Those facts do **not** establish sustained performance after audio promotion.

**Do first:** on one isolated candidate copied from the accepted native installation, measure the **same physically verified scenes** with sound enabled, `UA_FPS=1`, process/thread CPU, RSS/PSS/SwapPSS, fault/swap deltas, GPU frequency, temperature, and full-screen KMS output; then alternate release-equivalent baseline versus a single profiling switch. Record hashes and return to unchanged installed menu. The first candidate must not alter assets, renderer, class libraries, saves, drivers, CMA policy or clock settings.

**No universal “free 30 FPS” patch follows from the three upstream projects.** Their contributions are a mature instrumentation toolbox, an offline conversion/quality pipeline, scene- and ownership-aware optimizations, conservative GL transformations, and repeatable comparisons. Each has different applicability to WoL.

## 1. Source-of-truth and provenance matrix

| Repository/file | Verified applicability | What **not** to infer |
|---|---|---|
| [WoL README](../README.md), [native status](native-unity-port.md), [active layout](../port/README.md) | Current installed Unity/Mono port, files, audio, acceptance gaps. | Old Switch `docs/optimization-roadmap.md` describes active current-game behavior. |
| [WoL converter](../tools/unity/convert.json), [scene wrapper](../tools/unity/convert_scene.py), [packer](../tools/unity/prepare_packed.py) | `steps=["shaders","textures"]`, `highp`, ASTC `4×4`, `scale=1`, `mips=keep`; guarded two-node scene; aligned packed APK; exact version and assembly checks. | The `quality` step is already enabled; it is **not** in the current conversion configuration. |
| [WoL audio patch](../runtime/unity/legacy-fmod-output.patch), [host build notes](../runtime/unity/README.md) | Preserves legacy FMOD PCM via lazy SDL output; owner confirmed sound. | Silence is acceptable in optimization A/B; dummy-audio upstream benches are equivalent to installed sound path. |
| [Unity profiler](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/docs/profiling.md) | `UA_FPS`, `UA_PROF`, `profsum.py`, `profbench.sh`, `profcpu.py`, `memprof.py`; code is present in the **pinned** host source. | Their benchmark data on Mali-G31/H700 predicts WoL fps on Mali-G57/A523. |
| [Unity runtime reference](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/docs/runtime.md) | `UA_GL_TRACE`, `UA_GL_TRACE_GPU`, `UA_GL_DSCLEAR`, `UA_RENDER_SIZE`, `UA_FRAME_RATE`, `UA_QUALITY`, `UA_MONO64_GC_SLICE`, other gated switches. | All settings are appropriate for Unity **2017.4.19f1** or the **SDL/KMSDRM** display path; verify their individual guards. |
| [Unity quality converter](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/docs/quality.md) | Serialized quality changes and runtime cap mechanism can be evaluated **offline** for owner data, in a separately packed APK. | URP optimizations are relevant to a 2017-era built-in renderer without proof. |
| [Cuphead technical notes](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/docs/technical.md), [bench harness](https://github.com/wild1walker/portmaster-cuphead/tree/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/bench) | Alternating baseline-on/off-baseline runs, deterministic scene verification, narrow optimization gates, renderer-aware acceptance. | Cuphead's `CUPHEAD_*` switches or its exact Mono/Cecil patches exist in WoL. |
| [nx2android resource tracking](https://github.com/shirai91/nx2android/blob/6444d67694a4015003fc31c6c74f110fac43502a/nxnative/dm/android/gfx_vk_tex.c), [presentation](https://github.com/shirai91/nx2android/blob/6444d67694a4015003fc31c6c74f110fac43502a/nxnative/dm/android/gfx_vk_present.c) | Architecture ideas for guest-pool alias provenance, deferred resource destruction and bounded present tickets **in the experimental Horizon branch only**. | Its Vulkan/BC texture path is suitable for TSPS GLES/Mali or gives a portable no-copy solution. |

**Licensing:** WoL is GPL-3.0; upstream generic Unity/Cuphead/nxnative code carries MIT or other component licenses. Retain per-component notices when incorporating code. Do not commit the game, Unity's proprietary Android engine files, original managed assemblies, an owner-derived APK, keys, saved games, raw reverse-engineered proprietary blobs, or profiling dumps that contain those bytes. Source links above refer to the inspected upstream revisions; update the audit table when upstream is repinned.

## 2. Acceptance contract and immutable safety rules

**Two objectives, two independent proofs:**
1. **Performance:** stable visible game presentation in moving scenes, a **physically verified ≥30 distinct presents/s** where the game is expected to advance, **P95 physical frame interval ≤33.33 ms** during a stationary-frequency measurement interval, with no long stalls or unexplained regressions. A UI log or Unity engine count is not itself proof of scanout, distinct frames, or smooth input latency. Record median, P95, P99, worst, ≥50 ms hitch count, expected game pacing, and visual screenshot/sequence.
2. **Memory:** no process OOM, enough device MemAvailable and CmaFree headroom, stable RSS/PSS/SwapPSS and **swap in/out traffic** through cold load, indoor/outdoor changes, dialogue, maps, combat, ordinary DLC entrance and reload. **Zero-swap** is a separate stretch acceptance that must be tested with swap unavailable *before launch* in a dedicated candidate; low `VmSwap` or high `SwapFree` is not equivalent. Never disable swap on the production device merely for a speculative run.

**Functionality is a hard gate, not a weighted metric:** visuals (correct game panels, text, inventory, maps, scene transitions), audio, controller input, save/load, assets/DLC and safe exit all remain intact. Required evidence: independent KMS/DRM capture plus frame log plus device-side process evidence plus original-source/candidate hashes. If a performance switch improves the counter but a screen is black, static, cropped incorrectly, or content is missing, it **failed**, irrespective of fps.

**Operational invariants:**
- Leave the accepted `/mnt/SDCARD/Roms/PORTS/West of Loathing.sh` and `westofloathing/` untouched until an explicitly reviewed promotion. No write to `westofloathing/data/` or `westofloathing/home/` in experiments; work on a separately named copy with isolated HOME, config, persistent-data and cache, after confirming the copied launcher and APK use those paths.
- Preserve the existing save and legacy archive in `/mnt/SDCARD/Saves/West of Loathing/legacy-before-unity-promotion/`. Never infer byte-identical save semantics from successful title launch. Use diagnostic duplicate saves, not real progress, and compare hash plus semantic load/re-save/reload.
- Run one intervention at a time, default OFF, with rollback. No changing GPU clock/governor, scheduler, thermal limits, device memory-pressure policy, kernel/driver, screen model, library ABI, or default game settings to force a favorable measurement.
- For **historical Horizon** experiments preserve the explicit **65,536 KiB CmaFree preflight gate** and historical memory-floor policy; never lower them to force start. For **native Unity** the existing launcher does not advertise that Horizon gate—measure device headroom but do not falsely assert the same protection has been installed.
- Record boot ID, real process start ticks, ELF SHA-256, package/hash, application/Unity version, git HEAD and tracked effective environment for each run. A fresh device boot may be justified to restore CMA; reboot identity and restored frontend must be verified.
- Run bounded observations and restore frontend, audio route, GPU context and control mapping; after each run hash/check the installed production files and saves (or compare a recorded manifest).
- No asset dimensions, mip counts, shader precision, code patch, SDL display mode or GPU workaround is changed by the first benchmark.

## 3. Baseline: evidence separation

| State | Measured / verified | Confidence / limitations |
|---|---|---|
| **Native Unity—owner accepted** | Title, creation, base interiors, Gun Manor via duplicate save; native audio owner-confirmed. `ua_host` SHA-256 `2408581859254d93d7a0f2eca9828a63dfe21af63593f7013c3d3aeb20a21b50`. | Real device, but no matched post-audio sustained FPS/memory or cold full DLC entry. |
| Native Unity—**earlier pre-audio** DLC | Mostly **32.5–32.7 fps** late; sampled RSS max **710.71 MiB**, swap **173.12 MiB**. | Different audio state and short bounded runs; not a global 30-fps guarantee. |
| Native conversion | **4,155** `core` textures, **627** `house` textures, original dimensions/mips; ASTC 4×4 guided, highp GLES; 8 archived StreamingAssets preserved; 84-entry packed archive and 67-assembly dependency closure. | File-level conversion checks, **not** a live GPU-memory measurement. |
| Historical Horizon §15 | An older v23-era `UpRender` **pixel** override improved matched `tut_gulch` presents from ~24 to ~33–34. | Old guest/ELF; does **not** transfer to new v327680 metadata v24 or native Unity. |
| Historical Horizon v327680 | `Screen.get_width/height` 1280×720 but **3×1920×1080 colour + 1×1920×1080 depth** guest windows; diagnostic `AW_RELEASE=0` trace **4.61 fps**, unreproduced historical release **25.5 fps**. | Diagnostic figure cannot be compared with different release build. |
| Historical Horizon failed storage scale | `ZERO_RENDER_SCALE=2` allocated 720p storage and emitted 576 presents but KMS frame all black; `target-seen=0`. | Proven output failure; a “+32%” counter was retracted. |
| Historical Horizon physical-pages study | ~**582 MB** unique resident physical peak, **132–137 MB** repeated mappings in one diagnostic; anon/swap dominated. | Not a total host-committed GPU footprint and not a native-port measurement. |

Evidence: [native port](native-unity-port.md), [resource history](resource-optimization.md), [Oct 29 Horizon findings](optimization-findings-2026-10-29.md), [historical roadmap](optimization-roadmap.md). Keep each measurement attached to its **own artifact/run/scenario**.

## 4. Proposed benchmark manifest and reporting format (N0)

Create an **untracked, owner-local** `bench-native/` or similar path outside installed runtime and keep public output restricted to metrics, command definitions and hashes. Do not publish screenshots with private saved-game content unless reviewed.

Each run's manifest should capture:

```yaml
schema: wol-bench-native-v1
track: native-unity
run_id: example-A1
repository_head: a5af4611f4a69449abc72961f19c1b97d91dfaa1
host_upstream: 913debc122b8234a3db56939a4728d9438972ce2
host_sha256: "<measured>"
apk_sha256: "<owner-local measured, do not publish bytes>"
boot_id: "<device boot id>"
pid_start_ticks: "<proc stat>"
firmware: "<measured>"
gpu_driver: "<measured>"
scene: "<physically verified title/interior/street/DLC>"
checkpoint_save_sha256: "<duplicate>"
render_path: SDL2/KMSDRM
audio: actual SDL/ALSA FMOD path enabled
controls: original TRIMUI Player1 mapping
candidate_env_diff: {}
window_seconds: 60
warmup_seconds: 20
result: completed | stopped | invalid
valid_kms: true | false
native_frame_count: "<measured>"
display_frame_count: "<measured or unknown>"
p50_frame_ms: "<measured>"
p95_frame_ms: "<measured>"
p99_frame_ms: "<measured>"
hitches_over_50ms: "<measured>"
rss_peak_kib: "<measured>"
pss_peak_kib: "<measured>"
swappss_peak_kib: "<measured>"
swapin_delta_pages: "<measured>"
swapout_delta_pages: "<measured>"
major_fault_delta: "<measured>"
memavailable_min_kib: "<measured>"
cmafree_min_kib: "<measured>"
cpu_busy_by_tid: {}
gpu_clock_residency: {}
temperature_range: {}
audio_pcm_nonzero: true | false | not-sampled
save_hashes_unchanged: true | false
screenshots: ["<local metadata/hash only>"]
```

**Scene matrix:** T0 cold title and input; T1 character creator; T2 normal indoor scene; T3 outdoor walking with repeated physical input; T4 dialogue/inventory/map; T5 combat when reachable; T6 ordinary base→DLC quest entry and Manor; T7 save, terminate, cold restart, load, one more save; T8 20–30 minute mixed-scene endurance. Label T5/T6/T7/T8 `NOT_YET_VALIDATED` where applicable. A diagnostic duplicate save is **not** a substitute for normal DLC entry.

**A/B design:** A1 (baseline) → B1 (one switch) → A2 → B2 → A3, alternating adjacent short runs under comparable thermal/GPU frequency states. Warm the same scene and compare only stable windows; preserve boot, scene, save, inputs, output and audio path. Estimate effect using per-window frame time (ms), not only fps; inspect p50/P95/P99 and faults. Report confidence/noise. A ±2–3% difference in one short run is **not** evidence; require repeatability exceeding measured A/A variation. Re-run A if device frequency or CMA state drifts. A before and after is mandatory.

**Profiler interference:** `UA_PROF`, GL pass tracing, readbacks, shader dump, `glFinish` and heavyweight memory enumeration can alter throughput. The baseline run has only light `UA_FPS=1` and external /proc sampling; profile another matched run and measure the profiler overhead. Never report traced-frame fps as release fps.

## 5. Prioritized delivery board

A ranking for **expected information value**, not fabricated FPS savings. `P0` = immediate; `P1` = conditional after baseline; `P2` = later if profiling supports it; `H` = historical Horizon only.

| ID | Priority | Action | Borrowed reference | Definitive success/stop gate |
|---|---|---|---|---|
| N0 | P0 | Validate promoted native install, isolated candidate and benchmark harness | WoL current status; Cuphead `bench/`; Unity `profbench.sh` | Post-rename launch/cold save/load/audio input verified; 0 production/save hash changes. |
| N1 | P0 | Audio-enabled release baseline by scene, physical frames and memory | `UA_FPS`, `profcpu.py`, `memprof.py` | At least 3 comparable 60 s windows; precise P95/P99, readouts and CMA/faults; no missing KMS output. |
| N2 | P0 | CPU-on/off, UnityMain vs gfx worker vs Mono/JIT vs FMOD | `UA_PROF` + `profsum.py` | Dominant TID and module explained; sampler overhead checked (<5% ideally); only measured bottleneck enters next optimization. |
| N3 | P1 | Display pacing/SDL present classification | `UA_FRAME_RATE`, `UA_SWAP_INTERVAL`, host EGL trace | Distinguish app cap, swap wait, vsync/display pacing vs real work; no invisible/duplicate frames. |
| N4 | P1 | One-off GL pass census and suspected GPU bottleneck | `UA_GL_TRACE`, `UA_GL_TRACE_GPU`, Mali counters if supported | Identify per-pass target, calls, work; do not compare serialized `glFinish` times to untraced FPS. |
| N5 | P1 | Offline serialized quality profile in separate candidate | `pmunity quality`, `UA_QUALITY` | Exact before/after object/type-tree manifest; adequate visual parity or explicitly accepted fidelity change; repeatable P95 gain. |
| N6 | P1 | Renderer window size **only after GPU-bound proof** | `UA_RENDER_SIZE`, SDL path | Stable full-screen KMS output, correct input coordinate mapping, measured gain despite extra SDL GPU scaler. |
| N7 | P1 | Lifetime/GC/SwapPSS/fault study, targeted retention | Cuphead `MemReport` and `AtlasTrim` methodology, Unity `memprof.py` | Large owner identified; no ownership or save correctness violations; actual memory/swap-traffic reduction. |
| N8 | P1 | Verify inherited safe GL clear optimizations | `UA_GL_DSCLEAR` defaults ON; `UA_GL_SAMECLEAR=check` | Same pixels and state + measurable frame-time improvement; avoid re-“optimizing” default ON. |
| N9 | P2 | Scene-specific idle camera, effects, blank-pass work | Cuphead `CameraTrim`, `BlurIdle`, `RenderTextureFit` | Actual WoL camera/target owner and no-content proof; scene transitions and effect restoration pass. |
| N10 | P2 | ASTC memory-quality variants if GPU residency dominates | Unity guided ASTC conversion; Cuphead texture memory study | Source dimension/mip and format invariants checked, save/display visual gates and measured committed GPU savings. |
| N11 | P2 | JIT/Mono GC options and compilation/asset warm-up | Unity Mono profiling and Cuphead warm-up patterns | Hotspot is Mono/JIT or spikes are GC/compilation; no semantic/audio/save regression. |
| N12 | P2 | Conservative GL copy/clear equivalence or pass graph | Unity `UA_GL_RENAME=check`, `UA_GL_REC=census`; nxnative graph ideas | Exact captured preconditions + candidate acceptance; otherwise defer. |
| N13 | P2 | Whole-device scheduling/thermal/memory-pressure characterization | Unity `profbench.sh` clock/fault logger | Correlate rate with clocks/thermal without changing governor; no false GPU inference. |
| H0 | H | Release-equivalent **Horizon** phase ledger | Existing `NVN_PROFILE`; nx2android async GPU timestamps | Current ELF and visible screenshot, host wall/CPU/replay/present/swap spans; no trace-vs-release confusion. |
| H1 | H | NVN producer/alias graph for 1080p window slots | nx2android `alias_link/alias_check` | Every present slot's last legitimate producer identified without changing resource storage. |
| H2 | H | Post-provenance isolated 720p storage handoff | Producer/copy alias proof | Genuine visible pixels + matched frame/cma accounting; black output = immediate reject. |

The stage IDs above define **hypotheses and planned work**, not active tasks, shipped toggles or measured improvements.

## 6. N0 — protect the accepted Unity build; build a reproducible test rig

**Implementation facts to verify:** current launcher sets `SDL_VIDEODRIVER=kmsdrm`, `SDL_AUDIODRIVER=alsa`, `UA_DISPLAY=sdl`, `UA_PAD_NAME`, `UA_KEYMAP=start:escape`, original TRIMUI Player1 SDL mapping; it stores logs in `westofloathing/logs/`. `WOL_PROBE_SECONDS` only enables an optional bounded wrapper. It does **not** enable Unity's `UA_FPS` unless provided explicitly. The active launcher is not a generic `portmaster-unity` bench launcher.

**Procedure:**
1. Collect read-only hashes of accepted launcher, `ua_host`, generic Mono libraries, file manifest, APK and current saves; verify no game process running, frontend/state known, and memory/CMA baseline. Read `runtime-manifest.json`.
2. Create a **separate** `West of Loathing test.sh` / `wol-test/` candidate from known-good files, with distinct log/config/cache paths. If the player resolves a data directory from its package name or archive, validate isolation first; an APK or HOME copy alone does not prove save isolation. Use **duplicate** save data and read-only diff.
3. Verify KMS display ownership, audio sink exclusivity and working controller after the test launcher returns. If native host changes, rerun `test_unity_port`, `test_bounded_run` and upstream `runtime/host/test/test_audio_wiring.py`, plus actual-target audio behavior tests.
4. Run one 60-second no-modification **audio-enabled** candidate after post-rename, with screenshot and physical input. Preserve warnings, exit reason, process tree, audio nonzero PCM and source hashes.

**Pass:** visible title and gameplay + actual sound + real inputs + clean exit + saves unchanged. **Stop:** any path that touches production `data/` or `home/`, missing KMS capture, no audio, changed controller map, stale frontend, cold boot/lifecycle mismatch. Correct the harness before performance work.

## 7. N1 — precise baseline and pacing classification

**Core question:** is the pre-audio ~32.6 fps actually current when sound is active, and is the frame limit from game pacing, blocking swap, CPU execution, GPU work or memory faults?

Light baseline: `UA_FPS=1` on candidate, no GL trace or CPU profiler. External sampler: `/proc/<pid>/status`, `smaps_rollup`, per-TID `schedstat`/`stat`, major faults, `/proc/vmstat` swapin/out counters (with caution: system-wide, compare against other processes), `/proc/meminfo` MemAvailable/CmaFree, governor/devfreq residency, dmesg OOM, temperatures; independently record whether the KMS image changes as expected during scripted input.

Aggregate frame periods rather than only rounded fps:
- 30 fps nominal frame period **33.333 ms**, 32.6 fps **30.675 ms**, 25.5 fps **39.216 ms**, 4.61 fps **216.92 ms**.
- If an actual stable **32.6 fps** persists with p95 <33.33 ms, the remaining issue may be **memory/endurance/latency rather than steady-state FPS**, but a game-only fps counter doesn't prove displayed frames. Avoid unnecessary risk chasing higher fps before save and endurance acceptance.
- At fixed 30 Hz, a sharp 30 fps line does **not** imply no GPU headroom; compare pacing, thread CPU and a carefully controlled, reversible unpaced **measurement**, never make unpaced mode the default.
- FPS must remain linked to scene and output proof. The earlier Horizon 4.61 debug run is unrelated.

**Minimal env for an isolated test run (illustrative; do not invoke the accepted launcher or overwrite logs):**

```sh
# In a verified test-only launcher that inherits ALL the known-good SDL/ALSA,
# input, HOME and library settings, not a replacement for production:
export UA_FPS=1
# UA_PROF, UA_GL_TRACE, UA_RENDER_SIZE intentionally absent.
exec /absolute/test-only/wol-test/ua_host /absolute/test-only/wol-test
```

**Pass:** three stable paired baselines with full distributions and no driver/pacing ambiguity. **Stop:** the apparent fps count advances while physical output is unchanged, if audio is silently disabled, if scene load contaminates the timed interval or if clock residency differs substantially.

## 8. N2 — source-verified on-CPU/off-CPU sampling

The **pinned** `portmaster-unity` code includes `runtime/host/prof.c` and `tools/analysis/profsum.py`. `UA_PROF=250` or `500` starts a bounded sampler; default thread names include `UnityMain` and `UnityGfxDeviceW`, optional `Job.Worker*` and `FMOD*`. `profsum.py` attributes native/unwound regions, on-CPU percentage, blocked/waiting-for-CPU time, and Mono managed methods where available.

**Only after N1 passes**, compare baseline/profiler/no-profiler, same scene and clock. Use `UA_PROF_SECS=20` and `UA_PROF_START=<scene verified start second>` or explicit `prof.req` from the test harness. Set `UA_PROF_THREADS` conservatively to known real threads; inspect /proc TIDs rather than assuming names survive truncation. The project's upstream docs note an actual profiler crash under aggressive uncapped conditions, so do **not** combine all risky knobs in one run.

Read CPU time and wall time **together**:
- UnityMain CPU/wall near a full core, samples in game's JIT functions → **guest managed work candidate**.
- Similar CPU time in Unity engine/render worker or libGLES/Mali → engine submission or driver-side CPU overhead.
- Low CPU time with significant blocking in `eglSwapBuffers`, fences or futex → synchronization/pacing candidate, **not** automatic proof of GPU saturation.
- Low CPU with rising major faults/swapin → memory/I/O stalls.
- High system CPU from audio worker after audio fix → investigate bounded FMOD/SDL output independently; do not suppress sound to make fps “better.”
- Observe frame/GC distribution, not just average CPU: 1 s garbage-collection hitch may barely change average rate.

**Pass:** one dominant critical-path family supported by samples and timings, and profiler overhead small against A/A noise (<5% is a goal, not a promise). **Stop:** mixed scenes/threads, sampler alters stability, native unwinding incomplete, or no dominant family; then collect more targeted trace, not speculative code patches.

## 9. N3 — SDL/KMS display, vsync and physical presentation

Native WoL uses `UA_DISPLAY=sdl` + `SDL_VIDEODRIVER=kmsdrm`. Upstream `UA_FB_FLIP`, `UA_FB_BUFFERS`, framebuffer pan and the **zero-GPU-cost Allwinner display-engine scaler** were demonstrated on a **different 720×480 fbdev** path, not on this SDL/KMSDRM path.

For WoL:
1. Observe effective SDL display/GL backend, actual window size (1280×720 expected), EGL config, swap interval and KMS output.
2. Use `UA_FRAME_RATE` and `UA_SWAP_INTERVAL` **only as temporary measurements** once N1 establishes expected game pacing; check the pinned 2017.4 player's implementation branch. A test that removes pacing can alter game-time/update behavior and needs same-scene inspection; return to baseline immediately.
3. Collect wall+thread CPU time around swaps where supported, physical KMS capture count/interval, queue latency and GPU frequencies. A long `eglSwapBuffers` is a blocked CPU call; GPU execution time is separately measured, if supported.
4. Distinguish engine presents, scanout updates and **distinct** video frames. Do not count repeated, black or cropped frames as throughput.
5. If swapping is cheap and time is spent before it, close this path for now.

**Pass:** show where the last ~30–40 ms per frame actually lie and whether the renderer is capped. **Stop:** unpaced route hides a timing bug, breaks inputs/audio, or the display driver does not honor requested semantics.

## 10. N4 — one-off GL pass and shader-work census

The pinned host has:
- `UA_GL_TRACE=<period seconds>` and `UA_GL_TRACE_START=<seconds>` for a single representative graphics-frame trace.
- `UA_GL_TRACE_DRAWS=<n>` for *diagnostic only* per-draw bindings and framebuffer pixels, never an FPS run.
- `UA_GL_TRACE_GPU=3` which uses **glFinish per pass**; on other hardware this includes per-pass launch, start-up and potentially prior-frame waits. Never sum it and assert equivalent untraced GPU time.
- `UA_GL_TRACE_GPU=1/2` uses `EXT_disjoint_timer_query` when supported. Upstream Mali-G31 driver returned implausible/disjoint timings; Mali-G57 on TSPS must be independently vetted, with query availability/disjoint validation and no blocking result retrieval.
- `UA_SHADER_DUMP` / `UA_SHADER_OVERRIDE` for exact shader investigation (both affect Unity shader binary caching).
- `UA_GL_REC=census` and offline `framegraph.py` for a call/pass census; recorder mode itself is a separate intervention.

Trace after the game has *physically* reached a repeatable scene; log pass sizes, draw counts, clears, texture uploads, depth/stencil loads, resolve, framebuffer blits and call counts. Compare baseline scene's still frame with independently captured KMS output. Rank passes by **measured** or clearly marked estimated cost.

**Decision tree:**
- Many 720p fullscreen post/effect passes, same pixel work repeatedly → consider N5/N6/N9.
- CPU dominated in GL calls, draw count or repeated uploads → investigate batching/driver-call/texture upload ownership; a count alone doesn't establish cost.
- Large depth/stencil load churn → investigate inherited `UA_GL_DSCLEAR` (already default ON), **not** speculative invalidation.
- Frame's last copy to KMS costly → profile source, ownership and actual display routing before trying renderer handoffs.
- One-time shader compilation hitches → N11 cache/warm-up, not broad sustained FPS claims.

**Pass:** a real WoL per-pass inventory with scene+hash+source program, known timing limitations and plausible optimization locus. **Stop:** tracing corrupts timings so that the alleged hot pass exists only in traced mode; treat as structural data and validate separately.

## 11. N5 — conservative offline quality transformation (new candidate, NOT current default)

WoL currently runs `["shaders", "textures"]` only. Upstream `pmunity` supports a **quality** step, which can lower expensive settings (shadow resolution, soft shadow options, MSAA, number of pixel lights, post effects and optional Standard shader LOD choice where the required compiled variants exist). The six-game Mali-G31 results are examples, **not** WoL gains. A low-contrast black-and-white aesthetic still needs exact side-by-side assessment of dialogue, fonts, shadows and effects; "same gameplay" does not prove same picture.

**Before changing data:**
1. On the owner's original *copied* Unity data, inspect its `QualitySettings`, active renderer/shader type, serialized cameras/lights, depth/stencil/MSAA, shadow targets, frame capture and actual compiled shader variants. A Unity **2017.4 built-in** title does not automatically have URP, SSAO or cascaded shadows; skip absent features.
2. Offline inventory each changed object (file/node/PathID, original bytes, field/value, shader variant, size, dependency). Keep unchanged PathIDs and the exact two-node `main_scene` wrapper's hard checks. Don't enable quality when the converter has not proven that all transformed objects were recognized.
3. Produce *new* converted owner data and a separate packed APK, with a new name/hash; keep current conversion outputs intact and do not overwrite the installed APK.
4. Compare normal title, indoor, outdoor, text, UI, DLC, visual effects, menu/save and every important shader result. Distinguish **pixel exact**, tolerated image difference, or behavior change. Avoid global mobile shader fallback that deletes a needed shader.
5. If it changes the game intentionally, call it a **visual quality mode**, not a transparent optimization; provide opt-out.

**First candidates in this bucket** only if scene inspection confirms relevant costs: MSAA off if on; reduce expensive shadow map size if present; avoid unused postprocessing effects if there is a source-level proof of their inactivity. Do **not** blindly change every quality property or disable highp precision.

**Pass:** complete manifest of changes + compiled coverage + visually accepted screenshots + reproducible frame/committed-memory win. **Stop:** unsupported variants, missing text, overbright/dark lighting, nonmatching map panels, bad DLC shader or no measurable gain.

## 12. N6 — render size experiments when fill-rate-bound

The **pinned** `UA_RENDER_SIZE` / `UA_RENDER_SCALE` features are available, but on SDL/KMSDRM **the host scales with GPU work**, unlike the framebuffer display-engine scaler. Therefore the expected benefit is reduced game shader fragment work minus an extra upsample blit; it is not zero-cost scaling and may fail if CPU-limited.

Use a **single opt-in** per matched run at constant 16:9, e.g. **1152×648** (81% of panel pixels) *or* **1024×576** (64%). Do not mix both values into one causal test. Prefer a conservative first test, compare A/B/A as in §4, and inspect on-device scale uniforms, canvas, pointer/UI hit testing, readable fonts, black bars, physical KMS 1280×720 and audio. This is **not** the failed Horizon `ZERO_RENDER_SCALE`: it changes the Unity window resolution under the host's documented display routing, not guest NVN storage semantics.

**Pass:** valid fullscreen image, correct controls and scene transitions, same content and sustained wall-frame improvement >matched noise. **Stop:** Unity allocates same large internal camera textures, text/coords regress, extra blit erases gains, or a blank/static image appears. Only a device A/B can decide.

## 13. N7 — memory owner inventory, swap and GC

**Known:** a short native DLC run reached RSS ~711 MiB with swap ~173 MiB, and no long endurance/no-swap acceptance. WoL has packed StreamingAssets and the game's own Unity AssetBundle loader. Both the 4,155 + 627 texture counts and the 323 MB owner APK are **file/corpus facts**, not resident working-set sizes. Avoid adding compressed file size to RAM, or treating swapped pages as distinct physical resident memory.

**Measure externally first:** `smaps_rollup` RSS/PSS/SwapPSS; VMA split anonymous/file/shmem; peak `VmHWM`; minor and major page fault deltas; `pswpin/pswpout` or per-process I/O where available; `/sys/kernel/debug/mali0/gpu_memory` only if supported and permissions allow; account for shared, aliased, CMA and GPU pages separately (no double counting). Sample just before/after each scene transition and wait for memory settlement; GPU residency is not equal to process RSS.

**Borrow methodology, not code blindly:** Cuphead [`MemReport.cs`](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/MemReport.cs) uses Unity's runtime profiler, asset-type totals and bundle inventory. Its own comment warns `Profiler.GetRuntimeMemorySizeLong` can return **zero in a Release player**; a zero result on WoL would mean “not measured,” not “no textures.” Use isolated development-player/managed diagnostics only if available without compromising the accepted host. Offline serialized resource tables and `memprof.py` are an alternative.

**Classify owners:** Mono/JIT+GC heap, Unity engine allocations, immutable managed assemblies, mapped ZIP/APK/StreamingAssets, temporary decompression/asset loads, committed GLES textures/render targets, Mali/CMA, SDL framebuffers, FMOD queued audio, and file cache. Separate *live*, *reachable*, *reconstructible*, *aliased*, *GPU in-flight*, *dirty swapped* and *free inside an allocator*.

Only after proving lifecycle should you consider lazy load/unload, bundle unload, duplicate-resource elimination, smaller on-disk asset encodings, GC/heap configuration, or a decommit. Cuphead's [`AtlasTrim.cs`](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/AtlasTrim.cs) succeeds by proving boss-phase references are no longer needed and reloading before retry; **WoL's location/quest/bundle semantics are different**. Disabling an asset needed after entering/reloading Gun Manor is a serious correctness regression.

**Pass:** quantified owner of the top allocations or swap burst; actual resident/committed delta and reduced faults/swap traffic in a matched audio-enabled run; save+travel+reentry parity. **Stop:** only a higher `MemAvailable` or lower descriptor sum without attributable physical/reclaim proof, or new multi-second load/GC stalls.

## 14. N8/N12 — GL optimization checks; avoid redoing defaults

The pinned Unity host already implements `UA_GL_DSCLEAR=1` by default. Its upstream Hollow Knight Mali-G31 frame showed a gain from avoiding depth/stencil reloads, but this is **already in WoL's inherited host unless a version/setting guard prevents it**. First inspect effective startup configuration and compare OFF as a diagnostic control; do not count turning an existing default on as a new improvement.

Further upstream switches are promising only with matching WoL pass evidence:
- `UA_GL_SAMECLEAR=check`: verify redundant clears while still executing them; only after exact equivalence proof consider `=1`. Maintain GL state and per-frame dependency ordering.
- `UA_GL_RENAME=check`: source-to-destination copy equivalence check; default OFF. The upstream documents that no Hollow Knight copies were byte-exact on its Mali-G31. Never use `near` as an invisible “pixel-exact” win, because it allows differences.
- `UA_GL_REC=census` + `framegraph.py`: quantify dead passes, candidate load/store elimination and transformations in trace; merging GL passes is not automatically safe because texture sampling, depth/stencil, framebuffer bindings, attachments and cross-frame reads matter.
- `UA_GL_TRACE_GPU=3` is a **serialized probe**, not a production optimization or a valid absolute GPU-frame wall-time measurement; it deliberately changes scheduling.

**Pass:** effective switch status demonstrated, exact image/state equivalence, no GLES errors, stable full frame and repeatable CPU/GPU/frame-time improvement after restoring light instrumentation. **Stop:** any black frame, invalid draw, read-after-write alias, changed blend/fade, or trace-only gain.

## 15. N9 — scene-specific camera, effect and geometry work (Cuphead patterns)

Cuphead's [`CameraTrim.cs`](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/CameraTrim.cs), [`BlurIdle.cs`](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/BlurIdle.cs), [`RenderTextureFit.cs`](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/RenderTextureFit.cs), [`HeavySprites.cs`](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/HeavySprites.cs) demonstrate targeted managed-game optimizations—not generic knobs.

Conditional WoL adaptation must establish:
- Which cameras actually render per title/interior/outdoor/map and whether one is objectively idle; don't remove a camera that holds an invisible gameplay mask, an effect or a fade.
- Whether a RenderTexture exceeds the physical panel and is always sampled downscaled, with no arbitrary shader UV/texel offsets, blurs or UI targets that rely on original dimensions.
- Whether an off-screen actor's animation has events, collisions, state-machine transitions, audio or quest consequences. Never imitate broad animation culling without these exclusions.
- Whether geometry mesh simplification is exact for the relevant textures (not a generic rectangle substitution).
- Whether a full-screen blur/colour effect processes a constant/transparent image and has an exact identity or transparent-composite proof.

A safe custom managed helper would require **WoL-specific Mono.Cecil patch sites**, original-byte/IL assertions, metadata/type checks and a default-off bypass. The current WoL packer patches only Rewired and one proven `File.Exists` call; it has **not** deployed Cuphead's scene optimizations. Rebuild the **owner-local** APK, verify 67 assembly closure, then test saves and real renderer behavior. This bucket should start only after N4 identifies a measurable redundant pass.

**Pass:** camera/effect operation objectively removed, ≥one relevant pass's costs attributable, screenshot parity across UI/transition and reactivation. **Stop:** unable to prove content ownership, effects resume late, colliders/events differ, or performance change below noise.

## 16. N10 — ASTC and texture residency

The current conversion already uses **guided ASTC 4×4**, 1.0 scaling and preserved mips. Do not repeat the Horizon-side BC→ASTC suggestion as though native WoL still uploads all of its desktop BC content unconverted.

**If and only if GPU memory is a dominant measured owner**, inspect texture formats, dimension distribution, actual residency and pinning/duplicate files:
- ASTC 4×4 has **16 bytes / 16 texels = 1 byte/texel**, excluding mips/padding.
- ASTC 6×6 has **16/36 ≈0.444 bytes/texel**, a theoretical **55.6% reduction in the compressed texture payload** versus 4×4 for the same dimensions; that is **not** a prediction of total RSS/CMA saving. 5×5 is **16/25=0.64 byte/texel** (36% reduction). Test only a format the exact converter, player and GPU accept; quality on line art/fonts can degrade significantly.
- Mip stripping or texture downscaling is a visible quality change and must not be mixed with ASTC block-size A/B. The original acceptance specifically preserved mip counts/dimensions.
- Compare representative text, border outlines, tonal gradients, inventory icons, UI, intro, multiple regions and DLC under identical GL/sampling state. Inspect actual compressed residency and original/candidate APK size separately.
- Preserve the narrow two-node `main_scene` invariants and offline packer checks before any device launch.

**Pass:** visible/readable image fidelity approved plus committed GPU/SwapPSS reduction and no decode/upload regressions. **Stop:** corruption or no comparable physical memory reduction. This is P2 because memory's largest owner has not been established.

## 17. N11 — Mono JIT, GC, audio and load-time stutters

The target is Unity **2017.4.19f1** via the generic **Mono 5.0.1-era** bridge, not the former Switch IL2CPP. Managed method CPU samples can legitimately guide Mono optimizations, but a faster JIT option in another Unity game is not evidence for WoL.

**JIT:** Use `UA_MONO64_OPTIONS` or Mono's relevant environment options only if supported by the pinned bridge and checked in startup logs. Test one safe optimization flag at a time with methods attributed by `profsum.py`. Replaying the same input and serializing the same save must succeed; do not allow floating-point, exception or ordering changes to be described as “exact” without evidence.

**GC:** Use `UA_FPS` GC counters, managed allocation/fault samples and observed pause distributions. `UA_MONO64_GC_SLICE` is documented in the pinned host; inspect the current package and player support before changing it. `UA_GC_BUDGET` specifically targets newer games disabling collectors and is not automatically a Unity 2017 fix. Major GC reductions matter most when P95/P99 hitches are GC-dominated; always check new heap size/SwapPSS.

**Startup:** Shader cache/JIT warm-up should target real first-usage pauses proven by logs and unchanged game effects. A setup-time conversion saving is a *first-install UX win*, not gameplay FPS. Avoid merging offline converter tweaks into runtime timing A/B.

**Audio:** The local FMOD fix routes S16 stereo PCM to SDL/ALSA at the engine's **24 kHz** path. Verify queue/drain, backpressure, nonzero PCM, underruns, shutdown order and real sound during any host/runtime change. Pinned tests cover callback wiring, dummy SDL lifecycle and silent target preflight, but dummy playback cannot certify audible game sound. Never use a muted bench as sole production-optimization acceptance.

**Pass:** a measured class of JIT/GC/audio/compilation hitches improves in representative scenes without increased memory, lost audio or changed saves. **Stop:** GC heap ballooning, audio silence/crackle, first-scene stutter moved elsewhere, or unverified deterministic output.

## 18. N13 — device clocks and memory-pressure analysis (read-only)

The TSPS Mali-G57 may use a different driver, kernel power policy and display path from the H700 Mali-G31 in Cuphead/Unity upstream measurements. Read actual frequencies, available devfreq OPPs, residency, cool-down dynamics, thermal zones, cooling devices, CPU utilization/wait and system competing work during N1–N4. **Do not assume that higher CPU utilization reduces GPU clocks or that 600 MHz is a firmware cap.** The older Horizon read-only report found Mali `simple_ondemand` and 600 MHz `max_freq` in one state without an established cooling-device cause; that is not a native-game GPU-work profile.

If `gpucnt` cannot probe the TSPS driver/counter version, say **unsupported**; do not reinterpret Mali-G31 counter names/units as Mali-G57 data. Upstream performance findings are useful for creating hypotheses, not for copying per-fragment cycle costs.

**Pass:** a matched-frame study explains thermal/clock variation and excludes frequency differences from A/B effects. **Stop:** cooling policy unknown, counter driver unsupported, or a candidate requires disabling throttling.

## 19. N14 — hard game coverage before enabling any default

**Required certification order:**
1. Title/UI normal launch after promotion (not merely a hash-preserving rename).
2. Character creation and real controller button-by-button audit (not a synthetic script labeled physical).
3. Reproducible indoor/outdoor walking and map/dialogue/inventory.
4. Standard save, clean exit, cold restart, load, then semantic save output.
5. Normal DLC quest entitlement/entry, not an arbitrary duplicate save loading the location.
6. Multiple 10-minute mixed-scene samples; then longer **20–30 minute** endurance with sound and screen on. Compare beginning/end P95/P99, RSS/SwapPSS, swapin/out, CmaFree, thermal and GPU frequency; no unbounded growth or late OOM.

**Promotion gate:** default-on only after at least three stable adjacent A/B pairs in the relevant real scenes, intact picture/audio/input/save and no memory regression, with original install integrity verified and a safe rollback. Candidate to owner review before replacing accepted files.

## 20. Experimental Switch/Horizon branch — previous research checkpoint

**Read this only for experimental `build_horizon.sh` / `runtime/wol-adapter.patch`. The installed game does not use this code; its ongoing development is active.** Earlier H0–H4 order is **superseded by section 25**. This older checkpoint must not be used to claim Unity performance gains.

### H0. First reversible experiment: release-equivalent phase ledger

Observed old v327680 title evidence: 3×1920×1080 colour + 1×1920×1080 depth, display 1280×720, guest `Screen` 1280×720, crop from larger source, debug run **4.61 fps** using `AW_RELEASE=0`. Older **25.5** is unvalidated for current diagnostic. `ZERO_RENDER_SCALE=2` produced black frames with `target-seen=0`; pixel force offset +32/+36 on current `UpRender` holds **16 and 9** (ratio), not 1920/1080. `WOL_DISPLAY_MAX=1280x720` and 11 create-request size rewrites did not alter source or FPS, respectively. Stop re-proposing these.

Use a current **release-equivalent** candidate with an opt-in **wall+thread-CPU phase ledger**:
- previous present exit → next present entry (includes guest, pacing and other work: *not* pure IL2CPP);
- NVN replay wall and CPU;
- fence/finish/context waits wall;
- present quad setup and draw CPU-wall;
- actual swap wall; independent physical KMS frame.
- asynchronous GLES GPU present timer only if `EXT_disjoint_timer_query` is available, validated and nonblocking; otherwise “unsupported.”
- accumulate per frame but print every **64 presents**; pair OFF/ON/OFF with identical scene/save, ELF, thermal, memory guards. No `glFinish` inserted by the instrumentation.
- Diagnose CPU busy versus waiting by wall/CPU ratio **plus** on-CPU/off-CPU samples and GPU evidence; low CPU does **not** prove GPU bottleneck.

**Gate:** phase sums account for total wall time to a documented tolerance (aim ±5%, allow overlaps), profiler ≤5% perturbation, verified nonblack KMS. Reject any guessed 1080p “blit share” without a measured span. A 1080p sampled input blitted to a 720p target need not shade 1080p destination fragments.

### H1. One NVN provenance read-only probe after H0

Borrow [nx2android `alias_link` and `alias_check`](https://github.com/shirai91/nx2android/blob/6444d67694a4015003fc31c6c74f110fac43502a/nxnative/dm/android/gfx_vk_tex.c#L208-L281) **as ideas**, not its Vulkan structures: identify actual pool/offset/range, texture descriptor, crop, alias set, last CPU flush/write, last GL attachment, last copy/resolve, texture upload and final sampled GL image, with a reliable **run+PID/start/ELF identity**. Capture bounded events for every one of three window slots and associate each with the same visible KMS frame. Include `main.text.seg+0x540fd8` attribution. If the image is not a render target directly, the producer may be a copy or upload—not an excuse to declare it blank.

**Gate:** last legitimate producer for all window image slots is established, and preserving that producer reproduces visible pixels. No resource allocation/layout/storage change before that. `target-seen=0` proves only the absence of **observed** direct RT binding by that probe, not that guest rendering is absent.

### H2. Conditional 720p storage and present handoff (NOT first)

A nominal four 32-bpp 1080p surfaces occupy **31.64 MiB**, and at 720p **14.06 MiB**, potential **17.58 MiB** nominal saving, before alignment/copies/alias/multi-sampling. This is not necessarily a large gain against measured anonymous memory+swap and **not** proof of a GPU-time win.

Only consider when H0 establishes a present/storage critical-path cost **and** H1 identifies the producer/alias contract. A correct implementation preserves logical 1080p guest addressing or rewrites **all** descriptor/pitch/copy/UV/readback relationships consistently, with CPU/GPU ownership and in-flight lifetime maintained. A black or 1-colour frame—even with more present calls—is a hard FAIL.

**Gate:** same real frame output, three slot producers, no GL errors, matched title/gameplay screenshot parity, lower actual committed physical pages or measured per-frame wall time, stable CMA with historical ≥65,536 KiB preflight, no new OOM. Do not mix with Unity's `UA_RENDER_SIZE`.

### H3. Post-measured memory/format interventions

Older [Oct 29 findings](optimization-findings-2026-10-29.md) demonstrate physical/aliased page accounting and **no live 0x39 packed4444 textures** in one title session; older “130 textures, 29.5 MB saving” was retracted. Existing M6 create-time BC cache had **HIT=0** for real content because actual payload entered via `CopyBufferToTexture`, and its early apparent hits matched empty data. Do not reactivate these as universal wins. GPU descriptor byte sums, anonymous mapped sizes and SwapPSS are **not additive physical RAM**. Zero-swap research remains blocked on exact allocator ownership and live/free page proofs; `madvise` or decommit based on a guessed idle pointer is forbidden.

For future game scenes: only retest a packed format or compressed upload when a fresh **scene-local, current-ELF** descriptor census shows nonzero eligible live objects and a reconstructible write route. Measure committed bytes and upload CPU alongside displayed pixels, not historical cross-run texture IDs.

### H4. What NOT to port from nx2android to this Mali/GLES runtime

Its Android path uses **Vulkan**, relies on **BC texture format** device support (README explicitly excludes Mali/PowerVR), and uses `vkQueuePresentKHR`/`vkCmdBlitImage`, Vulkan fence slots and an async present worker. These are architectural studies, not a drop-in backend. The async queue may increase latency/memory and can only be tested if H0 proves present-thread blocking. Its host-image eviction requires explicit overlap/liveness/reconstructibility checks; translating its `EVICT_KEEP=60` into WoL without a correctness proof may delete live window/texture content. Its TBDR tools estimate attachment loads/stores and flag potential redundant passes but do **not** establish actual GPU time or capture all copy/clear hazards.

## 21. Do-not-repeat list and misconceptions

| Rejected / already inherited idea | Correct scope |
|---|---|
| Switch `UpRender +0x20/+0x24` as pixels in v327680 | Current 16:9 ratio; changing to 720p corrupts fit rather than fixes resolution. Old Unity v23 pixel patch is distinct. |
| `WOL_DISPLAY_MAX` and 11 unconditional guest request rewrites | Tested; no change / no throughput gain. |
| `ZERO_RENDER_SCALE=2` “+32% FPS” | Black KMS, 1 colour, no observed target writes; **failed**. |
| Historical “25.5 release FPS” versus `AW_RELEASE=0` “4.61 debug FPS” | Not a matched build, scene or instrumentation regime. |
| “0x39 format saves 29.5 MB” | Retracted cross-run false aggregation; 0 live 0x39 in one current-scene screening. |
| Old M6 create-time compressed cache | Later content arrives through copy, no demonstrated memory win; not native Unity pipeline. |
| `UA_GL_DSCLEAR` as a new native knob | **Default ON** in pinned upstream; first verify effective state, then compare OFF only diagnostically. |
| Cuphead `CUPHEAD_RTFIT`/`AtlasTrim`/`CameraTrim` generic flags | Game-specific managed helper; WoL doesn't have them until a proved WoL-specific patch is compiled and packaged. |
| Apply fbdev display scaler on SDL/KMSDRM | Different host path; SDL uses an extra GPU blit. |
| Disable audio for benchmark acceptance | Production has real FMOD→SDL/ALSA; silent performance-only benchmarks are not equivalent. |
| Compare `VmRSS+VmSwap+Mali descriptors` as total memory | Double-counts or mixes virtual mappings, swap and GPU allocations. |
| `perf` low CPU utilization automatically means GPU-bound | Could be swap, futex, display pacing, I/O, contention; need stall attribution. |
| More presents mean better visible output | Black/duplicate/stale frames invalidate result. |
| Automatically deploy latest upstream host to existing game | Installed host and its audio fix are **pinned**; later commits require audit, rebuild and full regression. |

## 22. Exact next execution sequence and stop/go decisions

This is a dependency chain; **do not execute every item as a batch**:

1. **N0 test-only candidate gate.** Independently verify accepted native install hashes, saved-game copies, post-rename normal launch/physical screen/audio/controls and safe cleanup. If not valid: **STOP**.
2. **N1 matched audio-enabled native baseline** with `UA_FPS=1` and external /proc/clock/CMA metrics in a scene with a verified moving picture. Repeat 3×; require P50/P95/P99/hitches and actual scanout observations. If current ~32.6 fps is valid throughout gameplay, prioritize memory/endurance, not speculative 1080p Switch fixes.
3. **N2 one on/off CPU sampling A/B** with `UA_PROF` and `profsum.py`; quantify profiler overhead and identify CPU vs blocking/driver/GC/audio. If dominant path unknown: **STOP and refine instrumentation**, do not alter renderer.
4. **Conditional fork:** GPU/driver-bound → N4 pass census then **one** of N5 or N6 or N8; CPU-bound → one Mono/UnityMain hotspot N11 or N9; fault/swap-bound → N7; present/vsync-bound → N3. Measure each candidate with A/B/A and independent KMS proof.
5. **N14 completeness:** normal DLC entry, cold save/load and ≥20-minute mixed-scene endurance. Only then propose an opt-in or default with new build SHA, exact effects, rollback file and attribution.

**A candidate is a win only if its measured, visual, functional and safety gates all pass.** No “probably,” no unmeasured FPS uplift, no promoting a file size reduction as resident-memory saving, and no conflating the old Horizon evidence with current Unity performance.

## 23. Suggested development commits (planned, not performed)

| Proposed commit | Files | Scope |
|---|---|---|
| `test(native): add isolated audio-enabled performance receipt format` | future `tools/native-bench/` + tests | Validate run IDs, PID/boot/ELF, prod hash parity, independently checked display and audio. |
| `test(native): add matched frame and memory A/B reports` | future offline analysis scripts | Percentiles, CPU/swap/cma deltas, clock drift, unknowns; no live renderer change. |
| `docs(native): record first post-audio baseline` | future `docs/native-unity-performance-results.md` | Actual measurements, scene hashes, method, limitations. |
| `perf(native): <single proven hotspot and opt-in>` | isolated source/packaging candidate | New flag defaults OFF, exact expected gain, picture/audio/saves tests, revert path. |
| `docs(horizon): qualify release ledger and producer graph` | historical evidence/docs only | No effect on active port; any actual runtime changes require separate proof. |

Do not commit any generated game data. Keep evidence receipts minimal and reproducible.

## 24. Direct source links, pinned where material

**Current WoL:** [README](../README.md), [current Unity verification](native-unity-port.md), [native runtime build/audio patch](../runtime/unity/README.md), [owner converter](../tools/unity/README.md), [converter configuration](../tools/unity/convert.json), [launcher](../West%20of%20Loathing.sh), [historical Horizon roadmap](optimization-roadmap.md), [historical Oct 29 findings](optimization-findings-2026-10-29.md).

**portmaster-unity:** [profiling](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/docs/profiling.md), [runtime options](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/docs/runtime.md), [quality](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/docs/quality.md), [Mono ARM64](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/docs/mono-arm64.md), [profiler implementation](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/runtime/host/prof.c), [GL trace](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/runtime/host/gltrace.c), [GL optimization](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/runtime/host/glopt.c), [device benchmark](https://github.com/wild1walker/portmaster-unity/blob/913debc122b8234a3db56939a4728d9438972ce2/tools/device/profbench.sh).

**portmaster-cuphead:** [technical](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/docs/technical.md), [benchmark tools](https://github.com/wild1walker/portmaster-cuphead/tree/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/bench), [camera](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/CameraTrim.cs), [render target fit](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/RenderTextureFit.cs), [asset lifetime](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/AtlasTrim.cs), [memory inventory](https://github.com/wild1walker/portmaster-cuphead/blob/4c94d4cdf7b1c96b5f47ad539b60e9dc0ff394a4/helper/MemReport.cs).

**nx2android:** [NVN→Vulkan resource identity](https://github.com/shirai91/nx2android/blob/6444d67694a4015003fc31c6c74f110fac43502a/nxnative/dm/android/gfx_vk_tex.c), [present queue](https://github.com/shirai91/nx2android/blob/6444d67694a4015003fc31c6c74f110fac43502a/nxnative/dm/android/gfx_vk_present.c), [GPU timestamp collection](https://github.com/shirai91/nx2android/blob/6444d67694a4015003fc31c6c74f110fac43502a/nxnative/dm/android/gfx_vk_core.c), [TBDR budget estimator](https://github.com/shirai91/nx2android/blob/6444d67694a4015003fc31c6c74f110fac43502a/nxnative/dm/gfx/tools/tbdr_budget.py), [build-ID NSO rewriter](https://github.com/shirai91/nx2android/blob/6444d67694a4015003fc31c6c74f110fac43502a/nxnative/dm/tools/patch_nso.py).

**Final state of this document:** a thorough prioritized research roadmap. It does not certify a new run, patch, measured frame-time reduction, new memory headroom or production deployment.


## 25. Current Horizon v327680 re-audit — 2026-10-30, HEAD `38f05f66`

**Current decision authority for the actively developed, isolated Horizon/NVN→GLES runtime.** This supersedes previous `25 and older `20/H0–H4 priority orders. The accepted/installed native ARM64 Unity/Mono port, including sound and saves, remains a **different implementation** with its own N0–N14 plan. This is a **source and published-evidence audit, not a new device run or implemented optimization**. Review basis: 13 further commits through `38f05f66a5ee14f75bd0fdf15bae9c88e00c419c` (2026-10-29 22:04:59 UTC).

### 25.1 Newly verified status

| Area | Valid fact | Evidence limitation |
|---|---|---|
| Old heavy gameplay frame | Release-like scripted run with ~71–73 indexed draws: **42.1–43.1 ms/frame**, replay **25.9–26.9 ms**, present ~**1.7 ms**, ~23.2–23.8 runtime presents/s. | [Current-status receipt](../evidence/update-327680-status/README.md) is a **different ELF/run** from the new E1b metrics. Distinct physical displayed FPS/P95 remains uncertified. |
| E1b per-op sampler | ELF `21e23b58…`, 90 rows in [raw V2 data](../evidence/horizon-roadmap25-device-status/e1b-op-v2-lines.txt): median three `DrawArrays` = **6.634 ms total wall**, **1.835 ms mean thread CPU/call** (~5.505 CPU ms for three); two `ReportCounter` = **10.132 ms total wall**, **0.105 ms mean thread CPU/call** (~0.210 CPU ms for two). | **Frame attribution is buggy**; source mixes first op of new frame with previous frame (below). Low thread CPU means blocking/off-CPU time, **not proof of GPU fence cost**. |
| E1b sample scene | [E1b profile](../evidence/horizon-roadmap25-device-status/e1b-profile.txt): first 60-frame `NVN_PROFILE` shows **462.637 ms/frame**, **44.180 ms replay**, **3.606 ms present**, `VmRSS=755544 kB`, `VmSwap=257584 kB`. | Startup/other scene dominates frame period; there is **no verified 71–73-draw scene and matching 42–43 ms baseline** in the 90-row E1b receipt. No profiling OFF/ON overhead proof. |
| H-M0 CMA pressure | [95 host samples](../evidence/horizon-roadmap25-device-status/mem0-samples.txt): **CmaFree min 12 kB, median 2,448 kB**, **66/95** samples below **65,536 kB** launch gate; `MemAvailable` min **34,812 kB**; `SwapFree` drops from **2,037,628 kB** to at least **955,248 kB** before recovery. | Includes prestart/post-exit samples; no explicit timestamp/PID/scene columns. `CmaFree` and `SwapFree` are **system-level**, not the exact attribution of one texture or guest pages. No OOM proven. |
| Shadow mirrors | [Device status](horizon-roadmap25-device-status-2026-10-30.md): `WOL_TEX_SHADOW_MB=192` default-OFF test, **zero `WOL_TEX_SHADOW_GC` evictions**. | No evictions are **not an exact live/peak byte census**. Source `sh_bytes` does not track all other free/replace paths; cannot conclude all CPU mirrors are immaterial to RAM use. |
| Async | [Async test](../evidence/update-327680-async-qualification/README.md) still stops `NVN_PROGRAM_INVALID` at `main.text.seg+0x532994`, `detail=0`; experimental pins did **not** fix it or trigger `NVN_PROGRAM_PINNED_DESTROY`. | Nonzero guest program recycling is **unproved**; null/unbind/state mismatch also plausible. Corrected ACK requires **exact `WOL_ASYNC_ACK=1`**, but an ACK does not qualify correctness or memory. |
| Draw target | [Target trace](../evidence/update-327680-drawarrays-target/README.md): two 7-vertex draws see **1280×720 flags=0x8**, one sees **logical 1920×1080 flags=0x9**, matching a window-texture family with `actual=1280x720`. | Flags ≠ unique resource identity; `id=0` unpopulated; **logical pixels ≠ physical fragment count**. Previous storage scale black-screened and v24 UpRender pair **16/9** is aspect, not pixel size. |
| Earlier speed flags | [Status](../evidence/update-327680-status/README.md): uniform cache is a wash, finish→flush no reliable replay gain, async needs qualification, lowered storage previously gave black visible output. | None is a validated ~9.8 ms improvement. |

**Performance arithmetic:** **43.13 → 33.333 ms** needs **9.80 ms/frame removed from the real critical path** (~22.7%). A perfect 6.84 ms DrawArrays-only reduction would still leave **36.29 ms** (~27.6 FPS). A different run's ~10.1 ms ReportCounter wall span is **not** a guaranteed recoverable 10.1 ms in the 43 ms scene; deferred GPU/scheduler waits can merely move to another call.

### 25.2 Source audit: H-E1b has a first-op-of-next-frame accounting bug

At the **latest effective hunk** in [`runtime/wol-adapter.patch`](../runtime/wol-adapter.patch), patch lines approximately **13036–13056**, the code:
- samples clocks around `nvn_replay_record(&r)`;
- adds the **current** operation to `ops_cnt[k]`, `ops_wall[k]` and `ops_cpu[k]`;
- **then** checks `ops_frame != nvn_replay.last_frame`, prints `WOL_OP_V2 frame=<new>`, and clears the bucket.

Thus each boundary report contains the **last frame's remaining selected ops plus the first op of the new frame**, labeled **as the new frame**. Frame 0 prints prematurely with one counter; a trailing incomplete bucket may not be flushed. If the opcode mix is stable (three DrawArrays and two counters), the resulting counts **look correct** despite false frame ownership. The raw median numbers remain raw observations, but cannot be joined to a particular displayed frame or exact `NVN_PROFILE` period. The static bucket is also not keyed by command list/thread; multi-worker ownership has not been tested. Printing one line per frame may disturb timing.

**Fix BEFORE further conclusions:** flush a completed frame bucket **before** adding the new frame's first op; tag the selected opcode's **entry** frame/list/worker owner; include end-of-run flush. Use a distinct `WOL_OP_V3` prefix with `frame, draw_count, class, count, sum_wall_ms, sum_cpu_ms, mean_wall_ms_per_call, mean_cpu_ms_per_call`, and a declared residual/uncategorized time. Aggregate at a completed frame/present boundary (or label delayed completion accurately); no per-op printing. Prove no double-counting and correct units in data-free tests for empty/mixed frames, frame/list rollover, multiple threads, terminal partial bucket and `sum≈mean×count`. Keep flag **default OFF**.

**Not yet demonstrated:** that median 10.132 ms in `ReportCounter` is a *GPU* fence instead of host futex/scheduler/page fault/driver backpressure, or that the 6.634 ms `DrawArrays` total occurs on the same heavy-scene 43 ms critical path. The prior first-use/raw 64-op interpretation error (“50.5 microseconds”) remains **retracted**. E1b is **implemented but its current frame-level attribution is insufficient**.

### 25.3 Critical CMA/guest-memory risks, separated from GPU optimization

The current **65,536 KiB `CmaFree` preflight** is an **admission gate, not a live reservation**. Observed system CMA often falls to **0–few MiB**; swap pressure is high. This blocks **assuming** there is room for an extra async framebuffer, pinned shader lifetime, independent render target or snapshot; it does **not** prove that any specific future allocation must fail or identify which object consumed CMA.

**P0 passive memory ledger, recorded in the same future matched gameplay run:** monotonic time, boot ID, exact PID/start tick, scene/frame phase, `CmaFree/CmaTotal`, `MemAvailable`, `SwapFree`, process `smaps_rollup` RSS/PSS/SwapPSS, `VmRSS/VmSwap`, faults, swap-in/out from `/proc/vmstat` and available Mali/DMA-buf live allocation stats. Record the prelaunch, startup, active, transition and cleanup phases separately; do not add overlapping RSS+GPU+CMA totals. Correlate deltas with existing guest pool+offset+length, GL texture/FBO name, format, logical/host dimensions, allocation/free generations. **Correlation is not causation:** attach a real allocation owner or leave unknown.

**Guest memory route:** identify resident anonymous mappings, alias sets, page use and last access before proposing on-demand commit/reclaim. Never discard guest pages, skip a rendering copy, disable swap, lower the runtime memory floor or shrink a render target without liveness+alias proof and visible KMS acceptance. The target of fitting comfortably within ~963 MiB **without** swap is not currently achieved.

**Shadow code warning:** the [`nvn_textures.h` overlay](../runtime/wol-adapter.patch) around 13079–13094 increments static `sh_bytes` on `cpu_snapshot` malloc and decrements it on that specific eviction, while the same overlay has other `free(t->cpu_snapshot)` and replacement paths that are **not coupled to the counter**. The eviction estimates `width×height×4` instead of storing exact buffer sizes, and `cpu_generation` is not true access recency. This can distort the supposed 192 MiB budget under churn. The zero-eviction test only shows its eviction path **did not fire**; leave it OFF. A trustworthy read-only exact alloc/free/replace census must precede any active cache pruning.

### 25.4 Async pinning: unproven root cause and safety issues

The async failure is still `NVN_PROGRAM_INVALID detail=0`; no recorded evidence shows which nonzero program was destroyed between snapshot and worker lookup. The pin experiment failed to change that. There are also source-level hazards in the experimental code: `nvn_snapshot_unpin()` indexes `nvn_programs[s->pins[i]]` **before** checking `s->pins[i] < 256`; the snapshot increments a program `async_pin` **before** ensuring `npins < 256`, potentially leaving untracked pins on overflow. No complete proof exists for dropped-frame, shutdown, job-order, snapshot-generation and live-queue retirement safety.

**Do not enable or tune async/pinning** until exact program object (including zero), stage mask, bind/unbind, snapshot generation, guest and worker IDs, caller PC, create/finalize chronology and failure join are collected **read-only** against synchronous control, AND a measured safe incremental GPU/CMA budget exists. If the object is zero/unbound, fix that state contract; only if retirement of an actual nonzero owner is demonstrated should generation-tagged pins and fence-bound release be implemented. Exact `WOL_ASYNC_ACK=1` is a **test acknowledgment, not proof of program qualification**.

### 25.5 Current dependency board

| ID | Status/rank | Work and acceptance |
|---|---|---|
| **H-E1b** | **done, incomplete/invalid for scene-critical conclusion** | Per-op class wall/CPU and unit labels exist, but frame rollover and unmatched scene invalidate attribution as steady ~43-ms gameplay. |
| **H-E1c** | **DONE 2026-10-30** | V3 frame ownership repaired and run OFF/ON/OFF on three fresh boots against the same real gameplay: p50 40.608 / 40.412 / 40.184 ms, p95 41.86/41.35/41.39, ledger overhead **+0.04 %**, KMS scene match at 180/240 s. [evidence](../evidence/horizon-e1c-abc-2026-10-30/README.md). Terminal bucket still unflushed (≤1 frame). |
| **H-M1** | **DONE as passive series** | CMA/SwapPss/VmSwap/pswp in the same three arms: `CmaFree` 128–130 MB preflight → 0.3–1.9 MB in gameplay → 117–130 MB after exit; VmSwap ~0.92 GB. System-level, no owner attribution. |
| **H-P1** | **DONE 2026-10-30 — negative** | The wait is `glFinish` (`nvn_counter_time.h:17`, twice per frame). Removing it (`COTM_COUNTER_CPU_TIME=1`) cuts the class 8.48 → 0.01 ms but the frame only 40.412 → 39.894 ms; the GPU work reappears in the unaccounted remainder. Counter sync is not a 30 FPS lever. |
| **H-G1** | P1 conditional | Join the three 7-vertex draws to real GL FBO/program/window slot; validate existing nonblocking `WOL_GPU_TIMELINE`, reject disjoint/unsupported timers. |
| **H-M2** | P1 memory architecture | Prove real owner of CMA and swapped guest pages; quantify safe reuse/reclaim only with liveness and alias safety. |
| **H-A0/A1** | P3 BLOCKED | Shader program object identity and safe incremental CMA budget first; recent pin experiment is not accepted. |
| **H-R1** | P2 conditional | One verified CPU/pass/copy/sync bottleneck only; a smaller gain than 9.8 ms is useful but **not 30 FPS acceptance**. |
| **H-ACCEPT** | final | Matched A/B/A/B/A, distinct physically displayed ≥30 FPS and p95 ≤33.333 ms in representative motion, memory/CMA and full save/audio/input/scene/recovery gates. |

### 25.6 H-E1c — ONE next reversible device experiment

**Hypothesis:** the 10-ms-class ReportCounter off-CPU span seen in E1b might explain the missing 9.8 ms **only if it recurs in the very same ~43-ms steady gameplay**, with frame ownership repaired and a real named wait. This test can falsify that claim.

**One patch:** default-OFF `WOL_OP_V3=1` (or versioned `WOL_OP_SPLIT` output). Flush preceding frame **before** adding first op of next; tag event by actual entry frame, list and thread; report per-class `count`, `sum_wall`, `sum_cpu`, `mean_ms`, plus max and any **explicitly named** existing GL/fence spans. Preserve identical GL, queue, assets, allocator, shaders and swap policy. No additional `glFinish`, `glFlush`, synchronous query read, context hop or per-op stdout. Unit tests cover start, rollover, zero ops, mixed op counts, terminal flush, worker-thread ownership and unit math.

**Device procedure:** use the working `SDL_GAMECONTROLLERCONFIG`/`TRIMUI Player1` mapping and existing repeating scripted presses; the historical valid heavy scene needed **~260 s**, not 90 s. Verify matching actual KMS game pixels/camera/scene and **≥3 matched 60-present windows** at ~71–73 draws each. The legacy E1b first-60 `462.637-ms` startup window is **not an acceptable control**. Run **OFF→ON→OFF** with the same release build/scene/thermal state and passive read-only H-M1 sampler. If boot/memory/temperature drift persists, use matched fresh-boot A/B/A/B/A pairs rather than pretending a sequential run is matched.

**Pass/stop:** ≤5% instrumentation overhead vs stable controls, exact per-op/frame bucket accounting, matching real scene and controller, no stale/black KMS image, no new error/OOM, safe CMA and MainUI recovery. If the total frame is not in the old **42–43 ms** band, classify the new run as a *different baseline*, not a speed change. Tag ELF SHA, source commit, full effective env, timestamps, temperatures/devfreq, `CmaFree`/`SwapPSS`/faults, independent physical image output, all production-hash receipts. A diagnostic success **may have zero FPS gain**.

**After H-E1c, choose exactly one branch:**
- High wall/low thread CPU in a **named actual wait** → capture identity of waited fence/driver/scheduler/page fault, resource owner, producer/consumer ordering; prove deferral legal before overlap. A wait that reappears later is **no optimization**.
- High wall/high thread CPU in DrawArrays/other handler → narrow the exact GLES validation/vertex format/shader/host packing call, then test one reversible CPU reduction.
- Handler cheap but total frame slow → profile the **guest execution and between-submit work**, not ReportCounter semantics.
- GPU timer confirms a heavy pass → validate GL FBO/shader/viewport/physical backing/pixel equivalence and memory before a single pass change, **never a blind logical 1080p→720p storage scale**.
- Memory goes critical with profiling or baseline → stop FPS experimentation and prioritize H-M2 **read-only** owner proof, without a speculative reclaim.

### 25.7 Acceptance, closed options and next development commits

**Closed / no-go without fresh evidence:** `MOMO_SUBMIT_FINISH=0` wash, `WOL_UNIFORM_CACHE=1` wash, `ZERO_RENDER_SCALE` black output, old v23 `UpRender` offsets on v24 16/9 aspect, forced `COTM_ASYNC_FRAME`, speculative pinned-program fixes, `WOL_TEX_SHADOW_MB` as a proven saving, and claiming a “10.1 ms GPU wait in the 43-ms scene” from unmatched E1b data.

**Correct acceptance contract:** net **≥9.8 ms** reduction toward **≤33.333 ms** in **same moving gameplay**; report mean, p50, p95, p99 and independently verified distinct physical frames, no shifted waits or repeated frames. Test title→game, HUD, dialogue, maps, inventory, interiors, combat, DLC where available, controller, real audio and save/cold reload. Preserve **65,536 KiB CmaFree** launch admission and existing runtime floor/cleanup, no added unsafe CMA use, no incorrect sum of overlapping memory domains, no production Unity/APK/saves/config changes. Clean watchdog return to Spruce/MainUI and protected hashes unchanged.

**Proposed commits (NOT performed here):** (1) `diag(horizon): repair first-op frame rollover and add V3 CPU/wall ledger`; (2) `evidence(horizon): matched scripted gameplay V3 OFF/ON/OFF with CMA series`; (3) `diag(horizon): attribute named counter wait or CPU-hot draw if V3 confirms`; (4) `diag(horizon): join seven-vertex draw to GL/FBO/window owner and validate GPU timer if relevant`; (5) `perf(horizon): one proven safe pixel-equivalent or sync critical-path optimization`.

**Verdict:** **H-E1c and H-P1 are closed (2026-10-30).** E1c: matched OFF/ON/OFF, +0.04 % overhead. P1: the 8.48 ms block is `glFinish`, and removing it moves the frame only 0.52 ms — a negative result, not a lever. The next measurable target is the `DrawArrays` CPU path (5.6–6.0 ms/frame) or the GPU work behind it. E1b and H-M0 remain valuable but **not** a 30 FPS or memory-safe async qualification. Leave installed Unity/Mono production entirely unchanged.

