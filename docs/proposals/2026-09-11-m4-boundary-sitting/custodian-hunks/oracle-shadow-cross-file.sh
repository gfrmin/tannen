
# --- M4 DRAFT HUNK: oracle-shadow-cross-file (D0229 item 3(a)) ---------------
# The anti-disarm property of the M4 supersession, which no single-file line can see. The
# superseded tests/laws/m3/test_l3_differential.py and its successor
# tests/laws/m4/test_l4_differential_superseding.py are collected TOGETHER, superseded
# FIRST, under oracle-shadow-spoofed's code decoy. A successor loader that KEPT the frozen
# module under the bare name would overwrite the decoy before the guard reads sys.modules at
# the end of collection. The guard would then stay silent while the M3 file ran a stub:
# exit 0, measured, and the M3-only line above still bites over the same broken loader.
# Deviations are oracle-shadow-spoofed's (no -I -P, the attack IS PYTHONPATH; -B, sealed
# directory; the literal venv interpreter), plus two for the WEAKENED case only:
# --collect-only (the tooth is at collection; a weakened guard would otherwise run 28 nodes)
# and TANNEN_NO_EVIDENCE=1 (a weakened full run would write an M4 record from a stubbed
# differential). Order matters: with the M4 file first, nothing is ever shadowed.
poison oracle-shadow-cross-file "answers with different code" \
    env -u TANNEN_CHECK_DECISIONS_NESTED TANNEN_NO_EVIDENCE=1 \
    PYTHONPATH=tests/poison/oracle-shadow-cross-file \
    "$PY" -B -m pytest -p bootstrap_shadow_cross_file \
    tests/laws/m3/test_l3_differential.py tests/laws/m4/test_l4_differential_superseding.py \
    -q --collect-only -p no:cacheprovider
# --- end M4 DRAFT HUNK: oracle-shadow-cross-file -----------------------------
