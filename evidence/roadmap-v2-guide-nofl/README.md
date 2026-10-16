# Per-texture UV fold A/B for the guide's own atlas ids

One guide run with `WOL_F191_NOFOLDID` and `WOL_TOP_RAWID` both set to the guide screen's own atlas
ids (`3212,3213,3214,3223,3233,24495,24496,24497,24505,510`), owner save restored
(`4a86756d8bf5e115…`), runtime `ba5a0dd51d5c5618f8ab5761b9af9c5f341d83d3da021be6bd8d98c2dc6387ba`,
cleanup verified, no warnings.

| region | reference | default | nofold+rawid |
| --- | --- | --- | --- |
| gulch | 23.71 % | 0.00 % | 0.00 % |
| mine | 31.64 % | 1.76 % | 1.76 % |
| boneyard | 21.54 % | 0.00 % | 0.00 % |
| town | 18.39 % | 4.50 % | 4.53 % |
| fricker | 14.99 % | 3.09 % | 3.09 % |
| centre | 1.48 % | 0.00 % | 0.00 % |
| title | 25.94 % | 23.99 % | 23.99 % |
| panel interior | 9.95 % | 2.12 % | 2.12 % |

Result: the per-texture UV fold lists are not what hides the panel either. Context, class list and
the texture dumps are in [`../roadmap-v2-guide-texdump/README.md`](../roadmap-v2-guide-texdump/README.md).
