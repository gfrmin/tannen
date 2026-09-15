"""The MODEL half of M5's laws — the frozen oracle (docs/specs/m5.md §10).

FROZEN at m5-laws-freeze, for D0094's reason: under the frozen-oracle protocol every law is a
skip at exactly the moment it becomes unrewritable — at M5 more so than ever, because every M5
law skips until an authorised corpus exists (docs/specs/m5.md §8), so `pytest tests/laws/m5`
prints "skipped" in CI for good. A model beside the laws is what turns this freeze from "the
laws do not run" into "the laws pass against a transcription of the spec and fail against a
stated mutant", and `tests/test_law_validation.py` runs that matrix at every commit.

It imports NOTHING from tannen (D0089) and uses no dataclasses (it is loaded by file location
under names absent from `sys.modules`). Nobody imports it by its bare name: M5 law files reach
it through `_dogfood_bind.m5()`.

Three families, one per mechanism a Session B could get subtly wrong:

  check_clamp       `tannen run` spends only against the checked-in budget.yaml unless
                    `--budget-override` names another file (§6; D0240 item (2), D0241).
  check_selection   the M5 vertical is the eligible source minimising parser LOC × distinct
                    operators, ties broken by operators then source id (§2; BRIEF §8).
  check_comparator  byte identity, never normalised: one `divergence/1` per differing item,
                    none for an identical one, and an incomplete run refused (§4, §5).

Generators follow D0118: the cases that matter are NAMED and run before any draw, and every
draw reports its shape through hypothesis `event()`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hypothesis import event, strategies as st

__all__ = [
    "BIG", "CATALOGUE", "CAUGHT_BY", "CLAMP_SCENARIOS", "COMPARATOR_CASES", "FAMILIES",
    "FLAGS", "MODEL", "MUTANTS", "REFUSED", "REQUIRED", "SELECTION_CASES", "Subject",
    "check_clamp", "check_comparator", "check_selection", "expected_cli", "expected_selection",
    "first_difference", "run_family", "schema", "vector_paths",
]

_HERE = Path(__file__).resolve().parent

#: A ceiling large enough that one zero-priced clock read always fits it.
BIG = 10**6

#: The catalogue the MODEL selects against — a transcription of docs/specs/m1.md §4's eight
#: names. The tannen subject answers with `tannen.kernel.ops.OPERATORS` itself, and L5.4 asserts
#: that identity, so the law's catalogue is derived from the package, never listed there.
CATALOGUE = ("select", "project", "map_rows", "union", "join", "distinct", "anti_join",
             "aggregate")

#: How a `tannen run` names its budget (§6). `budget-checked-in` is `--budget` pointed at the
#: repository's own budget.yaml, which is not an override.
FLAGS = (None, "budget-checked-in", "budget-other", "override-other", "both")

REFUSED = "refused"


class ModelRefusal(Exception):
    """Base of every refusal the model raises by name."""


class SelectionRefusal(ModelRefusal):
    """A measurement no rule can select from: no eligible candidate, an operator outside the
    catalogue, or one source measured twice."""


class IncompleteRunRefusal(ModelRefusal):
    """Outputs that do not answer exactly the corpus's items."""


# ------------------------------------------------------------------------ the rules


def expected_cli(spend: bool, flag: str | None, checked_in: int, other: int) -> dict:
    """What `tannen run` must do, PREDICTED from §6 rather than read off any implementation.

    `names` are substrings stderr must carry. Both budget flags together are a usage error.
    Without `--spend` neither flag is consulted, so replay-only refuses a novel invocation
    exactly as L4.4 froze. Under `--spend`, a `--budget` naming any file but the checked-in
    one is refused as `SpendDenied`, naming `--budget-override`, before the transport; every
    other spelling admits iff its budget's ceiling is nonzero (L4.5: a zero ceiling refuses
    even a zero-priced call)."""
    if flag == "both":
        return {"code": 2, "names": (), "calls": 0}
    if not spend:
        return {"code": 1, "names": ("NovelInvocationRefused",), "calls": 0}
    if flag == "budget-other":
        return {"code": 1, "names": ("SpendDenied", "--budget-override"), "calls": 0}
    ceiling = other if flag == "override-other" else checked_in
    if ceiling > 0:
        return {"code": 0, "names": (), "calls": 1}
    return {"code": 1, "names": ("SpendDenied",), "calls": 0}


