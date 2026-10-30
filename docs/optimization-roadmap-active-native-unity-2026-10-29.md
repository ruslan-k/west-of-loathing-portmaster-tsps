# West of Loathing — TSPS complete optimization audit (updated 2026-10-30)

> **Current reviewed HEAD:** `04384a73033d909778cda8ff9a1faf128b893c8f`, seven new commits since prior documentation release `45fdc930`. Complete repository-tree inventory (5,620 entries; 5,386 in evidence), build/launcher/Unity and Horizon surfaces, source patch and tests, CI latest actual failure, profiler source and device reports. **Current decision authority: [section 26](#26-complete-optimization-follow-up--head-04384a73-2026-10-30).** Section 25 remains the previous full-repo audit before the newly staged H-D1.
>
> **Installed playable game:** native **Unity 2017.4.19f1 / Mono ARM64**, audio owner-confirmed; its post-audio sustained FPS, memory, normal DLC entry, controls and cold save/load remain to be certified **independently**.
>
> **Separate development candidate:** Switch v327680 **Horizon/NVN→GLES**, matched heavy moving gameplay `~40.2–40.6 ms` per 60-frame-window **average** (~24.7 runtime presents/s), short of 30 FPS by `~7.08 ms/frame`. No accepted net 30 FPS gain.
>
> **Immediate order:** **B0 — restore full CI + source/overlay parity; B1 — find rebuilt-ELF `rtld.text.seg` size mismatch; H-S0 — process old sampler pp-stage logs offline; H-S1 — opcode/quiet-pick sampler CPU attribution**. The H-D1 profiler is source-staged in `evidence/` but **failed to reach gameplay**. No framebuffer/asset shrink, guest reclaim, sync bypass or extra GPU memory approved.

**Audit limits:** source and GitHub Actions inspected directly; c5–c8 XZ evidence and owner-specific segment files were not independently decompressed/replayed with the GitHub connector; no new device run, private data, build, runtime change or save change. Git history and historic measurements are preserved below. [Current Horizon status](horizon-roadmap25-device-status-2026-10-30.md), [c5–c8](../evidence/horizon-e1c-abc-2026-10-30/README.md), [failed H-D1 evidence](../evidence/horizon-hd1-2026-10-30/README.md).

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
| Historical Horizon section 15 | An older v23-era `UpRender` **pixel** override improved matched `tut_gulch` presents from ~24 to ~33–34. | Old guest/ELF; does **not** transfer to new v327680 metadata v24 or native Unity. |
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

Use a **single opt-in** per matched run at constant 16:9, e.g. **1152×648** (81% of panel pixels) *or* **1024×576** (64%). Do not mix both values into one causal test. Prefer a conservative first test, compare A/B/A as in section 4, and inspect on-device scale uniforms, canvas, pointer/UI hit testing, readable fonts, black bars, physical KMS 1280×720 and audio. This is **not** the failed Horizon `ZERO_RENDER_SCALE`: it changes the Unity window resolution under the host's documented display routing, not guest NVN storage semantics.

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


## 25. Full repo optimization re-audit — 2026-10-30

**Scope:** main `fd06778302e5803f7cfbc92a47bb575a432a3284`, 2 commits after previous docs update. This section supersedes earlier `25 and historical Horizon task order (`20). The detailed **installed Unity** N0–N14 procedures (sections 0–19) remain valid **only** for that distinct executable. Do not apply Horizon GPU/CMA timings to the installed Unity port.

### 25.1 Repository-wide state: architecture, builds, reproducibility and tests

