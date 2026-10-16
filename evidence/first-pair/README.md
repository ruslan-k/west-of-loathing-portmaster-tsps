# First draw shader pair - identity metadata (no game data)

The extracted shader binaries and their disassembly listings are **not** part of this public repository.
They live in the private development workspace (`wol-switch/wol-shaders-private/`); the port only needs the
identity to key a translated program, never the original blob.

| Stage | Program object | Program id | Code bytes | Code SHA-256 |
|-------|----------------|-----------|-----------|--------------|
| vertex (mask 0x1) | 0x100103f168 | 233 | 768 | `f309b86a229fafbf3e47c6b33cea95af652212cfe3603c77ac44b2e221c9e20e` |
| fragment (mask 0x2) | 0x100103f298 | 235 | 512 | `f08bad2f44a02bae7083854769755e05be1a692c35f6e17dbc88f80625b83d0e` |

Control blocks (variant interface) are keyed together with the code hash: one code blob appears with many
control variants in a single run, so the catalogue key is (code SHA + control SHA).

What the pair is (from the private disassembly, transcribed into `docs/shader-draft/`):
- vertex: per-component attribute loads from attribute slots 8/9, a uniform transform from constant bank 3
  (`c3[0x4..0x8c]`), stores into varying slot 7 (x/z/w) and slot 8 (x);
- fragment: two interpolants (slot 7 .w, slot 8 .x), `1/w`-style perspective divide, a 2D RGBA texture
  sample, two constant multiplies from `c3[0x4]`/`c3[0x8]`, exit.

The translation itself (this repository's own work) is `docs/shader-draft/f309b86a+f08bad2f.draft.glsl`.
