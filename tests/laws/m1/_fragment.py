"""The SQL-expressible fragment — the ORACLE half of law L1.16 (docs/specs/m1.md §10).

FROZEN at m1-laws-freeze, and frozen deliberately: this module holds the expression
catalogue, the data generators and the SQL renderer that L1.16 compares tannen against.
An oracle Session B could edit is not an oracle. `tests/laws` is a sealed directory
(governance/tier-c.yaml, D0056), so this is also the ONLY place M1's law files may share
anything: nothing can be added beside them later.

It imports NOTHING from tannen. The law module passes `ops`, the monoids and the Rel
constructor in, so this file cannot be the reason a pre-implementation run errors instead
of skipping.

The domain here is deliberately narrower than tannen's, and each narrowing is a place
tannen is WIDER than SQL rather than weaker (docs/specs/m1.md §10):

  * ints are drawn small so joins and groups actually match, with the declared bounds
    included as edge cases; the bound keeps every SUM inside BIGINT;
  * text is short, NFC by construction, from a small alphabet, so no collation or
    normalisation difference can be mistaken for an algebra difference;
  * no Decimal (DuckDB's DECIMAL has a precision ceiling tannen's has not), no None
    (SQL would read it as NULL), no nested values (no column image).
"""

from __future__ import annotations

from hypothesis import strategies as st

__all__ = [
    "ALPHABET",
    "COLUMN_TYPES",
    "DECLARED_INT_MAX",
    "DECLARED_INT_MIN",
    "MAX_MULTIPLICITY",
    "MAX_ROWS",
    "SHAPES",
    "SQL_TYPES",
    "TABLES",
    "Shape",
    "create_table_sql",
    "evaluate",
    "table_rows",
]

# --------------------------------------------------------------------------- domain

#: The declared bounds of the fragment's int column type (docs/specs/m1.md §10).
DECLARED_INT_MIN = -(2**31)
DECLARED_INT_MAX = 2**31 - 1

#: NFC by construction: every entry is already in normal form, so a mismatch here can
#: only be an algebra difference, never a normalisation one.
ALPHABET = ("", "a", "bb", "cc", "Z", "é")

MAX_ROWS = 6
MAX_MULTIPLICITY = 3

COLUMN_TYPES = {"f": "bool", "k": "int", "t": "text", "x": "int", "y": "int"}
SQL_TYPES = {"bool": "BOOLEAN", "int": "BIGINT", "text": "VARCHAR"}

#: Table name -> its SORTED schema. A Rel's schema is sorted, so these are too, and every
#: SELECT list below names its columns in the same sorted order — the comparison is then a
#: plain multiset equality with no column reshuffling to get wrong.
TABLES = {
    "a": ("k", "x"),
    "b": ("k", "y"),
    "c": ("k", "x"),  # union-compatible with `a`
    "d": ("f", "k", "t"),
}


def _value(column: str):
    kind = COLUMN_TYPES[column]
    if kind == "int":
        return st.one_of(
            st.integers(min_value=-4, max_value=4),  # collide often: real joins, real groups
            st.sampled_from([0, DECLARED_INT_MIN, DECLARED_INT_MAX]),
        )
    if kind == "text":
        return st.sampled_from(ALPHABET)
    return st.booleans()


def table_rows(table: str):
    """A strategy for `[(row, multiplicity), ...]` for one table of the fragment."""
    schema = TABLES[table]
    row = st.fixed_dictionaries({column: _value(column) for column in schema})
    return st.lists(
        st.tuples(row, st.integers(min_value=1, max_value=MAX_MULTIPLICITY)),
        max_size=MAX_ROWS,
    )


def create_table_sql(table: str) -> str:
    columns = ", ".join(f'"{c}" {SQL_TYPES[COLUMN_TYPES[c]]} NOT NULL' for c in TABLES[table])
    return f"CREATE OR REPLACE TABLE {table} ({columns})"


