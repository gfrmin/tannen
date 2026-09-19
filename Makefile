# tannen — governance targets. `make verify` is the session-closing gate (CLAUDE.md).
# `uv run tannen laws report` joined `verify` at M0, as decision D0012 said it would.
# Order is load-bearing: pytest runs the laws and emits their evidence records, then
# the report judges that evidence against the current descriptors. pytest now also
# runs BEFORE check_decisions.py, which reads its --junitxml report instead of
# spawning a second pytest over the same bound nodes (D0266 item 2).

.PHONY: verify projections digest drift laws-sweep

drift:
	$(PY) -I -P scripts/check_drift.py --file-records

# The gate controls its own environment. Two red-team findings live here:
#   RT-08 — TANNEN_CHECK_DECISIONS_NESTED inherited from the ambient environment turns
#           off all pytest-binding resolution while the guard still prints "green".
#           `env -u` removes the accidental case entirely (an exported variable, a shell
#           profile) and makes the deliberate case a visible diff in this file.
#   RT-05 — evidence records are content-addressed but unauthenticated, so a stale or
#           prepared evidence/ makes `tannen laws report` green for code this run never
#           exercised. The gate runs pytest and the report against a FRESHLY REMOVED
#           store, so the report can only see records the gate's own run produced.
#   RT-02 (resolution) — the custody set covers the guards' CODE; what resolved them was
#           `uv run`, which reads builder-controlled metadata, and PYTHONPATH, which reads
#           the ambient environment. The floor may depend only on tools the OS provides and
#           paths named literally (conferral ruling 3, D0063), so every guard below is the
#           venv interpreter at a literal path, in isolated mode: -I ignores PYTHONPATH,
#           PYTHONHOME and user site-packages; -P stops any directory being prepended to
#           sys.path implicitly. Each guard names its own directory from __file__ instead.
#           What this does NOT remove: site-packages itself is still builder-controlled.
VERIFY_EVIDENCE := $(CURDIR)/.verify-evidence
UNHATCH := env -u TANNEN_CHECK_DECISIONS_NESTED
PY := $(CURDIR)/.venv/bin/python

# The M5 vertical lives at .dogfood/ (gitignored, D0265), named by module stem. pytest
# needs it on sys.path both in this process (dogfood.run imports it) and in L5.10's fresh
# child interpreters (they inherit os.environ, not sys.path), hence PYTHONPATH. But never
# .dogfood/ itself: every file there would join the interpreter, and a sitecustomize.py
# beside the pipeline rewrote L5.9's failure into a pass (RT-M5-01). The gate stages the
# ONE module corpus.json names into a fresh directory, and unsets the variables that load
# pytest plugins or options from the environment. Empty when .dogfood/ is absent (CI).
DOGFOOD_STAGE := $(VERIFY_EVIDENCE)/pipeline
DOGFOOD_ENV := env -u PYTEST_PLUGINS -u PYTEST_ADDOPTS -u PYTHONSTARTUP PYTHONPATH=$(DOGFOOD_STAGE)

verify:
	rm -rf $(VERIFY_EVIDENCE)
	@test -x $(PY) || { echo "no interpreter at $(PY) — run 'uv sync --frozen'"; exit 1; }
	$(UNHATCH) $(PY) -I -P scripts/check_manifest.py
	$(UNHATCH) $(PY) -I -P scripts/check_concepts.py
	$(UNHATCH) $(PY) -I -P scripts/stage_dogfood.py $(DOGFOOD_STAGE)
	$(UNHATCH) $(DOGFOOD_ENV) TANNEN_EVIDENCE_ROOT=$(VERIFY_EVIDENCE) uv run pytest -q --junitxml=$(VERIFY_EVIDENCE)/pytest-report.xml
	$(UNHATCH) $(PY) -I -P scripts/check_decisions.py --pytest-report $(VERIFY_EVIDENCE)/pytest-report.xml
	$(UNHATCH) $(PY) -I -P scripts/check_tag_signers.py
	$(UNHATCH) $(PY) -I -P scripts/check_receipts.py
	$(UNHATCH) $(PY) -I -P scripts/check_laws.py
	$(UNHATCH) $(PY) -I -P scripts/check_doorway.py
	$(UNHATCH) env TANNEN_EVIDENCE_ROOT=$(VERIFY_EVIDENCE) uv run tannen laws report
	$(UNHATCH) $(PY) -I -P -c 'import sys; from importlinter.cli import lint_imports_command; sys.exit(lint_imports_command())' --config governance/importlinter.toml
	$(UNHATCH) bash scripts/custodian.sh --check-only
	rm -rf $(VERIFY_EVIDENCE)

projections:
	$(PY) -I -P scripts/gen_projections.py
	$(PY) -I -P scripts/gen_roadmap.py

digest:
	$(PY) -I -P scripts/gen_projections.py --digest

# A random-seed sweep: derandomised runs make evidence reproducible, this hunts for
# counterexamples the fixed examples never reach. The seed is recorded in every
# record the run emits, so a failure found here is replayable from the record.
laws-sweep:
	$(PY) -I -P scripts/stage_dogfood.py $(DOGFOOD_STAGE)
	$(DOGFOOD_ENV) uv run pytest tests/laws -q --hypothesis-seed=$${SEED:-$$RANDOM}
