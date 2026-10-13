# Graphics repair scope

- case_id: wol-indexed-alpha-repair
- primary_skill: reverse-engineering (R0, local GPU shader/data-flow analysis); implementation uses systematic-debugging
- lead_role: lead
- specialist_roles: [cre]
- auth.status: granted
- auth.basis: own_system
- auth.evidence_of_auth: owner explicitly requested kmsgrab screenshots and continued display repair
- in_scope.assets: local west-of-loathing-portmaster-tsps source, private shader captures, owner's TSPS 192.168.50.135 port directory
- in_scope.activities: static analysis, short principal-flow device tests, bounded diagnostics, exact test-process cleanup
- out_of_scope.activities: DRM circumvention, proprietary asset publication, unrelated device/service changes, multi-hour blind runs
- network_profile.mode: authorized_target_only
- constraints: preserve payload and launcher, SHA-256 runtime backups, independent physical KMS evidence, no fb0 substitutions
- ready_for_act: true

## Evidence / timeline
- Initial kmsgrab: before-kms.png shows the diagonal grayscale artifact, not a recognizable game screen.
- Existing hook treats DrawElementsBaseVertex as DrawArrays, ignores index pointer/baseVertex, and forces TRIANGLE_STRIP.
- Gfx165/166: native index-buffer decode confirms [0,1,2,0,2,3] and [0,1,2,2,3,0], with baseVertex 0/4/8/12. Correct indexed triangles remove the geometric artifacts, but physical screen is black.
- Gfx166 measured detail: (1) a transparent fullscreen sprite (vertex colour 0,0,0,0) wipes target 280 - sprite scan 586 -> 0 nonblack pixels in the same frame - because the pair path never applies the guest blend state (blend word 0x06050605 = SRC_ALPHA/ONE_MINUS_SRC_ALPHA, glIsEnabled(GL_BLEND)=0 at every sampled draw); (2) the sprite vertex shader derived v8.a from a_pos.w (float reinterpretation of the colour bytes, NaN for 255,255,255,255) instead of a_col.a.
- Gfx166 also: presented surface at frames 202+ carries ~893k non-black pixels (~97% white) - the title renders and presents content once boot progresses; black frames are the loading stage. Hypothesis until a capture matches known intro art.

## Work items
- [x] Physical capture and indexed-geometry root cause.
- [x] Opcode-aware indexed draw, native compiled regression tests, device trace.
- [x] Alpha output: v8.a = a_col.a * alpha-bank in wol_pair2_vertex_glsl (compiled test covers colour.a 0/fractional/scaled).
- [x] Guest colour contract: wol_apply_color_state applies blend enable (0x100 bit), separate factors/equations and the write mask for every substituted draw, sharing the standard path's state-cache slots. Definition lives outside all game-conditional blocks (build-167 first attempt failed exactly there: ANIMAL_WELL_SHADERS guard compiled it out).
- [x] build-167 compiled, unit-tested, deployed; runtime sha 4a99a1dd740b1b14739ea3178b1b582ff4ea09895980c94b0f09eaa4e80e3e09; previous binary backed up on device.
- [ ] Run 167 (240 s): verify via kmsgrab that the wipe is gone and target 280 keeps its content.

## Update 2026-10-13 evening (input + late-phase unblock)
- Input: `COTM_INPUT_DIAGNOSTIC=1` opens a unix socket (`HID_DIAGNOSTIC_SOCKET path=/tmp/cotm-input-*/buttons.sock`); 16-byte datagrams `{u64 buttons; u32 ms; u32 reserved}` enter the SAME Npad ring as physical input (logged `HID_DIAGNOSTIC_PRESS`/`HID_SAMPLE`). Verified with an autopilot: the control card is a GATE - without presses it held 10 min (gfx169), with presses the screen advanced within ~20-40 s (gfx171/172/173).
- Late-phase rendering: the game's later phases use texture ids from a session-wide counter (8394+). `wol_texture_by_id` rejected ids >= 4096, so the downsample views never resolved (6415 unresolved/run in gfx172) and the chain stayed black. Fix: drop the id cap (build-169, sha 9e1a6f1f...). After: unresolved = 0, and the post-card phases render - kmsgrab shows the game's own examine text "It's Mom's pie safe. It keeps all her pies safe." on the physical screen (gfx173, during-620/680).
- Remaining known gap (user report "some assets don't display"): draws whose shader pairs are not yet in the translation catalogue are skipped - 245760 skips in the gfx173 run (objects 0x10602259a8/0x1008cb2888 etc. in the gameplay phase). Scene/world art depends on those pairs; f191/f268 fragments are still TEST-DRAFT.
- [ ] Inspect physical KMS captures after correction; do not substitute frame counts for image correctness.
- [ ] Correct prior unsupported splash/loading claims in maintained docs and skills.

## Skip census (run gfx174, build-170) — which pairs make the missing assets
Draw-site per-pair skip counter (WOL_SKIP_TOP/WOL_SKIP_PAIR_NEW): 173797 + 38094 + 24653 + 1024 skipped draws over one 700 s run. Program-object inventory correlation (object -> code/control address -> captured SHA-256) reduces the first three pairs to ONE shader pair:
- vertex 1024 B code-sha256 f43463c57a81c5de... (control 94f306daf11a...) + fragment 512 B code-sha256 649ae12f51fe6689... (control 3ee2f2106c88...) - THE workhorse pair of the missing world/scene (about 87% of all skipped draws).
- second (small) pair: vertex d88c64a6ae67554a... (third d88c64a6 variant) + fragment f8e1b018f588f274... - that fragment is the one blob not yet captured (needs one WOL_DUMP=1 run in the gameplay phase).
envydis decode (gm107) of the top pair: fragment = tinted sprite with explicit perspective divide - ipa a[0x7c] (w), ipa a[0x90]/a[0x94] (uv), mufu rcp + fmul -> texture2D(tex0, uv/w), then rgb/a multiplied by the interpolated colour a[0x80..0x8c]; exit. Vertex = 9-10 attribute words (a[0x80..0xa4]) transformed through the c3 matrix family with c3 constant adds, varyings exported at a[0x70..0x94] matching the fragment's reads exactly. Same family as the already-translated f191/f268; blobs and disasm in the spike library (wol-shaders-private/untranslated, index.json).