# --------------------------------------------------------------------------- the plans

# A plan is a tuple tree. `evaluate` is its only interpreter, and it is ~20 lines, so the
# oracle's own machinery stays small enough to read in one sitting.
#
#   ("src", name)
#   ("select", plan, predicate_key)
#   ("project", plan, columns)
#   ("union", left, right)
#   ("join", left, right, on)
#   ("distinct", plan)
#   ("anti_join", left, right, on)
#   ("aggregate", plan, by, monoid_key, value_column_or_None, into)

#: Predicates, as (tannen callable, SQL text). The closed grammar of docs/specs/m1.md §10:
#: `col {=,<>,<,>} literal` combined with AND / OR / NOT. Every operand is NOT NULL, so
#: SQL's three-valued logic never engages.
PREDICATES = {
    "x-positive": (lambda r: r["x"] > 0, "x > 0"),
    "x-positive-and-k-nonzero": (lambda r: r["x"] > 0 and r["k"] != 0, "x > 0 AND k <> 0"),
    "not-x-negative-or-k-one": (lambda r: (not (r["x"] < 0)) or r["k"] == 1, "NOT (x < 0) OR k = 1"),
    "t-is-a": (lambda r: r["t"] == "a", "t = 'a'"),
}


class Shape:
    """One expression of the fragment: a plan, its SQL, and its sorted out-schema."""

    __slots__ = ("name", "plan", "sql", "columns")

    def __init__(self, name: str, plan: tuple, sql: str, columns: tuple[str, ...]) -> None:
        assert tuple(sorted(columns)) == columns, f"{name}: out-schema must be sorted"
        self.name, self.plan, self.sql, self.columns = name, plan, sql, columns

    def __repr__(self) -> str:  # pragma: no cover - test ids use .name
        return f"Shape({self.name!r})"


A = ("src", "a")
B = ("src", "b")
C = ("src", "c")
D = ("src", "d")

