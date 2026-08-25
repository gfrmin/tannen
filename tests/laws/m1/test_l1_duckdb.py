"""M1 law L1.16 — differential correctness against DuckDB. This is BRIEF §6's **L6**,
and M1's KILL CRITERION (docs/specs/m1.md §10).

FROZEN at m1-laws-freeze.

BRIEF §8: "kill: flaky L6 ⇒ fix encoding before anything else". "Flaky" includes any
failure here that does not reproduce under the derandomised profile. The response is
never to loosen the comparison, re-seed, or narrow the generator — it is to find what the
canonical form or the no-NULL mapping gets wrong. `golden-rels.json` and law L1.4 exist so
that this failure has somewhere smaller to be found than a random graph.

`duckdb` is imported directly, NOT through `importorskip`: an absent differential oracle
must be a loud collection error, never a silent skip that reads as a pass. It is pinned
exactly in `pyproject.toml` (decision D0079) — L6 compares tannen against THIS DuckDB, so
an unpinned range would let an upgrade change the oracle underneath a frozen law.
"""

from __future__ import annotations

import operator

import duckdb
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

ops = pytest.importorskip(
    "tannen.kernel.ops",
    reason="M1 operators not implemented yet (law suite frozen ahead of Session B)",
)
rel_mod = pytest.importorskip("tannen.kernel.rel")
semiring = pytest.importorskip("tannen.kernel.semiring")
algebra = pytest.importorskip("tannen.kernel.algebra")

import _fragment as F  # noqa: E402  (the oracle half, frozen beside this file)

Rel = rel_mod.Rel
Z, Why, ZxWhy = semiring.Z, semiring.Why, semiring.ZxWhy
WHY = "L6 runs the same graph under Z_ONLY and the default; SQL has no support-set image"
R1 = "sha256:" + "11" * 32

MONOIDS = {
    "sum": algebra.Monoid("sum-int", operator.add, 0, (-3, -1, 0, 1, 2, 5)),
    "count": algebra.Monoid("count", operator.add, 0, (0, 1, 2, 5)),
}


def _annotate(S, n: int):
    return (n, Why.of({R1})) if S.name == "Z*Why" else n


def _rel(table: str, pairs, S):
    rows = [(row, _annotate(S, n)) for row, n in pairs]
    if S.name == rel_mod.DEFAULT_ANNOTATIONS.name:
        return Rel(F.TABLES[table], rows)
    return Rel(F.TABLES[table], rows, annotations=semiring.Z_ONLY, annotations_reason=WHY)


def _sort_key(row: tuple):
    # Tuples here mix int, str and bool, which are not mutually orderable in Python.
    # Sorting by (type name, value) is total and is only ever used to compare two
    # multisets of the same shape against each other.
    return [(type(value).__name__, value) for value in row]


def _load(connection, name: str, rel) -> None:
    connection.execute(F.create_table_sql(name))
    bag = rel.to_bag()
    if bag:
        placeholders = ", ".join(["?"] * len(F.TABLES[name]))
        connection.executemany(f"INSERT INTO {name} VALUES ({placeholders})", bag)


@pytest.fixture()
def connection():
    with duckdb.connect() as handle:
        # Integer sums are order-independent, so this changes no answer; it removes a
        # source of run-to-run variation from the oracle, which is what the kill criterion
        # is about (docs/specs/m1.md §10).
        handle.execute("SET threads TO 1")
        yield handle


@pytest.mark.parametrize("shape", F.SHAPES, ids=[shape.name for shape in F.SHAPES])
@pytest.mark.parametrize("S", [None, "Z"], ids=["Z*Why", "Z_ONLY"])
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.data())
def test_l1_16_the_fragment_agrees_with_duckdb(connection, shape, S, data) -> None:
    annotations = ZxWhy if S is None else Z
    rels = {
        name: _rel(name, data.draw(F.table_rows(name)), annotations) for name in F.TABLES
    }
    for name, rel in rels.items():
        _load(connection, name, rel)

    result = F.evaluate(shape.plan, rels, ops, MONOIDS)
    assert result.schema == shape.columns, (
        f"{shape.name}: tannen's out-schema {result.schema} is not the sorted schema the "
        f"SQL selects, {shape.columns} — the comparison below would be meaningless"
    )

    mine = sorted(result.to_bag(), key=_sort_key)
    theirs = sorted(connection.execute(shape.sql).fetchall(), key=_sort_key)
    assert mine == theirs, (
        f"{shape.name} under {annotations.name}\n  SQL: {shape.sql}\n"
        f"  tannen: {mine}\n  duckdb: {theirs}"
    )


@pytest.mark.parametrize("shape", F.SHAPES, ids=[shape.name for shape in F.SHAPES])
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.data())
def test_l1_16_no_null_ever_appears_on_either_side(connection, shape, data) -> None:
    # The no-NULL mapping is the content of the comparison (BRIEF §6 requires it explicit).
    # Every column is NOT NULL and `aggregate` refuses an empty `by`, so SQL has no way to
    # invent one — and if it ever does, that is the finding, not a nuisance.
    rels = {name: _rel(name, data.draw(F.table_rows(name)), ZxWhy) for name in F.TABLES}
    for name, rel in rels.items():
        _load(connection, name, rel)

    for row in connection.execute(shape.sql).fetchall():
        assert None not in row, f"{shape.name}: DuckDB produced a NULL: {row}"
    for row, _ in F.evaluate(shape.plan, rels, ops, MONOIDS):
        assert None not in row.values(), f"{shape.name}: tannen produced a None: {row}"


def test_l1_16_the_catalogue_covers_every_operator_of_the_fragment() -> None:
    # A shape catalogue that quietly stopped exercising an operator would leave that
    # operator with no differential evidence while the law still read green.
    covered: set[str] = set()

    def walk(plan):
        head = plan[0]
        if head == "src":
            return
        covered.add(head)
        for part in plan[1:]:
            if isinstance(part, tuple) and part and isinstance(part[0], str) and part[0] in {
                "src", "select", "project", "union", "join", "distinct", "anti_join", "aggregate"
            }:
                walk(part)

    for shape in F.SHAPES:
        walk(shape.plan)
    assert covered == {"select", "project", "union", "join", "distinct", "anti_join", "aggregate"}
    # `map_rows` is excluded BY NAME: an arbitrary Python function has no SQL image.
    assert "map_rows" not in covered


def test_l1_16_the_declared_int_bounds_stay_inside_duckdbs_bigint(connection) -> None:
    for value in (F.DECLARED_INT_MIN, F.DECLARED_INT_MAX):
        (returned,), = connection.execute("SELECT ?::BIGINT", [value]).fetchall()
        assert returned == value
