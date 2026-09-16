"""The M5 dogfood: select the vertical, replay it, compare it with production byte for byte
(docs/specs/m5.md §1, §2, §4, §5; BRIEF §8; L5.4, L5.7, L5.10).

Three verbs, and the separation between them is the point.

  `select`   BRIEF §8's selection rule over a `measurement/1` record: among the candidates
             with a visible export, the one minimising (parser LOC × distinct operators,
             distinct operators, source id as UTF-8 bytes). A measurement naming one source
             twice, or an operator outside the catalogue in ANY candidate, is refused whole,
             and so is one with nothing eligible. The catalogue is `tannen.kernel.ops`'s own
             tuple — derived from the package, never listed here (D0171 ruling (3), D0261).
  `run`      the vertical over the corpus's frozen inputs: the operator's pipeline, called
             once per item in corpus order with a REPLAY-ONLY oracle context (BRIEF §5.10).
             Frozen inputs mean every value it reads is already a source or a capture in the
             store, so nothing novel is invoked and nothing is spent.
  `compare`  byte identity, and nothing else: no trailing newline forgiven, no whitespace
             stripped, no re-encoding (D0262 item (2)). One `unanalysed` `divergence/1` per
             differing item, in corpus order; none for an identical one; outputs that do not
             answer exactly the corpus's items refused by name.

ANALYSIS IS A SEPARATE ACT. The comparator classifies nothing: it writes `unanalysed` and
stops. Classifying a divergence is how a dogfood turns into a demonstration, and M5's kill
criterion (docs/specs/m5.md §12) forbids exactly that response.

THIS LIBRARY READS NO GOVERNANCE FILE (owner ruling D0240). It enforces the authorisation it
is handed and never reads the constitution: Tier-C door `renavon-first-contact` is verified by
`tests/laws/m5/test_l5_authorisation.py` over the corpus's `authorisation` field, not here, and
this module neither knows the door's name nor opens a `decisions/` path. The same rule is why
nothing here validates a record against a frozen schema: the Grade-S corpora are the laws'
(L5.3, L5.5, L5.6), and a library that re-validated them would be a second, divergent copy.

LIMITS, stated. `run` imports the pipeline by the name the corpus gives it, so the operator's
code must be importable by the interpreter that calls it — the same contract `tannen run` has
and the same one it states. A pipeline is trusted to be pure over its input ref; what it did
is judged by the store's bytes afterwards, never by watching it.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from typing import Any

from tannen.kernel.ops import OPERATORS
from tannen.kernel.refs import is_ref
from tannen.oracles import Oracles

__all__ = [
    "DIVERGENCE_TAG",
    "IncompleteRun",
    "SelectionRefused",
    "UNANALYSED",
    "compare",
    "first_difference",
    "run",
    "select",
]

#: What the comparator writes, and the only class it may write (docs/specs/m5.md §5).
DIVERGENCE_TAG = "divergence/1"
UNANALYSED = "unanalysed"


class SelectionRefused(Exception):
    """No candidate the rule may select: nothing eligible, an operator outside the catalogue,
    or one source measured twice (docs/specs/m5.md §2)."""


class IncompleteRun(Exception):
    """Outputs that do not answer exactly the corpus's items — a comparison over a subset is a
    report about a corpus that was not run (docs/specs/m5.md §4)."""


# ------------------------------------------------------------------ the selection rule


def _rows(measurement: Mapping[str, Any]) -> tuple[tuple[str, bool, Any, frozenset], ...]:
    """The four fields of each candidate the rule reads, and nothing else. A measurement
    missing one of them is refused by name rather than raising out of the sort: the shape is
    the schema's to judge (L5.3), but the rule must be total over what it is handed."""
    try:
        return tuple(
            (candidate["source"], bool(candidate["visible_export"]), candidate["parser_loc"],
             frozenset(candidate["operators"]))
            for candidate in measurement["candidates"]
        )
    except (KeyError, TypeError, IndexError) as exc:
        raise SelectionRefused(
            f"a measurement/1 record names candidates with a source, a visible_export, a "
            f"parser_loc and operators; this one does not ({exc!r})"
        ) from exc


def _key(row: tuple[str, bool, Any, frozenset]) -> tuple[Any, int, bytes]:
    """(parser LOC × distinct operators, distinct operators, source id as UTF-8 bytes). The
    product is BRIEF §8's; a tie on it breaks toward FEWER operators, because an operator is a
    unit of algebra the vertical must get right; the source id is the last and total key
    (D0261)."""
    source, _visible, loc, operators = row
    return (loc * len(operators), len(operators), source.encode("utf-8"))


