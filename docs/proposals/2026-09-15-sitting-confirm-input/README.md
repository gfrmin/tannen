# The sitting's y/n prompt ate the owner's answers (D0251)

**Drafted, not installed.** `scripts/boundary_sitting.sh` is custody-set, so this lands only
when the owner installs the next sitting driver — the M5 draft should carry `confirm.sh` in
place of the two lines in `confirm-m4-installed.sh`, and be cleared as whole bytes (D0068).

## What happened

At the M4 boundary sitting (2026-09-14/15) three answers the owner typed as `y` were taken as
declines: the D0248 accept at step 8, keeping D0131's binding upgrades at step 8b, and the
commit at step 9. The commit decline took no receipt, so step 10 refused on a dirty tree and
the sitting paused; a resume run completed it.

The driver's `confirm()` accepts only a line whose first character is `y`. Anything already
sitting in the terminal becomes part of the next line: a key pressed as `less` closes, or an
Enter pressed during a forty-minute gate. The driver logs prompt numbers, not input, so which
of these happened at each prompt is not recoverable — the mechanism is shown below instead.

## The fix (`confirm.sh`)

1. On a terminal only, each prompt first discards what was typed before it appeared, and
   prints what it discarded. Non-canonical reads (`-n`) are needed: a lone `q` with no Enter
   cannot be drained by a line read.
2. An answer is `y`/`yes` or `n`/`no`, case-insensitive. Anything else — an empty line
   included — is shown back and asked again. The `[y/N]` default is gone: a sitting's answer
   spends the owner's key, and a default is exactly how a stray Enter became a decline.
3. A decline echoes what was typed. End of input still declines.

## Watched

`python3 confirm_pty_test.py <impl.sh>` drives each implementation through a real pty.

| Case | installed | drafted |
|---|---|---|
| clean `y` / clean `n` / `yes` / `maybe` then `n` | ok | ok |
| Enter typed during a gate, then `y` | **DECLINE** | accept (discarded `\n` shown) |
| `q` typed during a gate, then `y` | **DECLINE** | accept (discarded `q` shown) |
| `qy` on the prompt line, then `y` | **DECLINE** | re-asked, accept |
| empty line, then `y` | **DECLINE** | re-asked, accept |

Installed: 4 failing. Drafted: 0 failing. Fed from a file, as `rehearse_sitting.sh` feeds its
answers, the drafted `confirm` and `pause` behave as before for `--answers y` and `--answers n`,
because nothing is drained off a non-terminal.
