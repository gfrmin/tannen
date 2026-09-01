# Loaded via `-p bootstrap_shadow_model` before collection starts (PYTHONPATH points at this
# directory), so `import _model` here primes sys.modules['_model'] with THIS
# directory's decoy before tests/laws/m2/test_l2_differential.py's bare `import _model as M`
# is ever reached. Whichever import runs first wins the sys.modules cache -- RT-M2-01.
import _model  # noqa: F401
