# tannen — governance targets. `make verify` is the session-closing gate (CLAUDE.md).
# `uv run tannen laws report` joined `verify` at M0, as decision D0012 said it would.
# Order is load-bearing: pytest runs the laws and emits their evidence records, then
# the report judges that evidence against the current descriptors.

.PHONY: verify projections digest drift laws-sweep

drift:
	uv run python scripts/check_drift.py --file-records

verify:
	uv run python scripts/check_manifest.py
	uv run python scripts/check_concepts.py
	uv run python scripts/check_decisions.py
	uv run pytest -q
	uv run tannen laws report
	uv run lint-imports
	bash scripts/custodian.sh --check-only

projections:
	uv run python scripts/gen_projections.py

digest:
	uv run python scripts/gen_projections.py --digest

# A random-seed sweep: derandomised runs make evidence reproducible, this hunts for
# counterexamples the fixed examples never reach. The seed is recorded in every
# record the run emits, so a failure found here is replayable from the record.
laws-sweep:
	uv run pytest tests/laws -q --hypothesis-seed=$${SEED:-$$RANDOM}
