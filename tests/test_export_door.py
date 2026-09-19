"""The export door re-derives a node's layer from what ran, never from its label (RT-M4-03)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tannen.executor import Built
from tannen.export import export
from tannen.kernel.layers import Layer, LayerError
from tannen.store import Store


def _built(store: Store, layer: Layer, operators: set[str]) -> Built:
    ref = store.put_bytes(b"row bytes")
    return Built(derivation_id="sha256:" + "0" * 64, output_ref=ref, rebuilt=True,
                 layer=layer, operators=frozenset(operators))


def test_an_honest_serve_node_exports(tmp_path: Path) -> None:
    store = Store(tmp_path)
    assert export(store, _built(store, Layer.SERVE, {"project", "select"})) == b"row bytes"


def test_a_serve_label_over_wider_operators_is_refused(tmp_path: Path) -> None:
    store = Store(tmp_path)
    with pytest.raises(LayerError, match="RT-M4-03"):
        export(store, _built(store, Layer.SERVE, {"join", "distinct"}))
