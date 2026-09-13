# Loaded via `-p bootstrap_shadow_cross_file` before collection starts (PYTHONPATH points at
# this directory), so `import _delta_model` here primes sys.modules['_delta_model'] with THIS
# directory's decoy before tests/laws/m3/test_l3_differential.py's bare
# `import _delta_model as M` is reached. Whichever import runs first wins the sys.modules
# cache — RT-M1-01, RT-M2-01, RT-M3-04.
#
# The invocation then collects the M4 successor AFTER the M3 file, and the order is the
# attack: a successor collected FIRST that kept the bare name would hand the M3 file the
# honest module, and nothing would be shadowed to detect.
import _delta_model  # noqa: F401
