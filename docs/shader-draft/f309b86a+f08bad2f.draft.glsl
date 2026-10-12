// WoL first shader pair - DECODE-STATE DRAFT. NOT A WORKING TRANSLATION.
//
// Source of every line below: evidence/first-pair/vertex.sass.txt and fragment.sass.txt
// (envydis -m gm107 -d 0x30; the captured blob starts with the SPH header, magic 0x12345678).
// Rule applied here: only statements that are supported by a DECODED SASS line appear; every
// unresolved element is a TODO, never an invention. Do not bind this to a draw.
//
// Faithful conventions (verified):
//   constant bank 3 -> uniform float c3[N], c3[0xNN>>2] is exactly the u32 at byte 0xNN
//   attribute space -> a[0xNN] is slot 0xNN>>4, component (0xNN>>2)&3   (a[0x80] = a8.x)
//   varying space   -> a[0xNN] is slot 0xNN>>4, component (0xNN>>2)&3   (a[0x7c] = v7.w)
//
// ---------------- VERTEX (code sha f309b86a..., 768 B) ----------------
#version 100
precision highp float;
attribute vec4 a8;             // slot 8  - ld b32 $r6 a[0x80] (+ a[0x84],a[0x88] likely r4,r5)
attribute vec4 a9;             // slot 9  - ld b32 $r8 a[0x90]
uniform float c3[96];          // constant bank 3, byte offsets 0x00..0x17f
varying vec4 v7;               // st b32 a[0x70] (and a[0x74],a[0x78],a[0x7c] per the st lines)
varying float v8;              // st b32 a[0x84] $r5
void main() {
    // TODO(attribute components): which of a8's components feed r4,r5,r6 is not yet established;
    // the guest vertex-attrib state object (nvnCommandBufferBindVertexAttribState) is the source of
    // truth and has not been decoded. Without it a wrong swizzle would silently misplace geometry.
    float r4 = a8.x, r5 = a8.y, r6 = a8.z;   // PLACEHOLDER ORDER - see TODO above
    float r7 = c3[0x80/4], r10 = c3[0x84/4];
    float r8 = a9.x;
    float r0, r1, r2, r3;
    r1 = r4 * c3[0x14/4];
    r0 = r4 * c3[0x10/4];
    r3 = r6 * c3[0x4/4]  + r1;
    r3 = r5 * c3[0x24/4] + r3;
    r1 = r4 * c3[0x18/4];
    r2 = r5 * c3[0x20/4] + r2;      // NOTE: $r2 is read here before any decoded write; an undecoded
                                    // instruction (one of the 33) initializes it - see TODO(below)
    r3 = r3 + c3[0x34/4];
    r0 = r6 * c3[0xc/4]  + r0;
    r2 = r2 + c3[0x30/4];
    r1 = r5 * c3[0x28/4] + r1;
    r0 = r5 * c3[0x2c/4] + r0;
    r6 = r2 * c3[0x40/4] + r4;
    r4 = r3 * c3[0x58/4];
    r8 = r8 * r7 + c3[0x88/4];
    r1 = r1 + c3[0x38/4];
    r7 = r2 * c3[0x44/4] + r5;
    r4 = r2 * c3[0x48/4] + r4;
    r0 = r0 + c3[0x3c/4];
    r6 = r1 * c3[0x60/4] + r6;
    r3 = r1 * c3[0x68/4] + r4;
    r1 = r1 * c3[0x6c/4] + r2;
    r6 = r0 * c3[0x70/4] + r6;
    v8 = r5;                        // st b32 a[0x84] $r5
    v7.x = r6;                      // st b32 a[0x70] $r6
    r3 = r0 * c3[0x78/4] + r3;
    r0 = r0 * c3[0x7c/4] + r1;
    v7.z = r3;                      // st b32 a[0x78] $r3
    // TODO(position): gl_Position and the remaining varying stores (a[0x74], a[0x7c], r10's slot)
    // come from the undecoded lines; no value is invented here.
    gl_Position = vec4(0.0, 0.0, 0.0, 1.0);   // PLACEHOLDER - do not draw with this
}

// ---------------- FRAGMENT (code sha f08bad2f..., 512 B) ----------------
#version 100
precision mediump float;
varying vec4 v7;               // ipa pass $r6 a[0x7c]  -> v7.w
varying float v8;              // ipa pass $r0 a[0x84]  -> v8
uniform sampler2D tex0;        // texs nodep $r2 $r0 $r4 $r5 0x8 t2d rgba
uniform float c3[96];
void main() {
    float r6 = v7.w;                     // ipa pass $r6 a[0x7c]
    float r0 = v8;                       // ipa pass $r0 a[0x84]
    float r5 = 1.0 / r6;                 // mufu rcp $r5 $r6
    r5 = r5 * r0;                        // fmul ftz rz $r5 $r5 $r0
    // TODO(tex operands): the decoded text is "texs nodep $r2 $r0 $r4 $r5 0x8 t2d rgba"; which
    // registers carry (u,v) and which carry the LOD/offset is not established. The natural reading
    // is u = r0, v = r5 (the perspective-divided value) with LOD 0, but that is a reading, not a
    // measurement: verify against the guest's texture/sampler state before trusting it.
    vec4 t = texture2D(tex0, vec2(r0, r5));   // SUBJECT TO THE TODO ABOVE
    float r1 = t.x * c3[0x4/4];          // fmul ftz $r1 $r1 c3[0x4]
    float r2 = t.y * c3[0x8/4];          // fmul ftz $r2 $r2 c3[0x8]
    // TODO(channels): the SASS multiplies two channels with two constants; how the third/fourth
    // channel and alpha are produced (and whether a constant add follows) is in the undecoded lines.
    gl_FragColor = vec4(r1, r2, 0.0, 1.0);    // PLACEHOLDER for the undecoded tail
}

// MEASURED SINCE THE FIRST DRAFT (runs 48/49, private disassembly; rule validated against all samples):
//
//  * the attribute/varying space of this SDK encodes: byte0 = register, byte2 = (component<<4)|0x7,
//    byte3 = slot; control word 0xefd87f80 = `ld b32`, 0xeff07f80 = `st b32`; the INPUT attribute space
//    starts at 0x80, the OUTPUT (varying) space at 0x00.
//  * inputs of this pair, all five loads with the validated address rule (address = 0x10*slot + 4*comp,
//    the component read from bits 6-7 of the third byte): slot 0 = (r6,r4,r5) = position x/y/z
//    (FLOAT32x3 at offset 0 of a stride-88 stream), slot 1 = (r8,r9) = the second FLOAT32x3 at offset 40,
//    read only as a vec2.
//  * outputs, all six stores: varying 7 = (r6,r7,r3,r0) - a full vec4; varying 8 = (r8,r5) - a vec2.
//    The fragment reads exactly v7.w and v8.y, so the storage map matches on both sides; note that the
//    value stored into v8.y is r5 = input slot 0 component 2, i.e. the position z.
//  * therefore v7 is the clip-position candidate (a vec4 stored by the vertex stage) and v8 the uv-like
//    pair; that assignment is confirmed empirically when the pair is first wired, not assumed here.
//  * still open: the predicated ALU ops (fe/3e/ff forms) that feed the stored values, the TEX operand
//    roles and the fragment tail. The instruction listing is complete (private workspace), so these are
//    decode work, not guesswork.
