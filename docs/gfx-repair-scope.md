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

## The world pair is translated and live (runs 175-176, builds 171-172)
- chat.txt review point 1 done twice over: the pair (v f43463c5 x f 649ae12f) added to wol_cat_bindings (WOL_TOP_DRAFT-gated, default on) AND the latent crash behind its first run fixed: wol_cat_program_find(...,1) returns NULL once the 128-entry table fills (every boot fills it), and the capture path wrote cp->cat[] without a guard - any catalogue match created after program ~128 faulted (CPU_FAULT, gfx175). Fix: NULL guard + table 128->1024 + linked cache 4->16 (the review's ask).
- After the fix (gfx176, 620 s, build-172 sha 2c413761...): WOL_CAT_LINK ok=1 top-v-draft/top-f-draft; 232646 draws rendered through the new pair (was ~237k skipped); WOL_SKIP_TOP prints stopped entirely (skips collapsed below the 8192 threshold); no stops. kmsgrab: the scene renders - a room with white wall, dark floor/hearth with diagonal shapes - and the game's own dialogue matches it: "This hearth really puts the 'hearth' in 'hearth and home.'".
- Measured pair layout: stride 24 (pos 3f@0 / colour RGBA8@12 / uv 2f@16 - the draft's assumption held), meshes up to 747 vertices, into the 1920x1080 scene target, real atlases sampled (512x128..1024x512). kmsgrab series gfx176/during-140..615.
- Still open: f8e1b018 blob capture (the review's lighter-flag suggestion), WOL_TOP_GEOM=1 pure-geometry A/B variant, f191/f268 real translations, then memory/affinity (VmSwap ~696 MiB, Cpus_allowed_list: 0).

## Light shader capture + the second pair's blob (gfx177, build-173)
- WOL_SHADER_DUMP=1 (new): admits ONLY the once-per-stage wol-shader-* dumps; frame dumps and the receipt journal stay off (verified: 139 code + 139 control files, no nvn-frame-*/nvn-video-* from that run). The review's capture/load separation is in.
- The missing blob f8e1b018f588f274... is captured (nvn-wol-shader-code-1791908615-138.bin, 768 B) - the untranslated-shader library is now 125/125 complete (code+control).
- Its disasm (envydis gm107): textured sprite with perspective divide + RECT GUARDS + conditional kill - ipa a[0x7c]=w, rcp, uv=(a[0x90],a[0x94])/w, texs, then fsetp chains against c3[0x10..0x1c] and c1[0x0] with `$p0 kil`, colour from a[0x80..0x8c] plus c3 constant offsets. Same family as f191/f268 (the f268 decode predicted exactly this guard shape).
- WOL_TOP_GEOM=1 (new): real world vertex + solid-colour fragment for a pure geometry A/B (TEST-ONLY).

## Second review (2026-10-13 night) executed - the attribute-binding root cause
The review's item 3 (attribute locations) was the root cause of the menu's green-to-red mesa gradient: `wol_cat_link` bound `a_col@1`/`a_uv@2` only for `v==0||v==1`, leaving the NEW pairs (top=8, top2=10) and the draft entries on `a_extra@1` while the draw path feeds colour at 1 and uv at 2 - the v266 pair's colour/uv went through garbage. After binding a_col/a_uv for every sprite-layout program (build 178, run gfx187): the menu background renders MONOCHROME (gray mesas, cacti silhouettes) exactly in the game's style. Also in 178: f8e1b018's guard/colour constants moved to the fragment bank `c3f` (fed from `fwords`; the link now reports c3f=97), and WOL_F191_UV now really applies to the f191 entry (the old branch sat under `if(!bf->diag)` and never reached the diag draft) with a new `grad` mode (uv-gradient probe: run gfx188 shows the gradient spreading across the f191 quads - v9 is the right uv source). A real f191 translation candidate (tex + c3f offsets + v10 rect guard in alpha, WOL_F191_REAL=1) links and draws but the fragment-bank PICK still lands on garbage slots (measured [1,1,1,1] and +-inf) - build 179 prefers slots >= 0x30 bytes but the inf-filled 64-byte slot still passes; THE NEXT TASK is parsing the control blob's CBUF descriptors to bind the fragment's real bank. The Switch menu reference (user-provided, switchplayer.net 1280x720): monochrome, NO WANTED poster, NO barrels - hanging sign WEST OF LOATHING, NEW GAME (+A prompt), OPTIONS; fence with two rails, clouds, tumbleweed; d-pad arrow cluster UPPER-RIGHT; control box bottom-right with L/R/ZL/ZR icons. Our current frame matches the desert; the sign area renders a black object with green artefacts (f191 constants still wrong), the arrow cluster sits low-centre instead of upper-right.

## Third review pass (2026-10-13 night): measured facts replace the descriptor hunt
- **c3f bank = stage-1 slot 0** (measured, not a control-descriptor hunt): every stage has exactly ONE non-empty uniform slot (slot 0) and its SIZE matches each shader's need - f191 = 32 B (8 floats = c3[0x0..0x1c]), f268 = 64 B, composite = 16 B. The previous "largest >= 0x30" heuristic DISCARDED the correct 32-byte slot. New rule: slot 0, validated (address, size, NaN, rect ordering) and reported as WOL_PAIR_BANK_OK/INVALID.
- **The +-inf values are a sentinel, not garbage**: f191's bank floats 4..7 = (-inf,-inf,+inf,+inf) = the pass-all rect; f268's c3[0x20..0x2c] likewise. With the measured bank the exact f191 formula reduces to texel * vertexColor with alpha unclipped - IDENTICAL to the draft's output.
- **f191 fully decoded (envydis)**: TEXS dest = the quad at REG_00 ($r0..$r3); uv = a[0x90]/a[0x94] (perspective via rcp of a[0x7c]); colour = (texel + c3[0x0,0x4,0x8,0xc]) * vertexColor; alpha additionally * rect-guard(a[0xa0],a[0xa4] vs c3[0x10,0x14,0x18,0x1c]). The real translation's colour formula was already exact.
- **f268 fully decoded**: ONE texture (the two-sampler draft was wrong), texs dest=$r5 t2d rgb; kill = rect(a[0xa0],a[0xa4] vs c3[0x20..0x2c]) * tintA, clip-enable (c3[0x10] != 0), kill-enable (c3[0x30] != 0), threshold 0.5 (driver constant c1[0x4]); colour = (texel + c3[0,4,8]) * vertexColor. Gated variant WOL_F268_EXACT=1.
- **Vertex attribute addressing solved**: the a[] space indexes COMPONENTS, not attributes - a[0x80 + 16*attr + 4*comp]. v189's reads: attrs 0-3 = position xyzw (the c3 matrix transform), attrs 4-7 = colour rgba (a[0x9c] alpha scaled by c3[0x8c] - matches the existing c3[35]), attrs 8-9 = uv, passed through to the fragment's a[0x90]/a[0x94]. The runtime's vertex layout (pos 3f@0, rgba8@12, uv2f@16) matches the declared attribute descriptors (formats 0x22/0x25/0x16, offsets 0/12/16, stride 24) for the sprite draws.
- **Texture slots measured per draw (WOL_TSLOTS)**: f191 draws bind ONLY t0 = a 4x4 texture; f268 draws bind ONLY t0 = a 1920x1080 texture (candidate UI atlas). Texture content dumps added (WOL_TEXDUMP). The sign-area rendering depends on identifying these correctly.

## Late-night session (2026-10-13/14): the full menu art found, composite decoded, gameplay renders
- **The game's menu art is in its textures** (late dumps): a 1024x1024 atlas with the hanging sign "WEST OF LOATHING", CONTINUE / NEW GAME / LOAD GAME planks, a moonshine jug and bottles; a 1024x325 two-rail fence; a 256x16 font strip. The TOP pair draws them into an offscreen 1920x1080 UI RT.
- **f08bad2f composite = texel * c3[0,4,8,0xc]** (full envydis decode). The old default sampled a degenerate uv and swapped R/G - the on-screen "green" muzzle flash was a red flash after the swap. Swap removed + c3f scale; the clip-derived uv stays (the quad carries no uv attribute; the attribute route blanked the screen).
- **TEXS dest = the quad at REG_00 ($r0..$r3)**, coords REG_08/REG_20 - verified by following the consuming code (all three fragments add c3 to those four registers then multiply by the tint). All sprite fragments are standard tinted sprites.
- **v10 (guard input) = the transformed position** (SASS stores the matrix-chain result), fixed in the pair2 vertex.
- **Measured regression chain**: the uv attribute-transform in the shared pair vertex blanked the screen white (Mali quirk on an unused varying) - reverted after a build-by-build bisect (185 ok, 186 black, 187/188 white, 189 ok).
- **Current state**: the gameplay scene renders completely (desert, player with revolver, muzzle flash, tracer, MOVE/AIM/FIRE box, arrows) - see evidence gfx203/205/206. The menu state is the bare desert; the top2 pair (menu-UI, 2930 draws) runs but its output is not visible on screen yet - next workstream. Wall-clock phases are not deterministic across builds: capture dense mark sequences.

## 2026-10-14 morning: the menu-UI uv doubling (repack root cause) - FOUND AND FIXED (gated)
- **SASS ground truth, both pair vertices** (envydis, main paths fully decoded): f43463c5 stores `v9 = raw a_uv` and scales the COLOUR block v8 by c3[0x80..0x8c]*c3[0x90..0x9c]; d88c64a6 stores `v9 = raw a_uv` and scales v8 by c3[0x80..0x8c]. The earlier "v9 = a_uv*c3[32..33]" fix (8032846) was based on a misreading of the fmul feeding the a[0x84] COLOUR store - no pre-scale exists on any uv path.
- **Trace v2** (build-205): byte-exact before/after frame diff (the old 320x180 sample saturated at 57600 on a filled target and hid real writes), full stage-0 bank dump (`WOL_TRACE c3v`, 40 floats), texture dump by id, indexed PAM names.
- **gfx222 census**: the first 32 draws sampling the menu atlas (id 493) write EXACTLY ZERO pixels; the sample = v9/v7.w ~ 0.0005 = the atlas corner. Banks/matrices are correct to the digit in the CPU replica; colour scales are 1; blend/scissor/mask valid.
- **All raw uv values are exactly 2x a clean [0,1) set** (5/5 distinct values: 0.5684/1.6133, 1.3184/0.2070, 0.3467/1.6367, 0.9326/1.1338, 1.0049/1.0479). Root cause: the memory repack halved the atlas (1024->512) while the runtime-computed sprite uvs keep the OLD pixel rects (uv = rect / CURRENT size). This is the measured mechanism behind "some assets don't display" (chat1.txt hypothesis).
- **New gated tooling** (build-206/207): `WOL_TOP_UV=raw|half|fract|mag` substitutes an isolated top-pair fragment program per draw (separate programs, never an if-chain); `WOL_TOP_TEXID` narrows to one texture (unset = every top draw, build-207); the selection prints `WOL_TOP_UV_SELECT`.
- **gfx224** (half + TEXID=493): every menu-atlas draw writes (6018..141687 px, was 0) and the physical screen shows the real menu - hanging sign WEST OF / LOATHING, CONTINUE / NEW GAME planks on chains, the XXX jug and bottles, crisp text (evidence/gfx224). The uv*0.5 sample without the /w divide is what matches the art.
- **gfx223** (top2 A/B, WOL_MASK_HIGHNIB=1): with the gate every other top2 draw writes a flat grey-127 panel (49585 px, RT274 407..641/347..557 -> screen 271..428/231..372); candidate menu plank. The guest mask word 0xfffffff0 vs 0xffffffff needs an honest decode before the gate can be a default.
- Open: (a) the /w divide - the awfully consistent SASS rcp(a[0x7c]) is empirically wrong for these draws (raw-all and half-all A/B runs: gfx225 baseline, gfx226 raw-all, next half-all); (b) generalising the uv correction beyond id 493; (c) bundle-side repack exclusion (restore the UI atlases) as the by-design repair; (d) top2 mask decode.


## 2026-10-14 (afternoon): default-half validation + pair2-family negative result

- **gfx228** (build-208, NO env uv set): default path selects `top-f-uvhalf` for every top draw - the
  good picture reproduces without any env (validated: WOL_TOP_UV_SELECT mode=half texid=0 x8 in the
  live log; frame compares to gfx227 within run-to-run jitter, sign region 13.5% / desert 10.8%).
  User verdict on gfx227/228 state: "в целом остальное более-менее нормально"; remaining gaps:
  WANTED-poster character figure missing, bottom-right control box missing its button icons.
- **gfx229** (build-209): extended the same treatment to the pair2 family (f191/f191-real/f268/
  f268-exact/pair2b+kill+diag sample `v9*0.5`, vertex back to raw `v9=a_uv`). RESULT: mass change
  across the whole frame (diff up to 66% per region); user: "сейчас как-то все приближено стало"
  (everything zoomed ~2x). => The pair2-family sampling is NOT the top pair's form; the *0.5 there
  samples half-range = zoom. REVERTED in build-210 (shader strings byte-identical to build-208,
  verified by strings-diff; deployed to the device).
- Correct model so far: the uv doubling ((repack) affects the TOP pair's world/UI sprites; the
  pair2-family elements that still render (text etc.) sample differently - their remaining broken
  pieces (poster character, button icons, f191/f268 corner-sampled fills) need a per-class diagnosis,
  NOT a blanket *0.5. Next: identify the exact draws for the missing icons/character (trace + atlas
  content match), then a targeted A/B.

## 2026-10-14 (evening): the f191 blind spot - probe-tool default + tiled-uv fold (poster figure and control icons land)

- **Root cause of the "WANTED figure + button icons missing" verdict**: `tools/wol_gfx_probe.py` had
  carried `WOL_F191_UV=xy` in its BASE env since the variant experiments on 2026-10-13. The xy variant
  samples `vec2(v8.x, v8.y)` - v8 is the vertex COLOUR lane, opaque white on these draws - so every
  nominally-production run sampled the whole f191 family at the constant (1,1) corner texel: the poster
  pieces, the control-box glyphs and the name text flat-blanked with the sample never touching the art.
  Measured proof: same build, `WOL_F191_UV=''` run (gfx251) shows the elements; the corner sample is a
  per-draw constant. The tool default is now `''` (the true draft); experiment selectors go via `--set`.
- **The f191 sprites use the page/tiled uv convention** (u 1.28..1.80, v 0..1.43 - the same
  "out-of-range = another page" scheme as the repack halving). The default f191 draft folds the lookup
  with `fract(v9)`: out-of-range coordinates tile, in-range lookups (frame outline, icons) are the
  identity. Verified twice: gfx251 (env forcing GL repeat) and gfx252 (NO env override at all) render the
  same poster ink (2634 / 2632 px below luminance 120) and the same control-box ink (2618 / 2627 px).
- **State after build-227** (sha256
  `d776be3d79044c2043a9344889607e4272974683b4c91bb272f1633d00f26772`): the WANTED poster contains the
  drawn character (face + hat) and the name "Wynona Carson"; the bottom-right box shows MOVE / AIM /
  FIRE with button glyphs; the sign, planks, fence and desert are unchanged vs the accepted gfx230
  (cross-run stable-difference map ~0 - the menu's own animation explains every per-frame delta).
- **Open polish items** (small, for user judgment against their reference): the control-box glyph
  identities read ambiguous at 24 px zoom; a leaf illustration + small ink marks sit near the poster
  name (6x zoom shows a deliberate drawing with veins and a stem, not noise); a scribble-like mass
  near the OPTIONS plank. Classify each as game art vs mis-sampled draft element before touching the
  drafts again.

## 2026-10-14 (day): the per-texture raw lists - OPTIONS sign, BEANS can, locator arrows (gfx257-262)

- **The mixed-family model, measured**: WOL_RECT_HIT hits now print the bound texture via the
  tex_state line (gl name + id + size). The traces show BOTH draw families mix repacked and
  never-repacked textures:
  - repacked (bundle width >= 512 -> halved at runtime -> uvs 2x): menu atlas id493, fence id513,
    landscape id543, poster art id499, piece sheet id313, ...
  - never-repacked (uvs already normalized or page-tiled): OPTIONS sign part id494 (434x186),
    beans can id556 (128x256), locator arrows id468 (300x300), font id630, frame id510, tuft id582.
- **Fixes for the three user reports** (all device-verified):
  - OPTIONS sign "partial letters + tangle" (gfx257): the universal top-half sampled the sign's
    already-normalized uvs at half range = the left half of the texture. Fix: WOL_TOP_RAWID - the
    listed ids sample raw v9 (top-f-uvraw); everything else keeps half. OPTIONS fully readable.
  - "the beans can has no label" (gfx257/261): the can (id556) was half-sampled; raw restores the
    BEANS label. The label's last letter was additionally covered by a mis-sampled locator arrow;
    both clean after the arrow fix.
  - the left locator arrow on the bottle label rendered as a dense scribble (gfx259 trace: the
    arrow quads come from the f191 pair, id468, with out-of-range page-tiled uvs; halfgt wrongly
    halved them into the wrong region). Fix: the new "f191-nofold" catalog entry (fract fold, a
    distinct name so the WOL_F191_UV override skips it) + WOL_F191_NOFOLDID="468" (gfx261).
- **Regression registered (gfx260)**: the experiment "base half + nofold {468,510,630,582}" visibly
  destroyed the control box and font draws - the f191 family is MOSTLY never-repacked, so halfgt
  (in-range lookup = identity) is the correct base; per-id handling narrows to the actual
  difference-maker id468. Reverted to halfgt + nofold {468}.
- **Production defaults baked (build-235, ELF sha256 06cc0b078df691382e13c98787093ad1344e4ec234be1c98272364041765aaba)**:
  WOL_TOP_RAWID unset/empty = {494,556}; WOL_F191_UV unset/empty = halfgt; WOL_F191_NOFOLDID
  unset/empty = {468}. Explicit "none"/"off"/"draft" values keep the experiment-free paths for A/B.
- **Verified final state (gfx262, NO env overrides)**: WEST OF / LOATHING, CONTINUE, NEW GAME,
  OPTIONS, BEANS, L MOVE / R AIM / ZL / ZR FIRE all readable; poster name readable; props and
  scenery clean; no scribble masses (the wire coil at far left is intentional scenery).
- **Open**: the WANTED figure. Our save renders "Wynona Carson"; the user's reference frame is
  "Gaylord Ninny III" (hat + sword) - different characters, so the figure's limb assembly must be
  judged against the real Wynona poster, not against that reference. Awaiting the user's ground
  truth photo before touching the piece assembly.
