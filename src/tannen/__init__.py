"""tannen — a semantic kernel for pure, versioned, content-addressed data pipelines (BRIEF §1).

A sibling repository may depend on this package at an owner-signed `<milestone>-close` tag or a
published version, never by path, submodule, vendoring or a moving branch (BRIEF §1.1). What it
may import is `SURFACE`: those modules and their submodules, and from each the names in
its `__all__`. A name that is merely reachable in a surface module is not promised, and a
submodule whose name starts with an underscore is private even under a surface package.
`NOT_SURFACE` names every other module and why. The promise is per tag: a tag's own copy of
these lists is what it promises, and a tag older than the lists (every tag through
`m5-close`) promises none. `tests/test_surface.py` derives the module set from the tree and
fails when a module is in neither list, so nothing becomes a promise to a dependent by being
added (D0275).
"""

SURFACE: tuple[str, ...] = (
    "tannen.kernel",
    "tannen.transform",
    "tannen.executor",
    "tannen.incremental",
    "tannen.sources",
    "tannen.store",
    "tannen.oracles",
    "tannen.export",
)

#: module -> why a dependent may not import it.
NOT_SURFACE: dict[str, str] = {
    "tannen.cli": "the `tannen` command; a dependent runs its pipelines from its own code",
    "tannen.dogfood": "M5's selection, run and comparison, over this repository's .dogfood/",
    "tannen.laws": "finds laws under this repository's tests/laws/ and reads src/tannen as the "
    "implementation, so it cannot run another repository's laws",
    "tannen.r2": "the transport behind tannen.store's R2Backend; use the backend, not this",
}
