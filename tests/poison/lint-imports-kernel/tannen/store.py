"""Poison: `no-cross-repo` (BRIEF §1, Tier C door renavon-first-contact).

Outside `tannen.kernel` on purpose: the cross-repo contract's source is the whole
`tannen` package, and a fixture that only ever violates inside the kernel would not
notice that source being narrowed.
"""

import pkm       # noqa: F401 — no-cross-repo
import proplang  # noqa: F401 — no-cross-repo
