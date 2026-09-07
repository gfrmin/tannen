# Patch 07 — the custodian carried its own copy of the receipt-chain check

**Status: drafted as `07-custodian-delegates-receipt-chain.patch`, not applied.**
`scripts/custodian.sh` is author-key territory (BRIEF §9.1). The driver applies it at
step 0, beside patch 04, under your confirmation. Filed by D0183.

## The finding

`scripts/check_receipts.py` verifies the receipt chain; so does section 4b of
`scripts/custodian.sh`, in bash, independently. Two implementations of one rule. Patch 02
taught the guard three things — a `receipts/REWRITE-<date>.md` attestation exists, it is
signed under its own namespace `tannen-rewrite`, and recorded HEADs resolve through its map —
and the custodian learned none of them. Measured on the rewritten history, first full
mechanics rehearsal, 2026-09-07:

```
check_receipts: OK — 6 receipt(s); chain unbroken to HEAD through 84 remapped commit(s)
custodian: FAIL — receipt receipts/2026-08-24.md records HEAD bac005e8…, which is no longer a commit here
custodian: FAIL — receipt receipts/2026-08-25.md records HEAD e6a9c8fc…, which is no longer a commit here
   (… four more …)
custodian: FAIL — receipt signature does not verify: receipts/REWRITE-2026-09-07.md
custodian: FAIL — custody floor violated
```

The guard says the chain is intact; the custodian, running in the same `make verify`, says
the history the owner attested to is gone and the attestation is a forged receipt. Both are
reading the same files. BRIEF §2: *restatement is duplication; duplication is drift* — and
this drift sat inside the floor, between the guard `make verify` runs and the custodian that
`make verify` also runs, which is where a disagreement is least visible.

`rehearse_rewrite.sh` could not see it: that harness only ever ran `check_receipts.py`
against the rewritten clone, never the custodian, because its step 10 maps `owner@tannen` to
the builder key and the custodian's other checks would have gone red for that reason alone.
The full rehearsal runs the custodian as the sitting will, and it went red at step 9.

## The fix

Section 4b becomes one line, the shape 3b already has for `check_tag_signers.py`:

```sh
"$PY" -I -P scripts/check_receipts.py || bad "receipt chain violated (scripts/check_receipts.py)"
```

`check_receipts.py` is custody-set, so nothing is lost: the custodian's inline loop verified
signatures against `allowed_signers`, resolved each recorded HEAD by `git cat-file`, and
checked ancestry — the guard does each of those, plus the attestation. The custodian's own
"receipt chain verifies to HEAD" line is replaced by the guard's summary line.

## Also found on the way: patch 02 itself

The first spelling of patch 02 verified the attestation **as a receipt** — its main loop
globbed `receipts/*.md`, which includes `REWRITE-*.md`, and asked for a `tannen-receipt`
signature over a file signed under `tannen-rewrite`. Red on the rewritten history, invisible
to `rehearse_rewrite.sh` for the same key-mapping reason. Patch 02 now skips `REWRITE-*` in
that loop (they are read once, above it, under their own namespace).

## Watched failing

Before the patch: the block quoted above. After it, on the same rewritten clone:

```
check_receipts: OK — 6 receipt(s); chain unbroken to HEAD through 84 remapped commit(s)
custodian: custody floor intact
```

Negative controls for the attestation itself (removed / unsigned / map tampered) are
patch 02's, in the package README; they exercise the same code the custodian now calls.
