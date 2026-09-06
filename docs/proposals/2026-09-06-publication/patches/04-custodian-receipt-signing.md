# The custodian says "author-signed" when the signing failed

Found 2026-09-06 by running `scripts/custodian.sh` bare as the merge gate for `m3 ->
master`, on a machine without the owner key's passphrase. Author-key territory (BRIEF
§9.1), so drafted, not applied.

## What happens

`scripts/custodian.sh:283-285`:

```sh
    ssh-keygen -Y sign -f "${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}" \
        -n tannen-receipt "$receipt"
    say "attention receipt written and author-signed: $receipt (+ .sig)"
```

`ssh-keygen`'s exit status is never read. Observed output, verbatim:

```
custodian: custody floor intact
Enter passphrase for "…/tannen_owner": Load key "…/tannen_owner": incorrect passphrase supplied to decrypt private key
custodian: attention receipt written and author-signed: receipts/2026-09-06.md (+ .sig)
```

There is no `.sig`. The custodian exits 0, having:

1. written an **unsigned** receipt into `receipts/`;
2. printed a line asserting it is signed, naming a file that does not exist;
3. reported the custody floor intact.

## Why it matters more than it looks

The receipt step runs **after** `check_receipts.py`, and only when the custodian is run
**bare** — `make verify` passes `--check-only` and skips it entirely. So the one context
where this fires is a sitting, which is the worst available place for it: the step appears
to succeed, and the damage surfaces on the *next* custodian run rather than this one.

It self-detects eventually, which bounds the blast radius. Confirmed as the positive
control:

```
$ python scripts/check_receipts.py
check_receipts: FAIL (1 violation(s))
  - receipts/2026-09-06.md has no signature. A receipt is an attestation of presence;
    an unsigned one attests to nothing and would let the chain below be extended by
    the party it measures.
```

But "the next run catches it" is not the property the line claims. An operator who reads
`author-signed` and moves on has been told something false by the guard whose entire job
is to be the thing you can believe. And a receipt is the artifact that starts the Tier-B
silence-as-consent clock: an unsigned one sitting in `receipts/` between two runs is a
clock nobody can verify started.

## The fix

Check the status, and leave no artifact behind when it fails. `bad` already increments
`FAIL`, so the custodian exits non-zero and says why.

```diff
-    ssh-keygen -Y sign -f "${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}" \
-        -n tannen-receipt "$receipt"
-    say "attention receipt written and author-signed: $receipt (+ .sig)"
+    if ssh-keygen -Y sign -f "${TANNEN_OWNER_KEY:-$HOME/.ssh/tannen_owner}" \
+           -n tannen-receipt "$receipt"; then
+        say "attention receipt written and author-signed: $receipt (+ .sig)"
+    else
+        # An unsigned receipt is worse than no receipt: it attests to nothing while
+        # looking like an attestation, and check_receipts would then redden every later
+        # run for a file this step should never have left behind.
+        rm -f "$receipt"
+        bad "receipt signing FAILED — $receipt removed, not left unsigned"
+    fi
```

The `rm -f` is deliberate and is the only deletion in this script: the file was created
three lines earlier by this same step and has never been part of the record. Nothing that
was ever signed, committed or attested is touched.

## Watching it fail

Both directions, before believing it:

```sh
# 1. signing fails -> non-zero exit, no receipt left behind
TANNEN_OWNER_KEY=/dev/null bash scripts/custodian.sh
test ! -e "receipts/$(date +%F).md" && echo "no orphan receipt"   # required

# 2. signing succeeds -> receipt and .sig both present, exit 0
bash scripts/custodian.sh
test -e "receipts/$(date +%F).md.sig" && echo "signed"            # required
```

Case 1 is runnable by anyone. Case 2 needs the owner key, so it belongs to the sitting.

## Housekeeping from the discovery

The unsigned `receipts/2026-09-06.md` this produced was **never committed** — it was
untracked, removed within minutes, and `check_receipts.py` was re-run to confirm
`5 receipt(s); chain unbroken to HEAD`. A copy is held outside the repository as evidence
for this note. The receipt chain is exactly as it was.
