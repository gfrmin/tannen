# tannen — governance targets. `make verify` is the session-closing gate (CLAUDE.md).
# `uv run tannen laws report` joins `verify` at M0, when the CLI and the first frozen
# law set exist (decision D0012).

.PHONY: verify projections digest drift

drift:
	uv run python scripts/check_drift.py --file-records

verify:
	uv run python scripts/check_manifest.py
	uv run python scripts/check_concepts.py
	uv run python scripts/check_decisions.py
	uv run pytest -q
	uv run lint-imports
	bash scripts/custodian.sh --check-only

projections:
	uv run python scripts/gen_projections.py

digest:
	uv run python scripts/gen_projections.py --digest
