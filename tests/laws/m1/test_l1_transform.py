"""M1 law L1.12 — the registering decorator (docs/specs/m1.md §8; BRIEF §5.1, §5.2).

FROZEN at m1-laws-freeze. BRIEF §5.1: "the only way to define a transform is the
registering decorator, which computes `code_hash` and derives the label. An unhashed
function cannot enter a graph." This law is the mechanical form of that sentence.

`code_hash` addresses the function's SOURCE TEXT, so a comment change mints a new
descriptor and invalidates that transform's evidence. That is deliberate — "what would make
this a different event belongs in the hash" — and a rule with an exception for comments is
a rule someone has to remember.
"""

from __future__ import annotations

import textwrap

import pytest

transform_mod = pytest.importorskip(
    "tannen.transform",
    reason="M1 transform registry not implemented yet (law suite frozen ahead of Session B)",
)
layers = pytest.importorskip("tannen.kernel.layers")

from tannen.kernel.descriptor import derive_label, descriptor_id  # noqa: E402
from tannen.kernel.encoding import CanonicalEncodingError, content_address  # noqa: E402
from tannen.kernel.refs import is_ref, ref_for_bytes  # noqa: E402

transform = transform_mod.transform

REFUSALS = (transform_mod.TransformError, CanonicalEncodingError, layers.LayerError, TypeError)


@transform(kind="derive", params={"scale": 2})
def doubled(source):
    """A registered transform."""
    return source


@transform(kind="derive", params={"scale": 3})
def tripled(source):
    """A registered transform, with different params and a different body length."""
    return source


def unregistered(source):
    return source


def plain(source):
    return source


def _same_body(params):
    """Two calls produce functions with IDENTICAL source text and different params."""

    def compute(source):
        return source

    return transform(kind="derive", params=params)(compute)


def test_l1_12_registration_attaches_the_whole_descriptor() -> None:
    for fn in (doubled, tripled):
        assert fn.is_transform is True
        assert is_ref(fn.code_hash)
        assert is_ref(fn.params_hash)
        assert is_ref(fn.descriptor_id)
        assert isinstance(fn.label, str) and fn.label


def test_l1_12_the_descriptor_is_m0s_function_of_its_four_components() -> None:
    # Not a new identity scheme — docs/specs/m0.md §4's, applied.
    assert doubled.descriptor_id == descriptor_id(
        kind="derive", name="doubled", code_hash=doubled.code_hash, params_hash=doubled.params_hash
    )
    assert doubled.descriptor_id != tripled.descriptor_id


def test_l1_12_params_hash_is_the_content_address_of_the_params() -> None:
    assert doubled.params_hash == content_address({"scale": 2})
    assert tripled.params_hash == content_address({"scale": 3})


def test_l1_12_the_label_is_the_pure_function_of_m0() -> None:
    # BRIEF §5.2: the label is DERIVED from module path, name and a sequence counted from
    # prior registrations, so there is no "forgot to bump" state.
    assert doubled.label == derive_label(doubled.__module__, "doubled", 0)
    assert tripled.label == derive_label(tripled.__module__, "tripled", 0)
    first, second = _same_body({"a": 1}), _same_body({"a": 2})
    assert first.label == derive_label(first.__module__, "compute", 0)
    assert second.label == derive_label(second.__module__, "compute", 1)  # seq advances


def test_l1_12_code_hash_addresses_the_source_text() -> None:
    # The exact bytes, decorator line included (docs/specs/m1.md §8). Written out rather
    # than recomputed from `inspect.getsource`, which would restate the implementation and
    # test nothing.
    source = textwrap.dedent(
        '''\
        @transform(kind="derive", params={"scale": 2})
        def doubled(source):
            """A registered transform."""
            return source
        '''
    )
    assert doubled.code_hash == ref_for_bytes(source.encode("utf-8"))


def test_l1_12_identical_source_hashes_identically_and_params_still_separate_them() -> None:
    first, second = _same_body({"a": 1}), _same_body({"a": 2})
    assert first.code_hash == second.code_hash, "identical source must hash identically"
    assert first.params_hash != second.params_hash
    assert first.descriptor_id != second.descriptor_id


def test_l1_12_different_source_hashes_differently() -> None:
    assert doubled.code_hash != tripled.code_hash


def test_l1_12_an_unregistered_function_cannot_enter_a_graph() -> None:
    # BRIEF §5.1: an unhashed function is refused BY NAME, not silently hashed on the fly.
    with pytest.raises(transform_mod.TransformError):
        transform_mod.descriptor_of(unregistered)
    with pytest.raises(transform_mod.TransformError):
        transform_mod.descriptor_of(lambda source: source)
    assert transform_mod.descriptor_of(doubled) == doubled.descriptor_id


def test_l1_12_a_lambda_cannot_be_registered() -> None:
    # `<lambda>` is not a name, so no label derives from it and no descriptor identifies it.
    with pytest.raises(transform_mod.TransformError):
        transform(kind="derive", params={})(lambda source: source)


def test_l1_12_registering_the_same_function_twice_is_refused() -> None:
    # Silently shadowing would leave two descriptors claiming one function.
    with pytest.raises(transform_mod.TransformError):
        transform(kind="derive", params={})(doubled)


def test_l1_12_the_layer_declaration_is_optional_and_defaults_to_inferred() -> None:
    # The node's real layer comes from what RAN (docs/specs/m1.md §6); the decorator only
    # records a declaration, and `None` means "infer at build".
    assert doubled.layer is None
    declared = transform(kind="derive", params={}, layer=layers.Layer.SERVE)(plain)
    assert declared.layer is layers.Layer.SERVE


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": "", "params": {}},
        {"kind": "derive", "params": {"bad": 1.5}},          # a float has no canonical form
        {"kind": "derive", "params": object()},              # params must be a value
        {"kind": "derive", "params": {}, "layer": "serve"},  # a Layer, not a string
    ],
    ids=["empty-kind", "float-param", "non-value-params", "string-layer"],
)
def test_l1_12_bad_registrations_are_refused_by_name(kwargs) -> None:
    with pytest.raises(REFUSALS):

        @transform(**kwargs)
        def victim(source):
            return source
