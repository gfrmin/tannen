
| `check-decisions-file-skip/` | `scripts/check_decisions.py` | a whole-file pytest binding whose target has one passing test and one unexplained `pytest.mark.skip` | `unexplained skip` |

This fixture proves RT-M1-05's fix: before it, a file-level binding with one skipped
test among several passing ones read as fully enforced (`pytest_violation` called a run
"skipped" only when *nothing* in it passed). Lands together with the guard patch it
proves — installing the fixture before the patch would leave the custodian red against
a guard that isn't shipped yet, which is why this row and `oracle-shadow/`'s were never
one table addition (see D0105 item 2).