SHAPES = (
    Shape("select-gt", ("select", A, "x-positive"),
          "SELECT k, x FROM a WHERE x > 0", ("k", "x")),
    Shape("select-and", ("select", A, "x-positive-and-k-nonzero"),
          "SELECT k, x FROM a WHERE x > 0 AND k <> 0", ("k", "x")),
    Shape("select-or-not", ("select", A, "not-x-negative-or-k-one"),
          "SELECT k, x FROM a WHERE NOT (x < 0) OR k = 1", ("k", "x")),
    Shape("select-text", ("select", D, "t-is-a"),
          "SELECT f, k, t FROM d WHERE t = 'a'", ("f", "k", "t")),
    Shape("project-one", ("project", A, ("k",)),
          "SELECT k FROM a", ("k",)),
    Shape("project-two", ("project", D, ("f", "t")),
          "SELECT f, t FROM d", ("f", "t")),
    Shape("union", ("union", A, C),
          "SELECT k, x FROM a UNION ALL SELECT k, x FROM c", ("k", "x")),
    Shape("union-of-selects",
          ("union", ("select", A, "x-positive"), ("select", C, "x-positive")),
          "SELECT k, x FROM a WHERE x > 0 UNION ALL SELECT k, x FROM c WHERE x > 0", ("k", "x")),
    Shape("union-then-distinct", ("distinct", ("union", A, C)),
          "SELECT DISTINCT k, x FROM (SELECT k, x FROM a UNION ALL SELECT k, x FROM c)",
          ("k", "x")),
    Shape("join", ("join", A, B, ("k",)),
          "SELECT k, x, y FROM a INNER JOIN b USING (k)", ("k", "x", "y")),
    Shape("join-then-project", ("project", ("join", A, B, ("k",)), ("y",)),
          "SELECT y FROM a INNER JOIN b USING (k)", ("y",)),
    Shape("join-then-distinct", ("distinct", ("join", A, B, ("k",))),
          "SELECT DISTINCT k, x, y FROM a INNER JOIN b USING (k)", ("k", "x", "y")),
    Shape("join-text", ("join", D, A, ("k",)),
          "SELECT f, k, t, x FROM d INNER JOIN a USING (k)", ("f", "k", "t", "x")),
    Shape("distinct", ("distinct", A),
          "SELECT DISTINCT k, x FROM a", ("k", "x")),
    Shape("project-then-distinct", ("distinct", ("project", A, ("k",))),
          "SELECT DISTINCT k FROM (SELECT k FROM a)", ("k",)),
    Shape("anti-join", ("anti_join", A, B, ("k",)),
          "SELECT k, x FROM a WHERE NOT EXISTS (SELECT 1 FROM b WHERE b.k = a.k)", ("k", "x")),
    Shape("anti-join-then-project", ("project", ("anti_join", A, B, ("k",)), ("x",)),
          "SELECT x FROM a WHERE NOT EXISTS (SELECT 1 FROM b WHERE b.k = a.k)", ("x",)),
    Shape("aggregate-sum", ("aggregate", A, ("k",), "sum", "x", "s"),
          "SELECT k, SUM(x) AS s FROM a GROUP BY k", ("k", "s")),
    Shape("aggregate-count", ("aggregate", A, ("k",), "count", None, "s"),
          "SELECT k, COUNT(*) AS s FROM a GROUP BY k", ("k", "s")),
    Shape("aggregate-of-join", ("aggregate", ("join", A, B, ("k",)), ("k",), "sum", "y", "s"),
          "SELECT k, SUM(y) AS s FROM a INNER JOIN b USING (k) GROUP BY k", ("k", "s")),
    Shape("aggregate-of-distinct", ("aggregate", ("distinct", A), ("k",), "sum", "x", "s"),
          "SELECT k, SUM(x) AS s FROM (SELECT DISTINCT k, x FROM a) GROUP BY k", ("k", "s")),
    Shape("aggregate-two-keys", ("aggregate", D, ("f", "k"), "count", None, "s"),
          "SELECT f, k, COUNT(*) AS s FROM d GROUP BY f, k", ("f", "k", "s")),
)


def evaluate(plan: tuple, rels: dict, ops, monoids: dict):
    """Interpret a plan with tannen's operators. `rels` maps table name -> Rel.

    Every step is unwrapped, so a Quarantine surfaces here — where the plan that produced
    it is still in the traceback — rather than as a mismatch three operators later.
    """
    head = plan[0]
    if head == "src":
        return rels[plan[1]]
    if head == "select":
        predicate, _ = PREDICATES[plan[2]]
        return ops.select(evaluate(plan[1], rels, ops, monoids), predicate).unwrap()
    if head == "project":
        return ops.project(evaluate(plan[1], rels, ops, monoids), plan[2]).unwrap()
    if head == "union":
        return ops.union(
            evaluate(plan[1], rels, ops, monoids), evaluate(plan[2], rels, ops, monoids)
        ).unwrap()
    if head == "join":
        return ops.join(
            evaluate(plan[1], rels, ops, monoids), evaluate(plan[2], rels, ops, monoids), plan[3]
        ).unwrap()
    if head == "distinct":
        return ops.distinct(evaluate(plan[1], rels, ops, monoids)).unwrap()
    if head == "anti_join":
        return ops.anti_join(
            evaluate(plan[1], rels, ops, monoids), evaluate(plan[2], rels, ops, monoids), plan[3]
        ).unwrap()
    if head == "aggregate":
        _, source, by, monoid_key, value_column, into = plan
        value_of = (lambda row: 1) if value_column is None else (lambda row: row[value_column])
        return ops.aggregate(
            evaluate(source, rels, ops, monoids), by, monoids[monoid_key], value_of, into
        ).unwrap()
    raise AssertionError(f"not a plan node: {head!r}")
