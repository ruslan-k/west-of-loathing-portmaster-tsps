# IPA / attribute access maps for the two remaining program pairs

Decoder: `wol_access_decode.py` (private workspace) - `envydis -m gm107 -d 0x30` output plus the
validated operand rules for `ld`/`st`/`ipa`, including lines envydis renders as `???`. Verified at
100% agreement on every decodeable access line of all four blobs (and on the earlier hand-verified
f309b86a list).

## Shared vertex `d88c64a6` (used by v189 and v266)

Inputs (attribute space, base 0x80):

```
a[0x80..0x8c] -> r7,r5,r8,r6   slot 0 = position (FLOAT32x3 + w), 12 bytes
a[0x90..0x9c] -> r9,r10,r11,r0 slot 1 = colour RGBA8 (loaded b32 per channel), 4 bytes
a[0xa0..0xa4] -> r12,r13       slot 2 = uv (FLOAT32x2), 8 bytes
```

Outputs (varying space):

```
v10 = (r7, r5, r8, r6)  raw position xyzw (r6 = raw position w)
v9  = (r12, r13)        uv
v8  = (r9, r10, r11, r6*c3[0x8c] after 0x1f8)  colour.rgb + alpha term
v7  = transformed position (r7 has been ffma'd by then)
```

Matches the measured stride 24 (12 + 4 + 8).

## Fragment `f191` (512 B) - tinted sprite, no kil

```
0x058 ipa pass r4 <- v7.w     (0x068) r0 <- v9.x   (0x078) r1 <- v9.y
0x088 r7 <- v10.x  (0x098) r8 <- v10.y
0x0a0 r9 <- v8.w   (0x0a8) r5 <- v8.y   (0x0b8) r6 <- v8.x   (0x0c0) r4 <- v8.z
```

Plus one `texs` (t2d rgba); the ALU chain then uses fsetp/fadd/lop3/fmul. r4 is written twice
(v7.w then v8.z); predicate bits unresolved - guard terms to be settled during authoring.

## Fragment `f268` (1024 B) - text/UI signature, two samples, alpha kil

```
0x058 ipa pass r2 <- v7.w
0x068 r0 <- v10.x  (0x078) r1 <- v10.y
0x080 r5 <- v8.w
0x108 r1 <- v9.y   (0x168) r0 <- v9.x
0x188 r8 <- v8.x   (0x198) r9 <- v8.y   (0x1a0) r10 <- v8.z
```

r0/r1 are written twice (v10.xy then v9.xy); the second pair is the texture-uv candidate to be
confirmed at authoring time.
