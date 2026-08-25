"""M1 law L1.10 — layers are sublanguages, statically checked
(docs/specs/m1.md §6; BRIEF P8, §5.9).

FROZEN at m1-laws-freeze. The four layers form a CHAIN under operator-set inclusion, so
"the most restrictive layer admitting a node's operators" is well defined rather than a
preference between incomparable options.
"""

from __future__ import annotations

import pytest

layers = pytest.importorskip(
    "tannen.kernel.layers",
    reason="M1 layers not implemented yet (law suite frozen ahead of Session B)",
)
ops = pytest.importorskip("tannen.kernel.ops")

Layer = layers.Layer

#: The pinned membership table (docs/specs/m1.md §6). `capture` admits no operators at all
#: — it is oracles only, and oracles arrive at M4.
EXPECTED = {
    Layer.CAPTURE: frozenset(),
    Layer.SERVE: frozenset({"project", "select"}),
    Layer.DECODE: frozenset({"project", "select", "map_rows"}),
    Layer.DERIVE: frozenset(
        {"project", "select", "map_rows", "union", "join", "distinct", "anti_join", "aggregate"}
    ),
}
ORDER = [Layer.CAPTURE, Layer.SERVE, Layer.DECODE, Layer.DERIVE]


def test_l1_10_the_membership_table_is_the_pinned_one() -> None:
    assert dict(layers.LAYER_OPERATORS) == EXPECTED
    # Every operator the kernel exports appears in `derive`, or the table has drifted from
    # the surface it is supposed to constrain.
    assert set(ops.OPERATORS) == EXPECTED[Layer.DERIVE]


def test_l1_10_the_layers_form_a_chain_under_inclusion() -> None:
    for narrower, wider in zip(ORDER, ORDER[1:]):
        assert layers.LAYER_OPERATORS[narrower] < layers.LAYER_OPERATORS[wider], (
            f"{narrower} must be strictly contained in {wider}: without a chain, "
            "'the most restrictive layer admitting these operators' is not well defined"
        )
    assert list(sorted(ORDER)) == ORDER  # the enum orders the same way the inclusion does


@pytest.mark.parametrize(
    ("operators", "expected"),
    [
        ((), Layer.CAPTURE),
        (("project",), Layer.SERVE),
        (("select",), Layer.SERVE),
        (("project", "select"), Layer.SERVE),
        (("map_rows",), Layer.DECODE),
        (("map_rows", "select"), Layer.DECODE),
        (("join",), Layer.DERIVE),
        (("distinct",), Layer.DERIVE),
        (("aggregate",), Layer.DERIVE),
        (("anti_join",), Layer.DERIVE),
        (("union",), Layer.DERIVE),
        (("project", "join"), Layer.DERIVE),
    ],
    ids=lambda v: getattr(v, "name", None) or "+".join(v) or "none",
)
def test_l1_10_layer_of_is_the_most_restrictive_admitting_them(operators, expected) -> None:
    assert layers.layer_of(operators) is expected


def test_l1_10_an_unknown_operator_is_refused_by_name() -> None:
    with pytest.raises(layers.LayerError):
        layers.layer_of(("not_an_operator",))


@pytest.mark.parametrize(
    ("declared", "operators"),
    [
        (Layer.DERIVE, ("project",)),       # widening from serve
        (Layer.DECODE, ("project",)),       # widening from serve
        (Layer.DERIVE, ("map_rows",)),      # widening from decode
        (Layer.SERVE, ("project", "select")),   # exact
        (Layer.DERIVE, ("join",)),          # exact
        (Layer.CAPTURE, ()),                # exact
    ],
    ids=["serve->derive", "serve->decode", "decode->derive", "serve", "derive", "capture"],
)
def test_l1_10_widening_is_accepted_and_recorded(declared, operators) -> None:
    assert layers.check_layer(declared, operators) is declared


@pytest.mark.parametrize(
    ("declared", "operators"),
    [
        (Layer.SERVE, ("join",)),
        (Layer.SERVE, ("map_rows",)),
        (Layer.DECODE, ("aggregate",)),
        (Layer.CAPTURE, ("project",)),
        (Layer.CAPTURE, ("join",)),
    ],
    ids=["serve<join", "serve<map", "decode<aggregate", "capture<project", "capture<join"],
)
def test_l1_10_narrowing_is_refused_by_name(declared, operators) -> None:
    # A node may promise LESS power than it has; it may not promise more restraint than it
    # practises (BRIEF §5.9).
    with pytest.raises(layers.LayerError):
        layers.check_layer(declared, operators)


def test_l1_10_capture_admits_no_operators_at_all() -> None:
    # Oracles only, and oracles are M4. An empty admitted set is the honest spelling of
    # "nothing in this layer computes over relations".
    assert layers.LAYER_OPERATORS[Layer.CAPTURE] == frozenset()
    for operator_name in ops.OPERATORS:
        with pytest.raises(layers.LayerError):
            layers.check_layer(Layer.CAPTURE, (operator_name,))
