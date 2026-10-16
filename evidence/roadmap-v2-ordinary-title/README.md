# Pre-fix ordinary-title observation (not diagnostic-free)

This run used the ordinary launcher without harness overrides, but its effective environment still contains `COTM_INPUT_DIAGNOSTIC=1`, supplied by the old launcher default. The environment assertion correctly rejected a diagnostic-free interpretation. Runtime/save cleanup itself succeeded.

Keep this as the pre-fix observation, not as clean-launch acceptance. The isolated default-off fix, backup/hash verification, repeated real title/menu captures and scope limits are in [the clean-title report](../roadmap-v2-clean-title/README.md).
