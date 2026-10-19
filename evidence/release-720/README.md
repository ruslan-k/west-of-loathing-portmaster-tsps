# Release 720 — owner-accepted experimental default (2026-10-19)

Deliverable per roadmap §17.4 step 8 / §17.10 step 5: promote the **720 UpRender size-only**
change into the normal handheld launcher, or honestly qualify it. **Decision (owner,
2026-10-19): PROMOTE — default ON in the stock Spruce launcher, kept as an experimental
label** (see "Exceptions" below). Owner acceptance was given after playing a battle and a
cave entry in the 720 profile with no visual or audio problems.

**Pinned build / private-hash references**
- runtime ELF `b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158`
  (main.text.seg 20,762,904 bytes; frozen acceptance build);
- main section sha256 `49bd16718ed0dc46f16599255791c7603e8aa2b5f04898784a39d6cacb9d0722`;
- overlay pin parity 209 files, `runtime/wol-adapter.patch`, overlay sha256
  `54eb28d27d713e7dc79c823ce5dd050264e399cfeeb7c8f6cc6ba693505eb9bf`;
- launcher `West of Loathing Switch.sh` sha256
  `272a499c4ef874fb5e9d2c46aa74e5541234ccd5800ab0a3dfb643eeb1e283de` with
  `export WOL_UPRENDER_720="${WOL_UPRENDER_720:-1}"` (line 87);
- pre-change backup `…sh.bak-720prep-20261019` sha256
  `fa30af838b22e01b7a5eeeb7c4f34c4b5eaf3f67c7a984eee0ba87ba90581f3a`;
- saves equal across all acceptance arms (`saves_equal: true`); owner saves preserved.

## Acceptance matrix (per scene)

| Scene / item | Status | Evidence |
| --- | --- | --- |
| Moving Gulch world | PASS (measured; P95 exception) | accept-720 six arms; 86/86 motion segments |
| Guide map open / travel / return | PASS | accept-720 (map/return); scene-coverage nav1–nav4 |
| Town travel + dialogue | PASS | nav3/nav4/nav5b town center; sign/dialogue text box |
| Cave entry (entered location) | PASS (owner-reported) | owner-battle-720 |
| Battle (720 profile) | PASS (owner sighting + KMS frame) | owner-battle-720 — 32.1/31.7 fps, clean frame |
| Interior — town building | NOT CAPTURED | door-entry attempts failed (nav4/nav5b); cave visit stands in |
| Save/load full cycle | OPEN | not yet exercised in the 720 profile |
| Physical buttons audit | PARTIAL | owner played with physical controls; formal audit open |
| Audio | PASS (owner + stream check) | ALSA PCM-out RUNNING in both owner sessions |
| Rare NVN guard (NVN_COMMAND_RECORD_SIZE) | OPEN (P0) | one 1/18 event, not reproduced — §17.5 plan |
| Sparse TransferMemory | OFF (candidate) | battle/save-load coverage pending — §17.6 |

## Performance (measured, stock clocks)

Moving Gulch, paired clean-window arms (`../accept-720/`):

| arm | profile | presents/s | p50 ms | p95 ms | p99 ms |
| --- | --- | --- | --- | --- | --- |
| accept-b1 | 720 | 31.57 | 30.7 | 34.4 | 43.9 |
| accept-b2 | 720 | 32.97 | 30.4 | 35.7 | 39.5 |
| accept-b3 | 720 | 29.02 | 33.2 | 37.9 | 47.8 |
| accept-a1 | 1080 | 22.53 | 42.9 | 48.1 | 57.9 |
| accept-a2 | 1080 | 22.97 | 42.1 | 47.4 | 60.5 |
| accept-a3 | 1080 | 22.83 | 42.3 | 47.8 | 54.5 |

Paired deltas (720−1080): **+9.04 / +9.99 / +6.19 presents/s**; p95 **−13.8 / −11.7 / −9.9 ms**;
process SwapPSS **−39.7 / −35.6 / −45.2 MiB**. Owner sessions (same battle arena):
28.3/28.1 fps (1080) vs **32.1/31.7 fps** (720, +13 %); process swap 487→580 vs **443→445 MiB**;
Mali commit ~322.0 vs **254.7 MiB**; system swap used 631→708 vs **602→606 MiB**.

Long gaps: four >1 s gaps in the acceptance series (a1 0.62 s; b2 two × 2.74/1.29 s at
game-idle; b3 0.58 s) — all with major-fault bursts and MemAvailable minima 54.7–85.4 MiB;
zero in the sparse series. The single dead-process event (nav5 guard stop) is tracked
separately under §17.5 and was not a hang.

## Exceptions and honesty notes (why the label stays "experimental")

- Strict FPS goal (>=30/s and p95 <=33.33 ms in every arm) is **not met**: one moving arm is
  29.02/s and moving p95 is 34.4-37.9 ms. The owner accepted the trade-off explicitly after
  real play (battle felt fine; +13 % measured vs the previous default session, same arena).
- Two acceptance rows remain open: full **save->quit->load** cycle in the 720 profile and
  the formal **physical-buttons** audit; town-building interiors were not captured (the cave
  visit stands in as the entered-interior transition).
- Sparse TransferMemory stays default **OFF** until battle/save-load coverage; zero-swap is
  parked/unachieved and is not claimed anywhere.
- No visual regressions vs 1080 were observed (KMS frames across all arms and owner
  sessions; ~97 % pixel match on the same battle arena).

## Revert

Restore the pre-change launcher: copy `West of Loathing Switch.sh.bak-720prep-20261019`
back over `West of Loathing Switch.sh` (or set `WOL_UPRENDER_720=0` for a session). No
runtime or save changes are involved - the change is one launcher env line.

## Evidence index

- `../accept-720/` — six-arm paired 720/1080 series (performance basis of this release);
- `../scene-coverage/owner-battle-default/` — battle in the default profile (baseline);
- `../scene-coverage/owner-battle-720/` — battle + cave in the 720 profile (acceptance run);
- `../scene-coverage/` — nav1-nav5b guide-map/town shots, routes, guard-stop record;
- `../uprender-owner/`, `../uprender-scope/` — UpRender mechanism evidence;
- `../transfer-sparse-repeat/` — sparse candidate pairs (still default OFF);
- `../unity-arena-owners/` — zero-swap no-go;
- `../../docs/optimization-roadmap.md` — sections 16-17 (execution log and decision contract).
