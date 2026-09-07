# Loaded via `-p bootstrap_shadow_spoofed` before collection starts (PYTHONPATH points at
# this directory), so `import _delta_model` here primes sys.modules['_delta_model'] with
# THIS directory's decoy before tests/laws/m3/test_l3_differential.py's bare
# `import _delta_model as M` is ever reached. Whichever import runs first wins the
# sys.modules cache — RT-M1-01, RT-M2-01, and now RT-M3-04 for the spoofed variant.
import _delta_model  # noqa: F401
