# Round-4 consultation: verdict Blocked

Asked for one reversible experiment to reach 30 presents/s. The answer refuses to
name offsets and says why: the v24 field offsets cannot be produced from the
public repo, because that needs the update's own `global-metadata.dat` plus the
`main.data.seg` registration table, and the bytes live only in the owner-local
image.

Confirmed by the consultant (matches our measurements):

- v23's `forceWidth/forceHeight` (+32/+36) yielded 32.638-33.878 presents/s vs
  24.019-24.226 controls, so the mechanism is real for that build only.
- Our v24 hook site `0x13963d8` reads the aspect pair 16:9, not the force fields;
  applying +32/+36 to that object would be wrong.
- `Screen::get_width/height` already return 1280x720 at the measured site, so
  rewriting them is not a proven lever (the old comment in `wol_uprender_v24.h`
  is stale).
- `0x13965a0` calls metadata initialization, not the RenderTexture constructor.
- The title has exactly four 1920x1080 allocations; the v23 win came from nine
  dynamic create requests that only exist in gameplay.
- Counting "size=1920x1080" mentions as allocations inflates the data (74 extra
  mentions in our trace), and `WOL_RT_ORIGIN` misreads the builder by 8 bytes, so
  its dimensions are not independent evidence.

## The named next step

Write `tools/wol_il2cpp24_owner.py` (read-only, fail-closed) modelled on the v23
parser: verify metadata magic/version, resolve the unique `UpRender` type, match
`forceWidth`/`forceHeight` definitions to the validated per-type field-offset
registration, and emit a machine-readable owner map with input hashes. Refuse on
any ambiguity. Only then touch fields, default-OFF and identity-gated.

Blocked operationally: the device is powered off and needs a physical power-cycle
before anything else can run.
