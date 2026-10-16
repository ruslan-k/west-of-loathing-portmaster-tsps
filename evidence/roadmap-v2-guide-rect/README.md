# Negative control: rect trace capped before the guide opened

Kept as a method note, not as evidence about the guide.

`WOL_RECT_TRACE=440,400,760,620` with `WOL_RECT_TRACE_LIMIT=20000`: the 20 000-hit budget was
exhausted by frame 1 770, while the guide opens at frame 2 285, so **zero** traced draws fall in
the guide period. The follow-up runs ([`../roadmap-v2-guide-rect2/`](../roadmap-v2-guide-rect2/README.md),
[`../roadmap-v2-guide-diag/`](../roadmap-v2-guide-diag/README.md)) raised the budget and re-ran.
Owner save restored, cleanup verified, no warnings.
