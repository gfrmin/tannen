"""A law file for the fixture tree, parsed statically and never executed.

`check_laws` reads law files with `ast.parse`, so this needs to be syntactically valid
Python and nothing more. It defines the retired node the registry names, so the fixture
fails on the SUCCESSOR check rather than on "names a file that does not exist" or "is
not a law node" — one fixture, one reason.
"""

VALIDATION_REASON = "fixture tree: never run, parsed only"


def test_l1_7_a_law_that_was_retired() -> None:
    """The node governance/laws.yaml retires. It exists so that the entry is well-formed
    up to the point the fixture is about."""
