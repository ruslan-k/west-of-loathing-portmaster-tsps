# Guide screen UV-gate A/B (the panel content does not come back)

Two reversible sessions, owner save restored (`4a86756d8bf5e115…`), runtime `0cca40eca762c984…`,
features off, the same one-press guide route, cleanup verified and no warnings.

| arm | gulch | mine | boneyard | town | fricker | centre | title |
| --- | --- | --- | --- | --- | --- | --- | --- |
| default | 0.00 % | 1.76 % | 0.00 % | 4.48 % | 3.09 % | 0.00 % | 23.99 % |
| `WOL_TOP_UV=raw` | 0.00 % | 1.76 % | 0.00 % | 4.50 % | 3.09 % | 0.00 % | 23.99 % |
| `WOL_TOP_UV=legacy` | 0.00 % | 1.76 % | 0.00 % | 4.48 % | 1.38 % | 0.00 % | 23.99 % |

Dark-pixel share per region, reference frame for scale: 23.71 / 31.64 / 21.54 / 18.39 / 14.99 /
1.48 / 25.94.

Result: the top-pair UV mode is not what hides the guide panel's map artwork and four labels.
`WOL_TOP_UV=legacy` (the pre-repair behaviour) only lowers the fricker region from 3.09 % to
1.38 %, i.e. it removes content rather than adding it.

Files: `guide-open-raw.png`, `guide-open-legacy.png`, `receipt-raw.json`, `receipt-legacy.json`.
This A/B needs no harness edit any more: `session.py` now forwards every ambient `WOL_*` variable
to the runtime, so the port's own gates can be swept without touching the harness.
