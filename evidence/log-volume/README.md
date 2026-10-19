# Log-volume measurement (§18.7.4)

The runtime redirects all stdout/stderr into `logs/latest.log`; the dominant volume is the
per-frame `NVN_PRESENT_UNMEASURED` cadence. Measured from the collected acceptance logs:

| trial | raw log | gz | present lines | last frame | bytes/frame | equiv. at 30 fps |
| --- | --- | --- | --- | --- | --- | --- |
| accept-b1 | 9.3 MB | 0.6 MB | 6,289 | 6,345 | 1,464 | ~2.6 MB/min |
| accept-a1 | 7.8 MB | 0.5 MB | 4,758 | 4,802 | 1,632 | ~2.9 MB/min |
| accept-b2 | 8.3 MB | 0.5 MB | 5,588 | 5,638 | 1,476 | ~2.7 MB/min |

So the cadence costs **≈1.5 KB per displayed frame** (≈2.6–2.9 MB per minute of play, ≈160 MB per
hour), and gzip compresses it ~13×.

Device state at the same check (2026-10-19): `logs/latest.log` 54.4 MB, `logs/` 146.4 MB across
115 files (≈1.3 MB per past run), on a card at **100 % (≈395 MB free of 117 GB)**.

**Implication:** roughly 2.5 hours of ordinary play can fill the remaining space on that card.
The cadence is also the FPS/continuity measurement source, so dropping it silently would reduce
evidence quality; the recommended remedy is **rotation, not silence** — keep the last N runs plus
any run whose log contains a `STOP`, a fail-closed guard or a black-screen receipt, and compress
or discard the routine per-frame bulk of the rest. This is a retention decision for the owner;
no evidence was deleted here.
