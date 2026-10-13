# Hades (Yuzu shader recompiler) against the WoL shaders — evaluation

Date: 2026-10-13. Tool: `DCNick3/shader-compiler-rs` (builds `shader-compiler-cli`;
the vendored Maxwell frontend is the Yuzu "Hades" lineage). Requested by the
2026-10-13 review (~/chat.txt, variant A: check whether the automated Yuzu/Hades
path can translate our captured shader blobs).

## Working input format (established empirically)

The CLI strips 0x30 bytes from its input and passes `[SPH][SASS]` to Hades with
the instruction base at `0x10030 + sizeof(ProgramHeader)` (`ProgramHeader` = 0x50).
Our captured code blobs are `[0x30 unknown header][SASS]`, so a valid tool input is:

    [0x30 filler][0x50 synthetic SPH][blob[0x30:] as SASS]

with the SPH `shader_type` field (bits 10..13 of word 0) = 1 (vertex) / 5 (fragment).
The tool accepted this for all five blobs and reached instruction translation
(no header complaints), so the recipe is confirmed working.

Artifacts (private workspace, `spikes/wol-switch/tools/hades-eval/`):
compiler tree with patch notes, prepared `.bin` inputs, and the run script.

## Abort matrix (instrumented build that prints the offending instruction)

| shader | stage | first abort | instruction (raw u64) |
|---|---|---|---|
| fragment f08bad2f (already hand-translated pair) | frag | AL2P BitSize 2 | `0x001d7c00e6200711` |
| fragment f191 | frag | AL2P BitSize 3 | `0x003fb400f3e007b1` |
| fragment f268 | frag | AL2P BitSize 1 | `0x0020c401e3a0071f` |
| vertex f309b86a | vert | AL2P BitSize 3 | `0x0003f00000000000` |
| vertex v189 d88c64a6 | vert | FFMA32I CC | `0x0f3ff00000000000` |

Additionally, without touching the prologue, every shader first aborts at
**IMAD32I** on the prelude word at file offset 0x40 (bytes `00*7 80`), and f191
later aborts at **LOP3 (cbuf) with CC**.

The prologue (`[0x30..0x58)`, five words of mixed filler) was replaced with NOPs
for the matrix above; the aborting instructions listed are the ones the
translator reached right after the prologue.

## Brute-force check (NOP-out each offending instruction, no rebuilds)

Each abort names the exact instruction; replacing only those words with NOPs and
re-running gives the blocked-instruction census per shader:

- f08bad2f: 4 instructions NOP'ed (offsets 0x50/0x70/0x90/0xb0) — then **the tool
  produced GLSL**. However the output is semantically empty (one `sampler2D`
  declaration and four empty `if (_41) {}` blocks — no texture read, no output):
  the four words are NOT dead — suppressing them removes the shader's actual
  control flow, so "produces GLSL" here is NOT a valid translation. It only proves
  the remaining instruction stream decodes.
- f191: after 3 NOPs (0xb0/0xd0/0xf0) still stopped at LOP3 (cbuf) CC.
- f268 / f309b86a / v189: same families (AL2P sizes, FFMA32I CC).

## Follow-up (same day): the "AL2P" matches are an artifact of the decode table

Instrumenting `Decode()` in the vendored frontend (patch kept in the private workspace
copy) shows exactly what happens to the words neither `envydis` nor Hades can render:

    DECODE_DUMP insn=003fb400f3e007b1 WLB=13 MS=51 idx=7 hm=0000 hv=0000 opcode=AL2P

`WIDEST_LEFT_BITS=13`, `MASK_SHIFT=51`. The matched table entry has `high_mask=0`,
`high_value=0` and `opcode=AL2P` — but that entry is not the AL2P pattern. The
`FAST_LOOKUP_TABLE` buckets hold `std::array<InstInfo, 2>` slots that stay
default-initialized when a bucket has fewer than two encodings, and the match test
`(insn & info.Mask()) == info.Value()` is trivially true for a zero mask/value slot.
`Opcode(0)` is the first entry of `maxwell.inc`, which is AL2P. In other words:

**any instruction absent from this frontend's `maxwell.inc` decode table silently
decodes as AL2P.**

Consequences:

- The earlier "AL2P BitSize 2/3" aborts on the `???` words were this artifact, not a
  real instruction family; the words are simply not in this table revision (the
  reviewer's caution was correct: implementing AL2P bit sizes from those matches would
  have implemented semantics for a mis-decoded opcode).
- Any user of this frontend needs the one-line fix (reject zero-mask slots in
  `Decode()`) to get honest "unknown instruction" errors instead of silent AL2P.

## Partial implementations used for the smoke test (all in the private copy)

For the experiment the following were implemented in the vendored source (see the
`tools/hades-eval` copy; the exact changes are listed in the private notes):
`FFMA`/`FADD`/`FMUL` with CC (Z/S from the result, C/O cleared), `LOP3` with CC,
`IMAD32I` (dst = src_a * imm32 + dst), and AL2P bit sizes 1/2/3 accepted with the B32
address math (this acceptance is only a smoke-test escape hatch — see the artifact
above). With these:

- f08bad2f and f191 produce GLSL (44 and 69 lines), but **semantically void**: empty
  `if` bodies and undefined condition variables; only one real expression survives in
  f191 (`attr2.x * c3[?] <= c3[6]`). "Produces GLSL" is thus not a translation — the
  branch logic of these shaders runs through instructions the table does not know.
- v189 / f268 / f309b86a stop at FADD32I CC (stub implemented after the last matrix
  run; a rebuild + rerun is pending and does not change the conclusion).

## Reading / conclusions

1. The automated path is real but **not usable out of the box** for WoL: the
   vendored Hades is missing four opcode implementations:
   - `IMAD32I` (integer multiply-add with 32-bit immediate) — stub
     (`.../impl/` has no implementation; decoder maps the word, translate throws).
   - `AL2P` for BitSize 1/2/3 — only B32 is implemented in
     `attribute_memory_to_physical.cpp`.
   - `FFMA32I/FFMA` with CC — throws in `floating_point_fused_multiply_add.cpp`.
   - `LOP3 (cbuf)` with CC — throws likewise.
2. Decoder caveat: on the "???"-class words (the ones `envydis` cannot render),
   Hades' truncated top-16-bit match table produces AL2P matches whose fields are
   implausible, while a strict match against `maxwell.inc` for the same words
   finds nothing. Both dissectors must be reconciled on those words (likely a
   newer GT21x encoding revision) before trusting either result — and before
   "implementing" anything based on the match.
3. The known-first-pair fragment is not a shortcut: it hits the same instruction
   families as the untranslated pairs.

## Next steps (ordered)

1. Implement the four opcodes in the vendored Hades (small, localised changes),
   rebuild, and re-run the matrix until f08bad2f translates to non-empty GLSL that
   semantically matches the hand translation (that gives the reference oracle for
   f191/f268).
2. Convert its GLSL 4.50/Vulkan output to GLES 3.x for Mali (SPIRV-Cross options)
   only after the semantic check against the hand translation passes.
3. Keep the hand-transcription route for f191/f268 as the parallel path; the
   access maps are already in `docs/shader-draft/ipa-access-map.md`.
