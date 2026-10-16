# Same-save desktop reference: guide/map rendering differs in the port

## Result

The owner loaded the port's **Wynona Carson** save in the desktop Steam build and opened the guide.
A physical DRM/KMS capture confirms all five tutorial destinations, their artwork and three NEW tags:

- Thousand Snakes Gulch (selected).
- Orehole Mine — NEW.
- Boring Springs Boneyard — NEW.
- The Town of Boring Springs.
- The Fricker Gang's Hideout — NEW.

The desktop permaflags now names `save-Wynona Carson-639274980123448959` as LAST_SAVED. The owner
also explicitly confirmed successful loading and the presence of the map elements. This is a real
same-save reference, not the earlier Larry Oakley map or a YouTube frame from unknown progress.

## Exact save relationship

- Original Switch file: SHA-256 `4a86756d8bf5e11577efd653dd34e7ab4d3603705e10f5b7d31d486ce5901af0`, 11033 bytes.
- Desktop test copy: SHA-256 `576bd93bb97fcac9050a78aa0cd88d6f5b52f88e502a26625e850a712b45a26f`, 11031 bytes.
- Conversion: remove exactly the initial two bytes `97 56`; leave every following byte unchanged.
- Strict parsing of the entire raw Switch file fails UTF-8/JSON; strict parsing of the converted
  desktop copy succeeds. The parsed JSON payloads are identical; no flag, item, location or progress
  edit was made. Payload equality was checked again after the owner's load.
- Name: Wynona Carson; played `05:10:09`; location `tut_gulch`; WAA_ID `tut_gulch,1580,57`.
- Map flags: `map_bsmain`, `map_bsgulch`, `map_bsmine`, `map_bscemetery`, `map_bsfricker`, all `1`.
- `unvisited_map_locations=bsfricker,bsmine,bscemetery`, matching the three visible NEW destinations.

The original Switch source remains unchanged. The pre-conversion desktop test copy and a conversion
receipt were backed up locally. Larry Oakley's 24 save/backup files were hash-compared across the
conversion and were unchanged. No game restart, input injection or device launch was performed for
this reference capture; the owner controlled the game.

## Owner-content reference (local only)

Capture time: `2026-10-17T00:33:46+04:00`; physical output: HDMI-A-1, 3840x2160.
Capture method: `ffmpeg` kmsgrab on `/dev/dri/card1`, VAAPI mapping, one PNG frame.

The owner frame and receipt are retained outside the repository:

- `~/Downloads/WoL-reference-test/same-save-map-20261017-003346.png`
- `~/Downloads/WoL-reference-test/same-save-map-20261017-003346.receipt.json`
- Frame SHA-256: `97075453941d31597a9f52fb35c77f26ba5febfdc7b8be880a84961d4635be9f`.

Neither the owner screenshot nor any save is committed.

## Comparison with the archived port capture

`evidence/roadmap-v2-owner-map/map-now-1.png` is the previously captured 1280x720 TSPS guide.
The heading, paper border, compass and bottom controls are present, but the location arrangement is
wrong: Thousand Snakes Gulch is far lower on the paper than in the same-save desktop reference,
and part of the Orehole Mine icon/NEW tag/text is visible beyond the paper at the far right screen
edge. Thus "four objects are wholly undrawn" is too strong: at least one is displaced/clipped, not
simply absent. The other destinations are not visible in their correct paper positions.

**Established:** game progress and a damaged map-flag payload do not explain the difference. The
port's rendering/layout path fails to reproduce this same game state.

**At this reference-only checkpoint, not yet established:** whether the immediate cause is a matrix/viewport/scissor mismatch, a draft
shader reconstruction, a target/composite issue or a combination. The misplaced visible objects
made the map-object coordinate-space path a high-priority hypothesis. No fix or device A/B was
performed as part of this reference capture itself.

**Subsequently resolved:** the repack changed application-visible Sprite pixel dimensions while map
node coordinates stayed in original pixels. The dimension-protected repack restores the complete
map; both controlled KMS captures and an ordinary owner launch confirm it. See
[verified map pixel-space repair](../roadmap-v2-map-pixel-space/README.md).

## Superseded conclusions

The earlier version of this document asserted that equal field names and a LAST_SAVED entry proved
cross-loading. They did not: the raw Switch copy initially produced `Failed to parse text from file
[...] as JSON` and the on-screen save-load error because of the two-byte prefix. The analyst's parser
had sliced from the first `{`, masking that incompatibility. Successful loading is verified only
after the exact conversion and owner-driven load above.

The earlier attribution of the supplied YouTube tutorial-map frame to a mature, 51-location profile
was unsupported and is withdrawn. A mature desktop save's flag count cannot establish another
frame's progress, and this exact early tutorial save itself displays all five destinations.

Save-history observations remain useful as state context, but are not the decisive comparison. The
same-save desktop reference above supersedes the previous pending owner-check status.
