# Gulch right-walk with the analog stick — same stop as the d-pad

Second bounded attempt at the same owner-given route, changing one input variable: the
left analog stick (packed `lx = +32767` in the diagnostic packet's stick field, see
`native/input_host.h`) instead of the d-pad right bit, four 1500 ms pulses plus two A
presses. Same runtime `0cca40eca762c984…`, same owner save `tut_gulch`, features off.

Result: identical shape to the d-pad run — two pulses move the scene (19.0 %/21.1 % of
pixels changed, 15.1 %/17.0 % above threshold), the third and fourth change almost
nothing (3.0 %/0.9 %, 1.4 %/0.8 %), and the A presses only disturb fixed animated areas.
No battle, dialogue or transition. The game accepted all 7 injected presses
(`HID_DIAGNOSTIC_PRESS … stick=32767,0`), zero GL errors, owner save restored, exact
PID/start-time cleanup, real Spruce menu verified, no cleanup warnings.

Conclusion and next step are in [`../roadmap-v2-gulch-combat/README.md`](../roadmap-v2-gulch-combat/README.md).
