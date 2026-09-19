# Custody for governance/record-edits.yaml (D0274, the RT-12 residue)

RT-12's guard (D0274) holds every decision record to the blob that first added it. A
legitimate past edit is declared in `governance/record-edits.yaml`. That file authorises an
edit, just as `governance/xfail-retirements.yaml` authorises a retirement, so it belongs in
the custody set for the same reason (D0273 ruling 3). Until it is custody-set, a builder can
commit an edit and then declare it, and every guard stays green. This is the residue D0274
names.

`record-edits-custody.patch` adds one line to `governance/tier-c.yaml`'s custody set.
`tier-c.yaml` is itself custody-set and in `MANIFEST.sha256`, so the owner applies the patch,
updates that manifest row, and re-signs `custody.sha256`. These are the same steps as the m5
close chain's custody patch.

It needs `governance/record-edits.yaml` to exist in the tree, because a custody pattern that
matches nothing is refused. So run it after the rt12 branch lands, at the next sitting or on
its own, in `~/git/tannen` on `master`:

```
ssh-add ~/.ssh/tannen_owner && P=docs/proposals/2026-09-19-rt12-record-edits-custody && git apply "$P/record-edits-custody.patch" && grep -v '  governance/tier-c.yaml$' MANIFEST.sha256 > MANIFEST.tmp && sha256sum governance/tier-c.yaml >> MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256 && .venv/bin/python -I -P scripts/gen_custody.py && rm -f governance/custody.sha256.sig && ssh-keygen -Y sign -f ~/.ssh/tannen_owner -n tannen-custody governance/custody.sha256 && .venv/bin/python -I -P scripts/check_manifest.py && git add governance/tier-c.yaml MANIFEST.sha256 governance/custody.sha256 governance/custody.sha256.sig && git commit -m "Custody-set governance/record-edits.yaml (D0274, RT-12 residue)" && git push origin master
```

One key touch, the custody signature. The chain was rehearsed in a scratch worktree up to
the signature: after `gen_custody.py`, `check_manifest.py` reddens only on the custody
signature.
