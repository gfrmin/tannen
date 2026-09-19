# The M5 close sitting

**Status:** drafted by the builder. It runs after the pipeline review has reported and D0273
pins its sha256. Doors plus signatures, one `&&` chain, rehearsed once (D0267 ruling 3).

## What it signs and applies

1. **The custody patch** (`doors-custody.patch`). `governance/doors.yaml`,
   `governance/xfail-retirements.yaml` and `governance/laws.yaml` join the custody set:
   RT-M5-05, RT-M5-04's exception, and RT-M2-02 and RT-14, by the owner's rulings of
   2026-09-19 (D0272, D0273). `tier-c.yaml` is frozen, so its MANIFEST row is refreshed, and
   custody is regenerated and re-signed.
2. **The attention receipt**, taken by `scripts/custodian.sh` at the HEAD being closed.
3. **The M5-close digest** (`make digest`).
4. **`m5-close`**, owner-signed, last. Its message quotes the delegation, custody and ledger
   hashes, the same as `m4-close` (`tag-message.sh`).

Before any key touch, the chain checks that `.dogfood/vertical.py` is still byte-for-byte the
reviewed file D0273 pins. If it has changed since the review, the chain stops.

## The chain

Run it in the m5 worktree, in a real terminal, with the owner key in the agent. Three key
touches: custody, the receipt (inside `custodian.sh`) and the tag. `make verify` runs first
and is the M5 attestation: on this machine, with the corpus present, the M5 laws run live.

```sh
cd ~/git/worktrees/tannen/m5 \
&& ssh-add ~/.ssh/tannen_owner \
&& git pull --ff-only origin m5 \
&& make verify \
&& P=docs/proposals/2026-09-19-m5-close-sitting \
&& test "$(sha256sum .dogfood/vertical.py | cut -d' ' -f1)" = "$(sed -n 's/.*vertical\.py sha256 \([0-9a-f]\{64\}\).*/\1/p' decisions/0273-*.yaml)" \
&& git apply "$P/doors-custody.patch" \
&& grep -v '  governance/tier-c.yaml$' MANIFEST.sha256 > MANIFEST.tmp && sha256sum governance/tier-c.yaml >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256 \
&& .venv/bin/python -I -P scripts/gen_custody.py \
&& rm -f governance/custody.sha256.sig \
&& ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-custody governance/custody.sha256 \
&& bash scripts/custodian.sh \
&& make projections && make digest \
&& git add -A && git commit -m "m5 close sitting: laws.yaml, door data and xfail retirements custody-set; receipt; digest" \
&& M=$(mktemp) && bash "$P/tag-message.sh" > "$M" \
&& git -c gpg.format=ssh -c user.signingkey="$HOME/.ssh/tannen_owner" tag -s m5-close -F "$M" \
&& git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" verify-tag m5-close \
&& .venv/bin/python -I -P scripts/check_tag_signers.py \
&& bash scripts/custodian.sh --check-only \
&& git push origin m5 m5:master m5-close
```

Then read every CI run the push starts: the branch, `master` and the tag. Finish with `ssh-add -d`.

## After it

The private sibling pins `m5-close` in its own sessions (BRIEF §1.1). The first post-M5 builder
session lands RT-12's record-immutability guard (D0273).
