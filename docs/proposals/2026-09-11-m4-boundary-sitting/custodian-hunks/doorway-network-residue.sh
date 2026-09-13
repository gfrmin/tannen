
# --- M4 DRAFT HUNK: check_doorway (RT-M4-02, D0229 item 2, D0248) ------------
# The shell's IO doorway, DERIVED rather than enumerated: an import whose static module-level
# closure reaches socket or ssl, or an os.system/popen/exec/spawn shell-out, anywhere outside
# tannen.oracles and tannen.r2 (the network doors) and tannen.laws (the runner door). The
# fixture is a miniature src/tannen/ carrying one payload per way frozen L4.9 misses, beside
# control modules that must stay silent. L4.9's own scanner finds nothing in the same tree —
# which is RT-M4-02, demonstrated rather than argued.
poison check_doorway "reads the world outside the doorway" \
    "$PY" -I -P scripts/check_doorway.py --root tests/poison/doorway-network-residue
# --- end M4 DRAFT HUNK: check_doorway ----------------------------------------