def select(measurement: Mapping[str, Any]) -> str:
    """The source id BRIEF §8's rule selects, or `SelectionRefused` naming why."""
    rows = _rows(measurement)
    sources = tuple(source for source, _v, _l, _o in rows)
    twice = sorted({source for source in sources if sources.count(source) > 1})
    if twice:
        raise SelectionRefused(
            f"the measurement names {twice} more than once — a source measured twice has no "
            "one LOC and no one operator set, so no rule selects from it"
        )
    unknown = sorted({op for _s, _v, _l, operators in rows for op in operators
                      if op not in OPERATORS})
    if unknown:
        raise SelectionRefused(
            f"{unknown} is not in tannen's operator catalogue {sorted(OPERATORS)} — a "
            "measurement naming an operator that does not exist is wrong as a whole, not only "
            "in the candidate that names it"
        )
    eligible = tuple(row for row in rows if row[1])
    if not eligible:
        raise SelectionRefused(
            f"no candidate of {sorted(sources)} has a visible export — BRIEF §8 selects among "
            "sources with one, and there is nothing here to compare against production"
        )
    try:
        return min(eligible, key=_key)[0]
    except TypeError as exc:  # a parser_loc that is not a number
        raise SelectionRefused(f"a candidate's parser_loc is not a count ({exc!r})") from exc


# ------------------------------------------------------------------ the vertical


def _pipeline(target: str) -> Any:
    """The corpus's `MODULE:CALLABLE`, imported as `tannen run` names it."""
    module, colon, attr = target.partition(":")
    if not (module and colon and attr):
        raise ValueError(f"a corpus pipeline is MODULE:CALLABLE, not {target!r}")
    return getattr(importlib.import_module(module), attr)


def _answer(pipeline: Any, oracles: Oracles, store: Any, item: Mapping[str, Any]) -> str:
    output = pipeline(oracles, store, item["input"])
    if not is_ref(output):
        raise IncompleteRun(
            f"item {item['id']!r} was answered with {output!r}, which is not a content address "
            "— an item is answered by the ref of the bytes the vertical produced [cites: "
            "provenance-ref-grammar]"
        )
    return output


def run(store: Any, corpus: Mapping[str, Any]) -> dict[str, str]:
    """`{item id: output ref}`: the corpus's pipeline over each item's frozen input, in corpus
    order, under a replay-only context. A novel invocation is refused by the context itself
    (`NovelInvocationRefused`), which is what makes "frozen inputs" a checked claim rather
    than a description."""
    pipeline = _pipeline(corpus["pipeline"])
    oracles = Oracles(store)
    return {item["id"]: _answer(pipeline, oracles, store, item) for item in corpus["items"]}


# ------------------------------------------------------------------ the comparator


def first_difference(a: bytes, b: bytes) -> int | None:
    """The first index at which two byte strings differ; the shorter length when one is a
    proper prefix of the other; `None` when they are identical."""
    if a == b:
        return None
    for index, (left, right) in enumerate(zip(a, b)):
        if left != right:
            return index
    return min(len(a), len(b))


def _divergence(store: Any, item: Mapping[str, Any], output: str) -> dict[str, Any] | None:
    """The `divergence/1` for one item, or `None` when its bytes are production's. The BYTES
    are compared, not the refs: a comparator that compared addresses would report on the
    store's arithmetic rather than on the vertical's output."""
    offset = first_difference(store.get_bytes(output), store.get_bytes(item["production_output"]))
    if offset is None:
        return None
    return {
        "tannen": DIVERGENCE_TAG,
        "item": item["id"],
        "input": item["input"],
        "tannen_output": output,
        "production_output": item["production_output"],
        "offset": offset,
        "classification": UNANALYSED,
        "analysis": "",
        "evidence": [],
    }


def compare(store: Any, corpus: Mapping[str, Any],
            outputs: Mapping[str, str]) -> tuple[dict[str, Any], ...]:
    """One `unanalysed` `divergence/1` per item whose output is not production's byte for
    byte, in corpus order. `IncompleteRun` when `outputs` does not answer exactly the corpus's
    items."""
    items = tuple(corpus["items"])
    ids = tuple(item["id"] for item in items)
    if len(set(ids)) != len(ids):
        raise IncompleteRun(
            "the corpus names an item more than once, so no set of outputs answers it exactly")
    if set(outputs) != set(ids):
        missing = sorted(set(ids) - set(outputs))
        extra = sorted(set(outputs) - set(ids))
        raise IncompleteRun(
            f"the outputs do not answer exactly the corpus's items: {len(missing)} unanswered "
            f"{missing}, {len(extra)} not in the corpus {extra} — a comparison over a subset is "
            "a report about a corpus that was not run"
        )
    found = (_divergence(store, item, outputs[item["id"]]) for item in items)
    return tuple(divergence for divergence in found if divergence is not None)
