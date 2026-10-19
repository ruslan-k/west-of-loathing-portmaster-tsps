# Runtime license and provenance

`wol-horizon` is a build of the recovered **upstream** Horizon runtime (GPL-3.0) plus this
repository's adapter overlay.

- Baseline source: `runtime/source-manifest.sha256` (435 files), reconstructed as described in
  [`../../docs/upstream-source.md`](../../docs/upstream-source.md).
- Modifications: [`../../runtime/wol-adapter.patch`](../../runtime/wol-adapter.patch) — the same
  patch that this binary was built with (verified: patched baseline reproduces the source tree with
  zero differences, see [`../../evidence/source-parity/README.md`](../../evidence/source-parity/README.md)).
- Build recipe: [`../../build_horizon.sh`](../../build_horizon.sh) with the pinned cross toolchain.
- Project license: [`../../LICENSE`](../../LICENSE) (GPL-3.0).

This binary contains **no game data**: no NSO segments, NPDM, RomFS content, textures, shaders,
saves or keys. At runtime it reads the owner's own `*.seg` files and `wol-romfs.section` from the
game directory. The string constants it embeds are diagnostic names and SHA-256 identity pins.

Deployed build: `fef4f7831407e21459c51cce17e19a8474de014d2e737f695117b5f02e5525b9`
(1,966,864 bytes). The previously accepted build `b60057ea…` differs only by the release-profile
logging gates documented in [`../../evidence/quiet-build/README.md`](../../evidence/quiet-build/README.md).
