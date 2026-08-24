# tannen — governance targets. `make verify` is the session-closing gate (CLAUDE.md).
# `uv run tannen laws report` joined `verify` at M0, as decision D0012 said it would.
# Order is load-bearing: pytest runs the laws and emits their evidence records, then
# the report judges that evidence against the current descriptors.

.PHONY: verify projections digest drift laws-sweep

drift:
	uv run python scripts/check_drift.py --file-records

# The gate controls its own environment. Two red-team findings live here:
#   RT-08 — TANNEN_CHECK_DECISIONS_NESTED inherited from the ambient environment turns
#           off all pytest-binding resolution while the guard still prints "green".
#           `env -u` removes the accidental case entirely (an exported variable, a shell
#           profile) and makes the deliberate case a visible diff in this file.
#   RT-05 — evidence records are content-addressed but unauthenticated, so a stale or
#           prepared evidence/ makes `tannen laws report` green for code this run never
#           exercised. The gate runs pytest and the report against a FRESHLY REMOVED
#           store, so the report can only see records the gate's own run produced.
VERIFY_EVIDENCE := $(CURDIR)/.verify-evidence
UNHATCH := env -u TANNEN_CHECK_DECISIONS_NESTED

verify:
	rm -rf $(VERIFY_EVIDENCE)
	$(UNHATCH) uv run python scripts/check_manifest.py
	$(UNHATCH) uv run python scripts/check_concepts.py
	$(UNHATCH) uv run python scripts/check_decisions.py
	$(UNHATCH) uv run python scripts/check_tag_signers.py
	$(UNHATCH) env TANNEN_EVIDENCE_ROOT=$(VERIFY_EVIDENCE) uv run pytest -q
	$(UNHATCH) env TANNEN_EVIDENCE_ROOT=$(VERIFY_EVIDENCE) uv run tannen laws report
	$(UNHATCH) uv run lint-imports
	$(UNHATCH) bash scripts/custodian.sh --check-only
	rm -rf $(VERIFY_EVIDENCE)

projections:
	uv run python scripts/gen_projections.py

digest:
	uv run python scripts/gen_projections.py --digest

# A random-seed sweep: derandomised runs make evidence reproducible, this hunts for
# counterexamples the fixed examples never reach. The seed is recorded in every
# record the run emits, so a failure found here is replayable from the record.
laws-sweep:
	uv run pytest tests/laws -q --hypothesis-seed=$${SEED:-$$RANDOM}
