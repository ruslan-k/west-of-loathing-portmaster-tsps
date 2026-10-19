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

Packaged build: `ac5b33e05133771a014e0f382fc1a5d2bff0ea5406820ce3b3c914fad4574d9f`
(1,975,008 bytes). The original source is manifest-checked before a reproducible
name-normalization step is applied to the build copy; the upstream commit identifiers
remain in `docs/upstream-source.md`. On-device smoke has reached the title menu and
returned to Spruce; a fresh full owner gameplay/save acceptance remains open.