| Area | Verified | What remains to be proved |
|---|---|---|
| Native Unity | `port/West of Loathing.sh` retains accepted SDL KMSDRM/ALSA/TRIMUI mapping, isolated `HOME`, optional bounded mode. `ua_host`, generic Mono and runtime manifest have hash/packaging tests. Owner-only APK/Unity player and saves excluded from git. [Native receipt](native-unity-port.md) | Owner-confirmed sound, real KMS base/DLC views **do not yet certify post-audio steady FPS, cold save/load, normal DLC entry, all physical buttons or endurance**. Previous 32.5–32.7 FPS and 711 MiB RSS/173 MiB swap are pre-audio short-run figures only. |
| Experimental Horizon | `build_horizon.sh` verifies source-manifest SHA, copies recovered GPL baseline, applies `runtime/wol-adapter.patch` then cross-builds. Source/evidence is reproducible only with exact external recovered source and owner image. Overlay ~930 kB and 116 unique paths. | Public CI runs `git apply --numstat` but **cannot validate complete application/compilation** to manifest-pinned recovered source. Need owner-side `git apply --check` and exact ELF SHA build receipts; do not distribute proprietary input. |
| Evidence and tools | Thousands of archived experiments, KMS shots, V3 frame-owner ledger, phase profiler, sampler subspan telemetry, memory analysis, >100 data-free tests. | Each FPS/CMA claim must be scoped to **same scene, ELF, default flags and physical screen**. 60-frame-window percentiles are **not individual-frame or scanout percentiles**. |
| Build/CI | 1 workflow, current latest [run 437](https://github.com/ruslan-k/west-of-loathing-portmaster-tsps/actions/runs/41024788603) **failed** after initial Unity/package and syntax checks. | Fix single failing test and run previously skipped ARM64 jobs. `tools/test_wol_op_v3_ledger.py` is not explicitly included in the current workflow. |

**Source status:** one cannot label a codepath safe solely because tests compile an isolated snippet or because a screenshot is bright. Production Unity still has a protected hash+save boundary; Horizon still lacks complete playability/audio/save/DLC endurance acceptance.

### 25.2 B0 P0: current CI failure, precise fix strategy

Latest run 437: **112/113 synthetic memory tests passed**, **one failed** at `tools/test_wol_memory_roadmap.py::test_published_overlay_still_carries_the_sparse_source_contract`. It asserted `len(touched)==len(set(touched))`, but the actual patch has **125 old-file headers for 116 distinct paths**. Five files recur: `native/nvn_async_frame.h` (4 sections), `native/nvn_replay.h` (3), `native/nvn_shaders.h` (3), `native/nvn_gl_worker.h` (2), `native/nvn_textures.h` (2). This is consistent with separate appended patches; **duplicate path headers alone are not a runtime failure**. The workflow's `git apply --numstat` passed; cross-compiler and ARM64 test stages were **skipped** after the failed assertion.

**First action (test/source-contract only, no game changes):** either consolidate sequential hunks by path against the pinned recovered baseline with exact semantic/diff review, **or** amend the obsolete uniqueness assertion to verify changed **file-set, newly added header provenance, ordered patch sections and context applicability**, not a one-header-per-file layout. Do not delete or weaken failure checks without a replacement invariant. Add explicit V3-ledger and future sampler-ledger tests to CI. Require a green public pipeline, and, with owner-controlled source, a manifest-verified `git apply --check` + isolated full Horizon build and resulting ELF manifest. No production executable/release promotion while source contract is red/unknown.

**Gate B0:** PASS only when all test steps run, complete, and the actual reconstructed overlay applies to its frozen source. This doc update does **not** repair CI itself.

### 25.3 Current matched gameplay performance: H-E1c and H-P1 closed

The [matched fresh-boot E1c report](../evidence/horizon-e1c-abc-2026-10-30/README.md) used ELF `f5c6f6f2f6c87c3c1c0308c62ef070a39d3c8b60c41b1071c03a9230fbed75d3`, correct scripted TRIMUI input, 240-second bounded runs, KMS at 180/240 seconds and 131 protected files unchanged.

| Arm | V3 | Median of **60-frame means** | P95 of those means | Replay median |
|---|---|---:|---:|---:|
| `c1-off` | OFF | **40.608 ms** | 41.855 | 24.683 |
| `c2-on` | ON | **40.412 ms** | 41.353 | 24.805 |
| `c3-off` | OFF | **40.184 ms** | 41.391 | 24.395 |

V3 overhead estimated **+0.016 ms (0.04%)**, below normal run-to-run drift; not a paired confidence interval and temperature/devfreq not recorded. This is **~24.6–24.9 runtime presents/s**, not physical distinct-frame FPS or a proven improvement over a different 42–43-ms ELF. The tool calculates P95 of **window averages**, not individual-frame P95.

Per-class V3 medians (c2-on, 2,772 completed frames): three **DrawArrays ~7.264 ms wall / ~6.047 ms thread CPU** and two **ReportCounter ~8.482 ms wall / 0.198 ms CPU**. H-P1 identified `ReportCounter` → `nvn_counter_timestamp` → **`glFinish`** twice/frame. One semantics-changing `COTM_COUNTER_CPU_TIME=1` diagnostic reduced the local counter span by **~8.47 ms**, but the whole-frame median only **40.412→39.894 ms** (~0.52 ms). No legal ~8-ms net gain: **H-P1 CLOSED NEGATIVE**; never ship CPU-wall substitution or infer that skipped GPU work vanished.

**Budget:** `40.412−33.333=7.079 ms/frame` (~17.5%). Even a hypothetical net removal of all **6.047 ms DrawArrays CPU** leaves **34.365 ms/frame (~29.1 FPS)**. Wall timers and overlapping GPU work are not additive recoverable milliseconds.

### 25.4 New c5–c8 sampler evidence — what it supports and what it DOES NOT

Published [latest c5–c8 receipt](../evidence/horizon-e1c-abc-2026-10-30/README.md#cpu-attribution-after-h-p1--where-the-drawarrays-6-ms-actually-is), all independent opt-in diagnostics on ELF `f5c6f6f2`:

| Measurement | Reported | Attribution boundary |
|---|---|---|
| `c5 COTM_REPLAY_PHASES` | `DrawArrays` **6.804 ms/frame**, three calls; indexed `DrawElementsBaseVertex` 4.470 ms / ~62.5 calls; Downsample 2.036 / four; copy 1.215 / one | Op-class wall intervals **in another run**; consistent shape with V3, not the partition of exact V3 thread CPU. |
| `c6 NVN_DRAW_SPLIT` | `a2c1` **7.764 ms/frame**, `submit` 1.225, `mid` 1.004 over ~60 draws/frame | **Includes other draw classes**, not exclusive to just three DrawArrays; wall, not thread CPU. |
| `c8 WOL_SAMPLE_SPLIT` | `sm1` **7.272 ms/frame across ~120 sampler calls**, ~61 µs/call. `sm3` 0.342; `sm2/sm4` ≤0.06 | `sm1` contains `nvn_render_sampler_prepare_mode`, copy trace and sampler storage require; **all sampler call sites**, wall-only. Its `pp1…pp5` stages are nested inside it. Do not add `sm1` to `a2c1` or name it a proven 7.27-ms CPU cost of the three DrawArrays. |
| `c7 COTM_TEXTURE_PARAMETER_CACHE=1` | Whole-frame median **40.292 vs 40.412 ms**, DrawArrays CPU **5.946 vs 6.047** | Small, unreplicated shift, within drift; **no accepted performance win** from `glTexParameteri` caching. c8 sampler profiling perturbs frame period by roughly +0.5 ms and must not be used for FPS acceptance. |

**Source verification:** `nvn_render_sampler_prepare_mode` resolves the descriptor and texture/sampler, then invokes `zero_texture_refresh`, `nvn_normal_require_materialized`, `nvn_rt_storage_require`, `nvn_rt_storage_sample`, and conditional `nvn_mfc_require` for real samples. `nvn_render_sampler` also performs sampler storage require, materialization, active texture/binds/parameters and other coherence work. The existing `WOL_SAMPLE_SPLIT` report has **pp1 descriptor**, **pp2 checks**, **pp3 refresh**, **pp4 materialization/RT-storage/MFC**, **pp5 filtering**; `sm1` wraps more than these. **First parse existing c8 XZ pp1–pp5 lines offline before another device rebuild**. Their exact pp per-zone distributions were not re-computed in this review.

**Important quiet-path fact:** in the `wol_quiet()` first-bound-texture choice (overlay around lines 5838–5860), each nonzero candidate calls **`nvn_render_sampler(candidate,0,0,0,...)`** and picks the first live nonzero-size texture. Despite `real_sample=0` it still executes `zero_texture_refresh`, materialization, storage requires and GL sampler-related work. This looks expensive for merely inspecting size/liveness, **but those operations may be essential for later draws or fail-closed lifetime handling**. A metadata-only bypass without state/alias/dirty/next-use proof is unsafe. Also the current profiler **does not separate candidate-only calls from actually sampled calls**; it cannot justify a fast-path change yet.

### 25.5 H-S1 P0: ONE NEXT REVERSIBLE EXPERIMENT — sampler-owner CPU and usage

**Goal:** determine what fraction of real `DrawArrays` CPU is spent on *unsampled quiet-pick candidates* versus *actual sampled texture preparation*, and which of `pp1–pp5` owns the cost. **Diagnostic success may yield 0 FPS**. This supersedes the broad H-D1 DrawArrays-stage measurement proposed before c5–c8.

**Default-OFF proposal (`WOL_SAMPLER_OWNER=1`, NOT implemented):**
1. Carry frame/list/thread ID, **enclosing replay opcode**, draw ordinal, caller category (quiet-pick/real sampled/other), `real_sample=0/1`, texture handle+object/generation, live/selected status and candidate count through **existing sampler calls**. No GL API query or new resource. Explicitly bound log volume and avoid runtime data snapshots.
2. Attribute **nonoverlapping CLOCK_MONOTONIC and CLOCK_THREAD_CPUTIME_ID** spans for `pp1–pp5`, extra `sm1` work and call-site remainder, with counts/sums/max by opcode+caller+real_sample. **Nested samples are not independent costs**. Compare on the **same frame+thread** to `WOL_OP_V3` DrawArrays ~6.05-ms CPU, with <=5% unexplained residual; record other draw/copy classes separately. No unqualified attribution from c5+c6+c8 across runs.
3. Synthetic tests: empty/one/multiple candidates, invalid/aliased/reused handles, frame rollover, different threads, terminal flush, nested-zone arithmetic, class boundaries, CPU<=wall (with rounding), zero-op windows, and passive side-effect counts. Do **not** skip existing refresh, materialization, stop checks or texture bind to gather evidence.
4. Fresh-boot **OFF→ON→OFF** in the same 240-second scripted scene, 180/240-second real KMS captures and visually identical movement, all probe/ELF/environment hashes, CPU/GPU clocks+temperatures if supported, timestamped CmaFree/SwapPss/fault/swap IO, 131 production hashes and MainUI cleanup. All prior performance flags (counter CPU-time, uniform/texparam cache, shadow eviction, async, scaled target) stay default OFF. **≤5% overhead**, preferably <=1%, no black/stale picture and zero new memory allocation.
5. **Decision:** if costly unsampled candidates own CPU time, consider one guarded `H-S2` metadata-only selection **only after** proving unchanged chosen handle, lifetime/fail-closed checks, required refresh/materialization state and GPU producer/consumer alias/fence correctness. If actual sampled texture refresh owns the cost, target only its measured dirty/upload/storage owner. If neither dominates, move to GL draw submission/GPU timer or the indexed draw path. No sampler shortcut before these conditional proofs.

### 25.6 Memory/graphics/guest safety

Matched H-M1 shows **CmaFree ~0.3–1.9 MiB during gameplay** from ~128–130 MiB on clean preflight, **SwapPss ~922–930 MiB** / VmSwap ~923–931. These are severe **headroom warnings**, not owner proof for a specific GPU texture. Keep **65,536 KiB launch CMA admission**, the runtime memory floor, watchdog, CPU/GPU governors and swap policy intact. No added async frame, program pin, extra full-sized FBO, blind guest-page discard or shader/texture compression change without measured marginal CMA/live allocation/alias/fence proof.

**H-M2, read-only when needed:** correlate per-process `smaps_rollup` PSS/SwapPss/major faults with host CMA and Mali/DMA-buf state and an exact guest pool+offset+extent, target generation, GL attachment, logical/physical dimensions, snapshot lifetime and GPU fence. Do **not** add RSS+GPU+CMA+SwapPss as independent allocations. `WOL_TEX_SHADOW_MB=192` recorded zero evictions; its byte count misses non-eviction free/replace paths, so not a proven RAM-saving mechanism.

**H-G1 conditional:** verify exact program/FBO/viewport/texture identity for the three seven-vertex draws and existing **nonblocking** `WOL_GPU_TIMELINE` with supported disjoint validation. Third draw logical 1920×1080 is associated with the window family, but backing was reported as `actual=1280×720`; flags `0x9` alone do not prove 2.25× actual pixel cost. v24 `UpRender` offsets are **16/9 aspect** and older `ZERO_RENDER_SCALE` produced **black KMS**. Async `NVN_PROGRAM_INVALID detail=0` survived speculative pinning and cannot be re-enabled without identity + memory qualification.

### 25.7 Dependency board: what to do in what order

| ID | Rank/status | Actual deliverable |
|---|---|---|
| **B0 CI** | **P0 BLOCKER — OPEN** | Repair exact old test/overlay-contract mismatch, verify public job green **including ARM64 stages**, add V3/sampler tests, pinned-source apply/build privately. |
| **N0/N1 Unity** | **P0 independent** | Isolated accepted installed/audio-enabled baseline, real controls, cold save, normal DLC entry and endurance; N2–N14 follow only their own evidence. |
| H-E1c / H-P1 | **DONE / CLOSED NEGATIVE** | Matched ~40.4 ms, low V3 overhead; counter `glFinish` not a recoverable 8 ms. |
| H-D1 / c5–c8 | **DIAGNOSTIC SCREEN DONE, attribution incomplete** | Sampler `a2c1/sm1` is a likely zone; not opcode-exclusive CPU. |
| **H-S1** | **P0 NEXT DEVICE EXPERIMENT (after B0)** | Replay-opcode/quiet-vs-real sampler and exclusive CPU pp-zone attribution, matched V3 and physical image. |
| H-S2 | P1 conditional | One proven unsampled quiet-pick metadata fast path, strict alias/resource side effects, default OFF, A/B/A/B/A. |
| H-M2 | P0 passive / P1 dedicated | Guest/GPU/CMA owner and page/residency; no unsafe reclaim or extra buffers. |
| H-G1 / H-R1 | P1/P2 conditional | True pass/driver cost, source target identity, pixel equivalent renderer optimization only if justified. |
| H-A0/A1 | **BLOCKED** | Async invalid program identity and no proven CMA budget or completed snapshot lifecycle. |
| H-ACCEPT | **NOT MET** | Individual physical distinct-frame p50/P95/P99, real ≥30 FPS, no black/duplicate frames, scene/audio/input/save/DLC/thermal/cleanup. |

**Closed no-go:** `MOMO_SUBMIT_FINISH=0` wash, `COTM_COUNTER_CPU_TIME` guest semantic change, `WOL_UNIFORM_CACHE=1` wash, `COTM_TEXTURE_PARAMETER_CACHE=1` not accepted, `ZERO_RENDER_SCALE` black, blind 1080p/metadata v24 resize, speculative async/pins, unproven CPU shadow eviction, unknown-liveness guest page reclaim.

### 25.8 Acceptance mathematics and next commits (NOT yet implemented)

**30 FPS debt:** `40.412−33.333=7.079 ms/frame`. Recover **end-to-end critical-path** time, not local/nested wall timer or a relocated fence. Existing `NVN_PROFILE` P95 is **P95 of 60-frame averages**, not P95 of single frame intervals. Final gate: individual frame-to-frame physical *distinct* scanout periods, p50/P95/P99 and >50ms hitch count, moving gameplay with unchanged scenery/map/dialogue/inventory, real input and audio, ordinary DLC, cold save/load and endurance. No false success from counters without a moving KMS scene. Confirm active boot/PID/ELF, default flags, memory/CMA/thermals, production byte hashes and clean Spruce MainUI recovery.

**Proposed small commits in dependency order:**
1. `test(horizon): restore changed-file patch contract and run V3-ledger tests in Actions` (B0, first).
2. `evidence(horizon): extract existing c8 pp1–pp5 sampler zones by scene and owner` (offline analysis).
3. `diag(horizon): default-off opcode/quiet-sample sampler CPU ledger` (H-S1).
4. `evidence(horizon): matched H-S1 OFF/ON/OFF with physical frames, CMA and swap`.
5. `perf(horizon): one owner-proved sampler fast path OR other named CPU/GPU cost` (conditional).
6. `test(native): isolated post-audio Unity scene and save/endurance receipts` (separate track).

**Conclusion:** restoring sound CI and identifying the *specific sampler-prepare CPU owner* is the current critical path to an honest optimization. Neither the published ~7.27-ms mixed sampler wall sum nor the 6.05-ms DrawArrays CPU can be called a 7-ms removable cost without overlap, resource lifetime and physical-frame proof.

## 26. Complete optimization follow-up — HEAD `04384a73`, 2026-10-30

**Scope and supersession:** §26 supersedes §25's *future task order*, but does not erase its source/evidence explanations. Source audit included the complete Git tree inventory, seven commits since `45fdc930`, GitHub Actions run logs for latest `04384a73`, entrypoints, scripts, test contracts, main GPL overlay, owner-only Unity packaging, H-E1c/c5–c8 and H-D1 reports. **No new live device measurements** were taken. The 5,386 evidence entries were inventoried but not each manually read; the latest XZ c8 log was not independently decoded. Historical pre-audio Unity numbers are not Horizon numbers.

### 26.1 Architectural inventory and evidence boundaries

| Subsystem | Verified implementation | What is NOT established |
|---|---|---|
| **Installed Unity/Mono PortMaster game** | `port/West of Loathing.sh` enforces single session via `flock`, isolates HOME, selects SDL KMSDRM and ALSA, maps TRIMUI controls; `port/westofloathing/` distributes `ua_host` and generic ARM64 Mono, owner-only packed APK/player/assets/saves excluded. Legacy Java-FMOD path has owner-heard output. [Installed-port evidence](native-unity-port.md) | No post-audio mixed-gameplay steady FPS/p95, normal DLC quest-entry, independent physical-button audit, complete cold save/reload, long endurance, zero-swap proof. |
| **Unity build/conversion** | Pinned exact Unity 2017.4.19f1 ARM64 donor, Mono dependencies and `runtime/unity/legacy-fmod-output.patch`; ASTC/highp conversion retains texture sizes/mips, compressed assets packaged into one owner-local APK. | Blind ASTC, shader, managed GC or AssetBundle rework is not justified before a profiled native session. |
| **Experimental Horizon** | `build_horizon.sh` verifies a **435-file** source SHA manifest, copies external recovered GPL source, normalizes names and applies cumulative `runtime/wol-adapter.patch` (~930 kB) before ARM64 build. No Switch images/segments or external source committed. [Runtime README](../runtime/README.md). | Public syntax check is NOT frozen-source `git apply --check` + byte parity or validated ELF gameplay. |
| **Profilers** | Working ELF `f5c6f6f2…` has corrected frame-ownership V3 ledger; c5–c8 have wall-span sampler/draw diagnostics; H-P1 localized the counter wait to `glFinish`. | c5/c6/c8 different runs/op classes; no same-frame **thread CPU** owner for sampler; p95 of 60-frame means is not individual-frame or scanout p95. |
| **H-D1** | [New candidate](../evidence/horizon-hd1-2026-10-30/README.md): `wol_da_split.h`, three owner-specific source diffs, 11-stage CPU/wall accumulator and one synthetic host test. | **NOT in current published GPL overlay; no CPU stage data.** Two rebuilt ELFs exit on `rtld.text.seg` before gameplay. The test finds a header at owner-local paths or uses `SkipTest` on normal checkout. |
| **CI and safety** | Latest GitHub Actions [41044438709](https://github.com/ruslan-k/west-of-loathing-portmaster-tsps/actions/runs/41044438709) **FAILED**; Unity package/bounded-run checks and `git apply --numstat` succeeded. | Memory/source contract test fails; cross compiler/QEMU and subsequent ARM64 stages **skipped**. No green end-to-end build check. |

### 26.2 B0 — fix broken CI without weakening GPL overlay guarantees (P0 FIRST)

The **latest run**, not older linked workflow `41024788603`, is [41044438709](https://github.com/ruslan-k/west-of-loathing-portmaster-tsps/actions/runs/41044438709) on `04384a73`. Failure is *exactly* `test_wol_memory_roadmap.ReportContracts.test_published_overlay_still_carries_the_sparse_source_contract`:

`AssertionError: 125 != 116 : overlay must name each file once`

The test counts `--- a/` records: 125 records, 116 unique old-file paths. Separate `+++ b/` count (137 / 128) includes additions and is **not** the failing assertion. Repeated file patch sections concern `nvn_async_frame.h`, `nvn_gl_worker.h`, `nvn_replay.h`, `nvn_shaders.h`, `nvn_textures.h`. Multiple sequential hunks **do not alone mean the final patch is wrong**; however the current test and overlay violate the documented one-section-per-file contract.

**One safe repair:** retain explicit touched-file set / sparse-contract/added-header checks and patch apply+byte-parity validation. Either canonicalize the overlay **against the exact manifest-pinned normalized original** to one contiguous file section each, or allow repeated sections only where an ordered apply + **final content SHA parity** against the frozen expected tree succeeds. Do **not** simply remove the uniqueness test and call CI green. Add synthetic tests for repeats, changed file omitted, conflicting hunks, path escape and duplicate introduced header. Public CI may use data-free synthetic fixtures; **the actual 435-file recovered source belongs to owner-side verification**, never GitHub uploads.

Add non-skipped V3/H-D1 fixtures to explicit CI command lines: `tools/test_wol_da_split.py` currently returns `SkipTest` if the test header is not in external local spike trees. A passing generic suite must not be misrepresented as H-D1 verification. Preserve the existing native Unity tests and full ARM64 compiler/QEMU stages.

**Exit:** latest complete workflow green through ARM64 steps, source overlay patch parsed, safety contract meaningful and no expected test silently skipped; owner-side exact source manifest → neutralization → apply-check → byte-parity → ARM64 build recorded.

### 26.3 B1 — fix rebuilt ELF *identity*, not a performance problem (P0)

H-D1 was attempted twice with a **rebuilt ELF**, both candidates failed very early with:

`segment size mismatch rtld.text.seg`

H-D1 candidate SHA256 `5786a3629f0210318d42e24a38f0703971e2019d0e7406cb87850a6e9ecf3c11` exits ~0.256 s after START. Another canonical overlay build `9a64faed…` also fails. In the same probe directory, known-good `f5c6f6f2…` passed segment mapping and reached video readback. A trial that tried `T2_IMAGE_FILE_MAP=0` via `E1C_EXTRA_ENV` still reported the mismatch; therefore neither effective child env nor root cause is proven.

**First read-only diagnostic, no candidate optimization:**
1. For both old and rebuilt ELFs, verify source hash, immutable owner image/probe path, manifest, ELF build args and **effective child environment**. Confirm whether the flag reaches the loader; never rely on launcher-shell intentions.
2. Add bounded failure logging at existing guard in `native/t2_image_file_map.h` for requested segment name, exact opened path/device/inode, `fstat(fd).st_size`, expected `s->file_size` and mapping mode. Do not dump segment data.
3. Rebuild source **without H-D1** as a control (same toolchain, baseline and deployment). Compare exact stdout and file identity to distinguish generic rebuilt-image contract from H-D1 instrumentation.
4. Correct only a proven mismatch in metadata/image selection/flag routing and **keep fail-closed** size checks; no padding guest segment, bypassing guard or switching game image to fake success.
5. Require rebuilt **default-OFF** executable to reach verified moving gameplay and return to MainUI safely before any new performance measurement.

**Exit B1:** reproducible effective ELF/image identity, no mapping stop, normal CMA admission, KMS moving scene and original protected Unity hashes intact. **H-D1 has produced no performance samples yet**, despite having source and host test artifacts.

### 26.4 Horizon accepted baseline and false leads

Working v327680 source/ELF `f5c6f6f2…` fresh-boot matched OFF/ON/OFF gives median **60-frame-average time** `40.608 / 40.412 / 40.184 ms` (approximately 24.6–24.9 runtime presents/s), V3 overhead ~**0.04%**. On same heavy scene, three `DrawArrays` calls consume **7.264 ms wall / 6.047 ms thread CPU**; two `ReportCounter` **8.482 ms wall / 0.198 ms CPU**. Times are **class-local**, not guaranteed additive net gains.

H-P1 closed negative: native `ReportCounter` calls `glFinish`; temporary `COTM_COUNTER_CPU_TIME=1` cuts class wall ~**8.47 ms**, but full-frame median only **40.412→39.894 ms** (~0.52ms) in one guest-semantics-changing arm. Do not ship the CPU-timestamp substitute or remove fences to chase the apparent ~8ms.

**c5–c8 reports** (same original ELF, but distinct diagnostics; XZ not independently decoded here):

| Evidence | Reported result | Correct interpretation |
|---|---|---|
| c5 `COTM_REPLAY_PHASES` | DrawArrays **6.804 ms/3 calls**, indexed draws **4.470 ms/~62.5 calls**, Downsample **2.036 ms/4**, Copy **1.215 ms/1** | All are own-run wall-class totals; not stage CPU under same V3 frame. |
| c6 `NVN_DRAW_SPLIT` | `a2c1 7.764 ms/frame` across ~60 draws; submit 1.225; mid 1.004 | Mixes different draw classes. Cannot call entire a2c1 cost of three DrawArrays. |
| c8 `WOL_SAMPLE_SPLIT` | `sm1 7.272 ms/frame` across ~120 sampler calls (~61µs/call), sm3 0.342 | Mixed opcode wall spans, with nested `pp1–pp5` zones; cannot add to c6 or claim 7.272ms *thread CPU*. |
| c7 `COTM_TEXTURE_PARAMETER_CACHE=1` | 40.292 vs 40.412 ms frame; DrawArrays CPU 5.946 vs 6.047 | Too small, not replicated and within drift; not a credible optimization. |

The source proves a **question**, not a safe fast path: `wol_quiet()` scans candidate handles and calls `nvn_render_sampler(candidate,0,0,0,...)`, which still executes `zero_texture_refresh`, render-target materialization and storage checks even though the selector appears to want only liveness/size. Those operations can carry later coherence/lifetime and GPU dependencies; metadata-only bypass **requires** side-effect proof.

**30 FPS gap:** representative `40.412−33.333=7.079 ms` on the *total frame critical path*. Even a theoretical net save of all 6.047ms thread CPU leaves 34.365ms (~29.1fps). Subtracting independently measured local wall waits, mixed sampler spans or time from another ELF is prohibited.

### 26.5 H-S0 then H-S1: ONE next narrow CPU owner test after B0/B1

**H-S0, offline first (no device):** check the already-committed `evidence/horizon-e1c-abc-2026-10-30/c8-samsplit.log.xz` in a local owner checkout, extract `WOL_SAMPLE_SPLIT pp1..pp5` counts, unit math and median/p95 *per completed 60-frame window*, plus sm1 remainder and bounds. Hash the source XZ and publish only the small data-free summary. These are nested spans, not independent per-frame costs; c5/c6 are different runs.

**H-S1 proposed default-OFF `WOL_SAMPLER_OWNER=1` (NOT implemented):** augment sampler preparation **without altering GL/texture logic** with enclosing replay opcode, frame/list/worker, exact draw ordinal, quiet candidate versus real sample versus other caller, `real_sample=0/1`, candidate selected status, texture generation/lifetime and bounded **wall + CLOCK_THREAD_CPUTIME_ID** exclusive pp1..pp5/remaining-sm1 spans. Reconcile **same frame/thread/class** CPU to V3 DrawArrays ~6.047ms within ±5%, recording residual and nested zone arithmetic rather than adding c5+c8. Synthetic tests must cover missing/reused handles, incorrect candidate order, zero/multiple candidates, stale resources, cross-frame and multi-thread tags, terminal flush, and resource-state **non-mutation**. No additional GL readback, memcpy pixels, async frame or CMA-consuming snapshot.

**Device acceptance:** H-S1 only after rebuilt ELF qualifies B1. Run fresh boot **OFF→ON→OFF**, same 240-second proven scripted controller route, KMS scene + temporal movement at 180/240s, exact ELF/boot/PID/full flags, thermals/devfreq if possible, per-process PSS/SwapPss/faults and host CMA, clean watchdog/MainUI and 131 protected production hashes. Overhead ≤5% (prefer ≤1%), no black/stale image. Do not enable `COTM_COUNTER_CPU_TIME`, §WOL_UNIFORM_CACHE`, texture-param cache, async, shadow evictions or scaled targets in same experiment.

**If** costly *unused quiet-pick* candidates dominate real thread CPU, test **one** separate H-S2 guarded metadata-select optimization **only after** documenting unchanged chosen texture/generation, next-use GL state, all refresh/materialization/RT-storage/MFC/fail-closed side effects and pixel output. If real-sample preparation dominates, optimize only the measured dirty/upload/storage owner. If driver submission dominates, prove GPU cost via existing nonblocking `WOL_GPU_TIMELINE` with disjoint checks; if none, reject the sampler hypothesis.

**H-D1 status:** owner staging exists at [H-D1 evidence](../evidence/horizon-hd1-2026-10-30/README.md), but its builds crashed before gameplay; the three patches refer to owner-local paths, the header is not in `runtime/wol-adapter.patch` and normal CI lacks the fixture. Once B1 passes, H-D1 can be integrated as a **secondary, opcode-exclusive accounting control**, not accepted evidence of a bottleneck today. Do not repeat broad H-D1 device runs until its build identity is fixed.

### 26.6 Memory and GPU: blockers, not speculative 30 FPS shortcuts

H-E1c had initial `CmaFree` ~128–130 MiB but during gameplay **0.3–1.9 MiB**, with process **SwapPss ~922–930 MiB** / `VmSwap ~923–931 MiB`. Earlier H-M0 66/95 samples were below the 65,536 KiB *admission* threshold, and pagemap evidence measured ~582 MiB unique physical pages at 60s in a **different run**. These numbers describe different domains and cannot be added or assigned to any one texture. High swap use and near-zero CMA may block extra GPU images regardless of a CPU optimization.

**H-M2 read-only** after H-S1 or immediately if instability: pair monotonic phase/PID with `smaps_rollup`, actual PSS/SwapPss, major faults, swap-in/out, host CMA and Mali/DRM/dma-buf with exact NVN pool+offset+extent, GL texture/FBO generation, actual versus logical allocated dimensions and last-use fence. Retain **65,536 KiB CMA preflight**, memory floor, watchdog and normal CPU/GPU/swap policies. No speculative guest-memory decommit, unbounded CPU mirrors, extra async frame, shader pins or GPU second buffer until owner/lifetime/alias proof.

Two 1280×720 draw targets and one *logical* 1920×1080 window-family target were observed; actual backing was reported 1280×720, so flags `0x9` do not demonstrate 2.25× fragment work. v24 UpRender's 16/9 pair is **aspect**, not width/height; `ZERO_RENDER_SCALE` produced black output. `WOL_GPU_TIMELINE` must be nonblocking and valid with `EXT_disjoint_timer_query` plus actual FBO/program identity before changing any pass.

**Closed/no-go:** removed `glFinish` or CPU counter timestamps as a shipping fix; `MOMO_SUBMIT_FINISH` and uniform-cache wash, texture-param cache near-noise, `WOL_TEX_SHADOW_MB=192` zero evictions with incomplete byte counter, pixel resolution guesses, speculative GPU-work discards, async program pins after `NVN_PROGRAM_INVALID` persisted, and blind game memory reclaim.

### 26.7 Actual installed Unity track (N0/N1 is independent P0)

Installed `ua_host`/Mono uses the exact 2017.4.19f1 donor, ASTC/highp and owner-approved packed assets with audible FMOD→SDL/ALSA playback; [documented real-device verification](native-unity-port.md). Historic *pre-audio* DLC samples ~**32.5–32.7fps**, RSS up to **710.71 MiB**, swap **173.12 MiB**, but these are not a post-audio proof. Do **not** transplant Horizon ~24.7 FPS, CMA ~0 or 900MiB SwapPss to the installed build.

**N0/N1:** copy accepted installation and protected saves/config into an **isolated test copy**; compare all owner hashes; run title, real movement, menus, indoor/outdoor, inventory/dialogue, normal DLC entitlement/entry, audio through playback, physical controller, cold save→exit→load and ~30-minute bounded endurance with p50/p95/p99 *individual* frame intervals + physical distinct scanout, PSS/SwapPss/faults/CMA, CPU/GPU utilization and thermal/devfreq. Then choose a single Unity optimization only after a measured hot spot (managed allocations/GC/bridge, shader/texture, asset cache), not by trimming assets or changing owner saves on speculation.

### 26.8 Priority board, acceptance and proposed commits

| Rank | Step | Status now | Exit criterion |
|---|---|---|---|
| **P0 B0** | Repair cumulative patch contract + full CI | **RED**, latest run 41044438709 | Meaningful non-skipped tests, ARM64 stages green, owner frozen-source parity. |
| **P0 B1** | Rebuilt ELF segment identity | **BLOCKED**, two `rtld.text.seg` failures | Same image, default-OFF rebuilt ELF reaches moving gameplay and recovers menu. |
| P0 H-S0 | Offline pp1..pp5 c8 breakdown | **OPEN** | Per-zone bounded count/time report, unchanged raw XZ hashes and nested units. |
| **P0 N0/N1** | Installed Unity post-audio certification | **OPEN, separate** | Proper input/audio/save/DLC/endurance and physical frame pacing. |
| H-E1c / H-P1 | Matched V3 and glFinish negative | **DONE / CLOSED** | Reopen only with fresh causal evidence. |
| H-D1 | Stage ledger source/test | **STAGED, DEVICE FAIL** | B1 fixed, portable fixture, opcode CPU reconciliation after running real scene. |
| P0-after-B1 H-S1 | Sampler owner CPU by opcode/quiet vs real | **PROPOSED, NOT CODED** | ±5% V3 reconciliation, ≤5% overhead, matched images and CMA. |
| P1 H-S2 / H-CPU1 | One proven safe fast path | **CONDITIONAL** | A/B/A/B/A, unchanged state and physical images, measurable net frame saving. |
| P0-safety H-M2 | Exact memory/GPU allocation owner | **PENDING** | No cache/page release without alias/fence/liveness proof. |
| H-G1 / H-R1 | Real GPU pass optimize | **CONDITIONAL** | Correct FBO/input/output and nonblocking GPU time; 0 visual corruption. |
| H-A0/A1 | Async frame/program | **BLOCKED** | Fix invalid program identity + have CMA margin & valid resource lifecycle. |
| H-ACCEPT | 30 FPS | **NOT MET** | ≥30 distinct physical FPS and individual-frame p95 ≤33.333ms in representative moving gameplay, full game/audio/save/DLC/thermals acceptable. |

**Measurement rules:** §NVN_PROFILE` 60-frame-window p95 is not p95 of individual frames; instrument both, plus physical distinct frames. Compare same scripted scene, source/ELF/env/boot, clocks, thermals, memory and owner save hashes, using OFF→ON→OFF fresh boots. A removed local 8ms wait that migrates elsewhere is **0 accepted gain**. Stop/revert on black/stale output, stop-code change, resource leak, lower admission gate, invalid game state, save modification or cleanup failure.

**Proposed commits, NOT executed by this documentation update:**
1. `test(horizon): safely reconcile repeated overlay file sections and preserve manifest/sparse contracts` (**B0**).
2. `diag(horizon): log effective rtld segment identity without bypassing fail-closed check` (**B1**).
3. `evidence(horizon): summarize existing c8 pp sampler spans with hashes` (**H-S0 offline**).
4. `test(horizon): make H-D1 CPU-stage header fixture portable and non-skippable` (only if that diagnostic is reused).
5. `diag(horizon): default-off opcode/quiet sampler CPU attribution` (**H-S1**, after B1).
6. `evidence(horizon): fresh-boot H-S1 OFF/ON/OFF, KMS/CMA/SwapPss/thermal receipts`.
7. `perf(horizon): one owner-proved high-CPU path with safe resource semantics` (only if H-S1 causal).
8. `evidence(native): post-audio Unity physical input, cold save, normal DLC and endurance profile` (independent N0/N1).

**Bottom line:** the repository is **not yet in an optimization-ready rebuilt-Horizon state**. It is in a build/test correctness phase. Improve CI and source/ELF identity first, measure same-opcode sampler CPU second, and select a single reversible hot-path change third. Do not claim 30 FPS or a safe memory fix from old wall sums, nested counters, black scaled frames or a staged profiler that never reached game.

