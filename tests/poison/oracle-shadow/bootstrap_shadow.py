# Loaded via `-p bootstrap_shadow` before collection starts (PYTHONPATH points at this
# directory), so `import _fragment` here primes sys.modules['_fragment'] with THIS
# directory's decoy before tests/laws/m1/test_l1_duckdb.py's bare `import _fragment as F`
# is ever reached. Whichever import runs first wins the sys.modules cache -- RT-M1-01.
import _fragment  # noqa: F401