def expected_selection(measurement: dict, catalogue: tuple) -> str:
    """§2: refuse a repeated source or an operator outside the catalogue (in ANY candidate,
    eligible or not — a measurement that names a nonexistent operator is wrong as a whole);
    among candidates with a visible export, minimise (parser_loc × distinct operators, distinct
    operators, source id as UTF-8 bytes); refuse when none is eligible."""
    candidates = measurement["candidates"]
    sources = [c["source"] for c in candidates]
    if len(set(sources)) != len(sources):
        return REFUSED
    if any(op not in catalogue for c in candidates for op in c["operators"]):
        return REFUSED
    eligible = [c for c in candidates if c["visible_export"]]
    if not eligible:
        return REFUSED
    best = min(eligible, key=lambda c: (c["parser_loc"] * len(set(c["operators"])),
                                        len(set(c["operators"])), c["source"].encode("utf-8")))
    return best["source"]


def first_difference(a: bytes, b: bytes) -> int | None:
    """The first index at which two byte strings differ; the shorter length when one is a
    proper prefix of the other; None when they are identical."""
    if a == b:
        return None
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def _ref(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------------ the subject


class Subject:
    """What a law needs of an implementation. Fine-grained hooks, so a mutant breaks one
    mechanism without forging the rest."""

    name = "model"
    selection_refused = SelectionRefusal
    incomplete_run = IncompleteRunRefusal
    catalogue = CATALOGUE

    # -- the clamp (§6)
    def budget_for(self, flag: str | None, checked_in: int, other: int) -> Any:
        if flag == "budget-other":
            return REFUSED
        return other if flag == "override-other" else checked_in

    def run_cli(self, spend: bool, flag: str | None, checked_in: int, other: int) -> list[dict]:
        """Run the scenario, then a plain replay (no flag, no `--spend`) over the same store.
        Each outcome: exit code, stderr, cumulative transport calls, whether the store holds
        anything."""
        calls, wrote = 0, False
        if flag == "both":
            first = {"code": 2, "stderr": "usage: --budget and --budget-override exclude each other"}
        elif not spend:
            first = {"code": 1, "stderr": "NovelInvocationRefused: replay-only"}
        else:
            ceiling = self.budget_for(flag, checked_in, other)
            if ceiling == REFUSED:
                first = {"code": 1, "stderr": "SpendDenied: --budget names a file other than "
                                              "the checked-in budget.yaml; spending against it "
                                              "requires --budget-override"}
            elif ceiling > 0:
                calls, wrote = 1, True
                first = {"code": 0, "stderr": ""}
            else:
                first = {"code": 1, "stderr": "SpendDenied: zero ceiling"}
        first.update(calls=calls, wrote=wrote)
        replay = ({"code": 0, "stderr": ""} if wrote
                  else {"code": 1, "stderr": "NovelInvocationRefused: replay-only"})
        replay.update(calls=calls, wrote=wrote)
        return [first, replay]

    # -- selection (§2)
    def select(self, measurement: dict) -> str:
        chosen = expected_selection(measurement, self.catalogue)
        if chosen == REFUSED:
            raise SelectionRefusal("no rule selects from this measurement")
        return chosen

    # -- the comparator (§4, §5)
    def ref_of(self, data: bytes) -> str:
        return _ref(data)

    def same(self, a: bytes, b: bytes) -> bool:
        return a == b

    def offset(self, a: bytes, b: bytes) -> int:
        return first_difference(a, b)

    def items_compared(self, items: list) -> list:
        return items

    def compare_cases(self, cases: list, omit: str | None = None) -> list[dict]:
        """`cases` is [(item id, production bytes, tannen bytes)]; `omit` drops one item's
        tannen output so the run is incomplete."""
        items = [{"id": i, "input": _ref(b"input:" + i.encode()), "production_output": _ref(p)}
                 for i, p, _t in cases]
        outputs = {i: t for i, _p, t in cases if i != omit}
        if set(outputs) != {item["id"] for item in items}:
            raise IncompleteRunRefusal("outputs do not answer exactly the corpus's items")
        production = {i: p for i, p, _t in cases}
        found = []
        for item in self.items_compared(items):
            tannen, prod = outputs[item["id"]], production[item["id"]]
            if self.same(tannen, prod):
                continue
            found.append({"tannen": "divergence/1", "item": item["id"], "input": item["input"],
                          "tannen_output": _ref(tannen), "production_output": _ref(prod),
                          "offset": self.offset(tannen, prod), "classification": "unanalysed",
                          "analysis": "", "evidence": []})
        return found


#: Exactly what a check calls on a subject. `_dogfood_subject.py` asserts the tannen adapter
#: defines EVERY name here in its own `__dict__` — no subclassing, no silent fallback.
REQUIRED = ("name", "selection_refused", "incomplete_run", "catalogue",
            "run_cli", "select", "ref_of", "compare_cases")

MODEL = Subject()


# ------------------------------------------------------------------------ the checks


def check_clamp(subject: Subject, scenario: tuple) -> None:
    """L5.1. The first outcome matches the §6 prediction — exit code, the names on stderr, the
    transport count, and whether anything was written — and a plain replay afterwards serves
    exactly what the first run captured, with no further call."""
    spend, flag, checked_in, other = scenario
    want = expected_cli(spend, flag, checked_in, other)
    first, replay = subject.run_cli(spend, flag, checked_in, other)
    label = f"spend={spend} flag={flag} checked_in={checked_in} other={other}"
    assert first["code"] == want["code"], f"{label}: exit {first['code']}, want {want['code']}\n" \
                                          f"{first['stderr']}"
    for name in want["names"]:
        assert name in first["stderr"], f"{label}: stderr does not name {name}: {first['stderr']}"
    assert first["calls"] == want["calls"], (
        f"{label}: the transport was reached {first['calls']} time(s), want {want['calls']} — a "
        "refusal after the call has already spent")
    assert first["wrote"] == (want["code"] == 0), f"{label}: a refused run wrote to the store"
    if want["code"] == 0:
        assert replay["code"] == 0 and replay["calls"] == want["calls"], (
            f"{label}: a capture made under --spend did not replay without it, or the replay "
            "reached the transport")
    else:
        assert replay["code"] == 1 and "NovelInvocationRefused" in replay["stderr"], (
            f"{label}: a replay after a refusal found something to serve")
        assert replay["calls"] == 0, f"{label}: the replay reached the transport"


def check_selection(subject: Subject, measurement: dict) -> None:
    """L5.4: the subject selects exactly what the §2 rule predicts, or refuses by name."""
    want = expected_selection(measurement, subject.catalogue)
    try:
        got = subject.select(measurement)
    except subject.selection_refused:
        got = REFUSED
    assert got == want, f"selected {got!r}, the rule selects {want!r}: {measurement}"


def check_comparator(subject: Subject, cases: list) -> None:
    """L5.7. One unanalysed `divergence/1` per differing item, in corpus order, naming the refs
    and the first differing offset; none for an identical item; every value valid against the
    frozen schema; and a run missing an item's output refused by name."""
    import jsonschema

    found = subject.compare_cases(cases)
    want = [(i, first_difference(t, p), subject.ref_of(t), subject.ref_of(p))
            for i, p, t in cases if t != p]
    got = [(d["item"], d["offset"], d["tannen_output"], d["production_output"]) for d in found]
    assert got == want, f"divergences {got}, want {want} over {cases}"
    validator = jsonschema.Draft202012Validator(schema("divergence"))
    for value in found:
        validator.validate(value)
        assert value["classification"] == "unanalysed" and value["analysis"] == "", (
            "the comparator analysed a divergence itself — analysis is a separate act (§5)")
    if cases:
        try:
            subject.compare_cases(cases, omit=cases[-1][0])
        except subject.incomplete_run:
            pass
        else:
            raise AssertionError("a run missing an item's output was compared as if complete")


# ------------------------------------------------------------------------ mutants


class _BudgetAsGiven(Subject):
    """The unclamped CLI M4 shipped: `--budget` is honoured as given."""
    name = "budget-as-given"

    def budget_for(self, flag, checked_in, other):
        return other if flag in ("budget-other", "override-other") else checked_in


class _OverrideIgnored(Subject):
    """A clamp so tight that `--budget-override` falls back to the checked-in file."""
    name = "override-ignored"

    def budget_for(self, flag, checked_in, other):
        return REFUSED if flag == "budget-other" else checked_in


class _ClampWithoutSpend(Subject):
    """The clamp consulted in replay mode too — which breaks L4.4's first node."""
    name = "clamp-without-spend"

    def run_cli(self, spend, flag, checked_in, other):
        if not spend and flag == "budget-other":
            out = {"code": 1, "stderr": "SpendDenied: requires --budget-override", "calls": 0,
                   "wrote": False}
            return [out, dict(out, stderr="NovelInvocationRefused: replay-only")]
        return super().run_cli(spend, flag, checked_in, other)


class _RefuseAfterCall(Subject):
    """The clamp checked after the pipeline already invoked its oracle."""
    name = "refuse-after-call"

    def run_cli(self, spend, flag, checked_in, other):
        outcomes = super().run_cli(spend, flag, checked_in, other)
        if spend and flag == "budget-other":
            outcomes[0].update(calls=1, wrote=True)
        return outcomes


class _VisibilityIgnored(Subject):
    """Selects among every candidate, exported or not."""
    name = "visibility-ignored"

    def select(self, measurement):
        everyone = {**measurement, "candidates": [dict(c, visible_export=True)
                                                   for c in measurement["candidates"]]}
        return super().select(everyone)


class _SumNotProduct(Subject):
    """LOC + operators instead of LOC × operators."""
    name = "sum-not-product"

    def select(self, measurement):
        if expected_selection(measurement, self.catalogue) == REFUSED:
            raise SelectionRefusal("refused")
        eligible = [c for c in measurement["candidates"] if c["visible_export"]]
        return min(eligible, key=lambda c: (c["parser_loc"] + len(c["operators"]),
                                            len(c["operators"]), c["source"].encode()))["source"]


class _TiebreakPrefersOperators(Subject):
    """On a product tie, prefers MORE operators."""
    name = "tiebreak-prefers-operators"

    def select(self, measurement):
        if expected_selection(measurement, self.catalogue) == REFUSED:
            raise SelectionRefusal("refused")
        eligible = [c for c in measurement["candidates"] if c["visible_export"]]
        return min(eligible, key=lambda c: (c["parser_loc"] * len(c["operators"]),
                                            -len(c["operators"]), c["source"].encode()))["source"]


class _NormaliseBeforeCompare(Subject):
    """Trailing whitespace forgiven — the comparison byte identity forbids."""
    name = "normalise-before-compare"

    def same(self, a, b):
        return a.rstrip() == b.rstrip()


class _ItemDropped(Subject):
    """The last corpus item never compared."""
    name = "item-dropped"

    def items_compared(self, items):
        return items[:-1]


class _OffsetOffByOne(Subject):
    """The offset one past the first differing byte."""
    name = "offset-off-by-one"

    def offset(self, a, b):
        return first_difference(a, b) + 1


MUTANTS = {m.name: m for m in (
    _BudgetAsGiven(), _OverrideIgnored(), _ClampWithoutSpend(), _RefuseAfterCall(),
    _VisibilityIgnored(), _SumNotProduct(), _TiebreakPrefersOperators(),
    _NormaliseBeforeCompare(), _ItemDropped(), _OffsetOffByOne(),
)}

FAMILIES = ("check_clamp", "check_selection", "check_comparator")

CAUGHT_BY = {
    "budget-as-given": "check_clamp",
    "override-ignored": "check_clamp",
    "clamp-without-spend": "check_clamp",
    "refuse-after-call": "check_clamp",
    "visibility-ignored": "check_selection",
    "sum-not-product": "check_selection",
    "tiebreak-prefers-operators": "check_selection",
    "normalise-before-compare": "check_comparator",
    "item-dropped": "check_comparator",
    "offset-off-by-one": "check_comparator",
}


# ------------------------------------------------------------------------ named cases


#: Every clamp scenario there is: the space is finite, so it is enumerated, not sampled.
CLAMP_SCENARIOS = tuple((spend, flag, checked_in, other)
                        for spend in (False, True) for flag in FLAGS
                        for checked_in in (0, BIG) for other in (0, BIG))


def _candidate(source: str, loc: int, ops: tuple, visible: bool = True) -> dict:
    return {"source": source, "visible_export": visible, "parser_files": [f"{source}.py"],
            "parser_loc": loc, "operators": list(ops)}


def _measure(*candidates: dict) -> dict:
    return {"tannen": "measurement/1", "counter": "loc/1", "candidates": list(candidates)}


SELECTION_CASES = {
    "single": _measure(_candidate("alpha", 120, ("select", "project"))),
    "cheaper-but-no-export": _measure(_candidate("alpha", 120, ("select", "project")),
                                      _candidate("beta", 10, ("select",), visible=False)),
    "product-beats-loc": _measure(_candidate("alpha", 30, ("select", "project", "join")),
                                  _candidate("beta", 50, ("select",))),
    "product-beats-sum": _measure(_candidate("alpha", 10, ("select", "project", "join")),
                                  _candidate("beta", 12, ("select", "project"))),
    "product-tie-fewer-operators": _measure(
        _candidate("gamma", 40, ("select", "project", "join")),
        _candidate("delta", 60, ("select", "project"))),
    "full-tie-source-bytes": _measure(_candidate("zeta", 20, ("select",)),
                                      _candidate("eta", 20, ("project",))),
    "no-eligible": _measure(_candidate("alpha", 10, ("select",), visible=False)),
    "unknown-operator-anywhere": _measure(_candidate("alpha", 10, ("select",)),
                                          _candidate("beta", 5, ("teleport",), visible=False)),
    "source-measured-twice": _measure(_candidate("alpha", 10, ("select",)),
                                      _candidate("alpha", 99, ("project",))),
}

COMPARATOR_CASES = {
    "all-identical": [("i-1", b'{"a":1}', b'{"a":1}'), ("i-2", b"", b"")],
    "differ-at-zero": [("i-1", b"abc", b"xbc")],
    "tannen-is-a-prefix": [("i-1", b"abcdef", b"abc")],
    "production-is-a-prefix": [("i-1", b"ab", b"abcd")],
    "trailing-newline-only": [("i-1", b"rows\n", b"rows")],
    "trailing-space-only": [("i-1", b"rows", b"rows ")],
    "empty-against-bytes": [("i-1", b"", b"x")],
    "mixed-last-differs": [("i-1", b"same", b"same"), ("i-2", b"one", b"two")],
}


# ------------------------------------------------------------------------ strategies & harness


def _profile(max_examples: int) -> Any:
    from hypothesis import HealthCheck, settings

    return settings(max_examples=max_examples, deadline=None, derandomize=True,
                    report_multiple_bugs=False, suppress_health_check=[HealthCheck.too_slow])


def measurements(catalogue: tuple) -> Any:
    @st.composite
    def draw(d: Any) -> dict:
        sources = d(st.lists(st.sampled_from(["a", "b", "c", "d", "e", "f"]), min_size=1,
                             max_size=5, unique=True))
        candidates = [_candidate(s, d(st.integers(1, 40)),
                                 tuple(d(st.lists(st.sampled_from(catalogue), min_size=1,
                                                  max_size=4, unique=True))),
                                 d(st.booleans()))
                      for s in sources]
        event(f"candidates={len(candidates)} eligible={sum(c['visible_export'] for c in candidates)}")
        return _measure(*candidates)
    return draw()


def byte_cases() -> Any:
    @st.composite
    def draw(d: Any) -> list:
        n = d(st.integers(1, 4))
        cases = []
        for i in range(n):
            production = d(st.binary(max_size=8))
            tannen = d(st.one_of(st.just(production), st.binary(max_size=8),
                                 st.just(production + b"\n"), st.just(production[:-1])))
            cases.append((f"i-{i}", production, tannen))
        event(f"items={n} differing={sum(t != p for _i, p, t in cases)}")
        return cases
    return draw()


def run_family(subject: Subject, family: str, max_examples: int = 25) -> None:
    """Run one family against `subject`; raise on the first counterexample. Named cases first
    (D0118)."""
    from hypothesis import given

    profile = _profile(max_examples)
    if family == "check_clamp":
        for scenario in CLAMP_SCENARIOS:
            check_clamp(subject, scenario)
    elif family == "check_selection":
        for name in sorted(SELECTION_CASES):
            check_selection(subject, SELECTION_CASES[name])
        profile(given(m=measurements(subject.catalogue))(
            lambda m: check_selection(subject, m)))()
    elif family == "check_comparator":
        for name in sorted(COMPARATOR_CASES):
            check_comparator(subject, COMPARATOR_CASES[name])
        profile(given(c=byte_cases())(lambda c: check_comparator(subject, c)))()
    else:
        raise ValueError(f"unknown family {family!r}")


# ------------------------------------------------------------------------ the Grade-S corpora


def schema(name: str) -> dict:
    """The frozen schema of `measurement`, `corpus` or `divergence`."""
    return json.loads((_HERE / name / "schema.json").read_text(encoding="utf-8"))


def vector_paths(name: str, side: str) -> list[Path]:
    return sorted((_HERE / name / side).glob("*.json"))
