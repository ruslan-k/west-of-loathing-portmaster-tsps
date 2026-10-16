# Guide screen state A/B: which save is loaded does not change it

`--control-save /mnt/UDISK/roadmap-v2-v2-audit-saloon/owner-save` (control save hash
`8a70c734feaee946b2618fa85ff6f47670667e5f6932e8d11c23f1c2cf525779`) replaces the owner's
gulch-state save for one run; the owner save is restored afterwards (`4a86756d8bf5e115…`, verified),
runtime `ba5a0dd51d5c5618f8ab5761b9af9c5f341d83d3da021be6bd8d98c2dc6387ba`, same one-press guide
route, cleanup verified with no warnings.

| region | reference | gulch state | saloon state |
| --- | --- | --- | --- |
| Thousand Snakes Gulch | 23.71 % | 0.00 % | 0.00 % |
| Orehole Mine | 31.64 % | 1.76 % | 1.76 % |
| Boneyard | 21.54 % | 0.00 % | 0.00 % |
| Town of Boring Springs | 18.39 % | 4.48 % | 4.49 % |
| Fricker Hideout | 14.99 % | 3.09 % | 4.56 % |
| map centre | 1.48 % | 0.00 % | 0.00 % |
| title | 25.94 % | 23.99 % | 23.99 % |
| panel interior overall | — | 2.12 % | 2.23 % |

OCR of the saloon-state guide frame reads the same single label at the same place
(`Thousand` / `Snakes Gulch`, x471–631, y515–573) plus the same heading, EXIT, ©1890 and SELECT.
The world frame behind it differs (the loaded scene changed), the guide panel does not.

Files: `guide-open.png`, `world.png`, `receipt.json`.
