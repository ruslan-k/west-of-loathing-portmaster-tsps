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

Deployed build: `ab132760de594598efe86fe08d2ac376da9f15d7c18a0e51ec230173cba23176`
(1,978,960 bytes). The previously accepted build `b60057ea…` differs only by the release-profile
logging gates documented in [`../../evidence/quiet-build/README.md`](../../evidence/quiet-build/README.md).
