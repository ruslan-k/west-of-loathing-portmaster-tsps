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
- [ ] Inspect physical KMS captures after correction; do not substitute frame counts for image correctness.
- [ ] Correct prior unsupported splash/loading claims in maintained docs and skills.
