#!/usr/bin/env python3
"""gen_projections.py — generated projections of the governance records (BRIEF §9).

Writes CONCEPTS.md (from concepts/*.yaml), DECISIONS.md (from decisions/*.yaml) and,
with --digest, digest/<date>.md. Each output carries an input-hash header binding it
to the exact record set it was generated from; the check scripts fail when the header
goes stale. Projections are queries, not authorship: a digest cannot omit a decision.

The digest is exception-only (BRIEF §9.1–§9.2): risk-flagged records always surface,
K others are sampled deterministically (seed = input hash + date; no wall-clock
randomness), the rest auto-consent under a fresh attention receipt. Ratcheted metrics
(unenforced count; Grade-P/S-pending residue) are compared against the previous digest
and a rise is flagged as a breach.

Files are rewritten only when content changed, so the pre-commit hook is idempotent.
Exits non-zero only on internal errors (it generates; the check scripts judge).
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import re
import sys
from pathlib import Path

from _gov import (
    GEN_MARKER,
    effective_status,
    input_hash,
    load_yaml,
    receipt_state,
    REPO_ROOT,
)

METRICS_RE = re.compile(r"<!-- metrics: unenforced=(\d+) residue=(\d+) -->")


def header(digest_hash: str) -> str:
    return f"<!-- {GEN_MARKER}; input-hash: {digest_hash}; DO NOT EDIT BY HAND -->\n"


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def gen_concepts(root: Path) -> str:
    paths = sorted((root / "concepts").glob("*.yaml"))
    records = [load_yaml(p) for p in paths]
    lines = [
        header(input_hash(paths, root)),
        "# CONCEPTS — adopted-concept registry (generated projection)",
        "",
        "Generated from `concepts/*.yaml` (BRIEF §2). One row per concept; the records,",
        "not this file, are the test manifest. Grades per BRIEF §2.1; `S-pending` marks a",
        "data-shaped concept whose owner has not yet published frozen vectors.",
        "",
        "| Concept | Posture | Grade | Owner (normative home) | Pinned commit | Local artifact |",
        "|---|---|---|---|---|---|",
    ]
    for rec in sorted(records, key=lambda r: r["id"]):
        cites = "<br>".join(
            f"`{s['repo']}` — `{s['document']}` {s['section']}" for s in rec["sources"]
        )
        commits = "<br>".join(
            (s["commit"][:12] if s["commit"] else f"*{s.get('commit_note', 'unpinned')}*")
            for s in rec["sources"]
        )
        artifacts = "<br>".join(f"`{s['snapshot']['path']}`" for s in rec["sources"])
        if rec["grade"] == "S":
            artifacts += f"<br>vectors: `{rec['conformance']['vectors']}`"
        lines.append(
            f"| **{rec['id']}** — {rec['title']} | {rec['posture']} | {rec['grade']} "
            f"| {cites} | {commits} | {artifacts} |"
        )
    pend = [r for r in records if r["grade"] == "S-pending"]
    if pend:
        lines += ["", "## S-pending"]
        lines += [f"- **{r['id']}**: {r['conformance']['pending_reason']}" for r in pend]
    return "\n".join(lines) + "\n"


def load_decisions(root: Path) -> tuple[list[Path], list[dict]]:
    paths = sorted((root / "decisions").glob("*.yaml"))
    return paths, sorted((load_yaml(p) for p in paths), key=lambda r: r["id"])


def gen_decisions(root: Path, today: dt.date) -> str:
    paths, records = load_decisions(root)
    receipts_fresh, receipt_detail = receipt_state(root, today)
    lines = [
        header(input_hash(paths, root)),
        "# DECISIONS — the decision log (generated projection)",
        "",
        "Generated from `decisions/*.yaml` (BRIEF §9, as amended §9.1–§9.2). Truth is the",
        "fold of the records; this file is a query over them. Effective status is computed:",
        "a provisional Tier-B record past its veto date is accepted by lapse ONLY while the",
        "attention receipt is fresh; on a stale receipt it blocks instead.",
        "",
        f"Attention receipt: **{'FRESH' if receipts_fresh else 'STALE'}** — {receipt_detail}",
        "",
        "| Id | Tier | Title | Decision | Status (effective) | Veto by | Risk flags | Enforcement |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for rec in records:
        if rec["bindings"]:
            enforcement = "; ".join(f"{b['type']}: `{b['target']}`" for b in rec["bindings"])
        else:
            enforcement = f"**unenforced** — {rec['unenforced_reason']}"
        decision_short = rec["decision"].strip().split("\n")[0]
        flags = ", ".join(rec.get("risk_flags", [])) or "—"
        lines.append(
            f"| {rec['id']} | {rec['tier']} | {rec['title']} | {decision_short} "
            f"| {effective_status(rec, today, receipts_fresh)} | {rec.get('veto_by', '—')} "
            f"| {flags} | {enforcement} |"
        )
    unenforced = [r for r in records if not r["bindings"]]
    if unenforced:
        lines += ["", "## Unenforced (visible debt, BRIEF §9)"]
        lines += [f"- **{r['id']}** {r['title']}: {r['unenforced_reason']}" for r in unenforced]
    return "\n".join(lines) + "\n"


def previous_metrics(root: Path, today: dt.date) -> tuple[str, int, int] | None:
    digests = sorted(
        p for p in (root / "digest").glob("*.md")
        if p.stem < today.isoformat()
    )
    for path in reversed(digests):
        m = METRICS_RE.search(path.read_text(encoding="utf-8"))
        if m:
            return path.stem, int(m.group(1)), int(m.group(2))
    return None


def gen_digest(root: Path, today: dt.date) -> str:
    decision_paths, records = load_decisions(root)
    concept_paths = sorted((root / "concepts").glob("*.yaml"))
    concepts = [load_yaml(p) for p in concept_paths]
    receipts_fresh, receipt_detail = receipt_state(root, today)

    extra_inputs = [
        p for p in (
            root / "allowed_signers",
            root / "budget.yaml",
            root / "governance" / "policy.yaml",
        ) if p.exists()
    ]
    if (root / "receipts").is_dir():
        extra_inputs += sorted((root / "receipts").glob("*.md*"))
    inputs = decision_paths + concept_paths + extra_inputs

    policy = load_yaml(root / "governance" / "policy.yaml") if (root / "governance" / "policy.yaml").exists() else {}
    sample_k = ((policy or {}).get("spot_check") or {}).get("sample_rate_k", 3)

    lines = [
        header(input_hash(inputs, root)),
        f"# Digest — {today.isoformat()}",
        "",
        "Generated projection (BRIEF §9.1–§9.2): the owner's boundary-sitting batch,",
        "exception-only. Sections are queries over the records and repo state; nothing",
        "here was authored by hand.",
        "",
        "## Custody state",
        "",
        f"- Attention receipt: **{'FRESH' if receipts_fresh else 'STALE'}** — {receipt_detail}",
        f"- Policy signature: **{'present' if (root / 'governance' / 'policy.yaml.sig').exists() else 'absent (owner signs at opening)'}**",
        "",
        "## Requires owner (Tier-C queue — non-blocking: work continues elsewhere; batched to the next boundary sitting)",
        "",
    ]
    owner_items: list[str] = []
    signers = root / "allowed_signers"
    if not signers.exists() or "TODO-owner" in signers.read_text(encoding="utf-8"):
        owner_items.append(
            "**Opening sitting pending** — owner key not yet in `allowed_signers`; the "
            "`brief-freeze` tag is unsigned; policy.yaml unsigned; no receipt possible. "
            "Checklist: `docs/OPENING.md`."
        )
    budget = load_yaml(root / "budget.yaml") if (root / "budget.yaml").exists() else {}
    ceilings = (budget or {}).get("ceilings", {})
    if ceilings and all(v == 0 for v in ceilings.values()):
        owner_items.append(
            "**All spend envelopes/ceilings are zero** — no oracle spend is possible until "
            "the owner signs nonzero values (Tier-C door: spend-envelopes; `docs/OPENING.md`)."
        )
    if not receipts_fresh:
        blocked_b = [
            r for r in records
            if r["tier"] == "B" and r["status"] == "provisional"
            and dt.date.fromisoformat(r["veto_by"]) < today
        ]
        if blocked_b:
            owner_items.append(
                f"**{len(blocked_b)} Tier-B record(s) past veto with a stale receipt** — "
                "blocked, not consented; blocks accumulate and work pauses at the next "
                f"milestone boundary (BRIEF §9.1): {', '.join(r['id'] for r in blocked_b)}."
            )
    for rec in records:
        if rec["tier"] == "C" and effective_status(rec, today, receipts_fresh) == "blocked-on-owner":
            owner_items.append(f"**{rec['id']}** {rec['title']}: {rec['decision'].strip().splitlines()[0]}")

    unenforced = [r for r in records if not r["bindings"]]
    residue = [c for c in concepts if c["grade"] in ("P", "S-pending")]
    prev = previous_metrics(root, today)
    breaches: list[str] = []
    if prev:
        prev_date, prev_unenforced, prev_residue = prev
        if len(unenforced) > prev_unenforced:
            breaches.append(f"unenforced count rose {prev_unenforced} → {len(unenforced)} since {prev_date}")
        if len(residue) > prev_residue:
            breaches.append(f"Grade-P/S-pending residue rose {prev_residue} → {len(residue)} since {prev_date}")
    for breach in breaches:
        owner_items.append(f"**RATCHET BREACH** — {breach} (BRIEF §9.1: must trend down).")

    lines += [f"- {item}" for item in owner_items] or ["- Nothing requires the owner."]

    flagged = [r for r in records if r.get("risk_flags")]
    lines += ["", "## Risk-flagged decisions (always shown)", ""]
    lines += [
        f"- **{r['id']}** [{', '.join(r['risk_flags'])}] {r['title']} — "
        f"{effective_status(r, today, receipts_fresh)}"
        for r in flagged
    ] or ["- None."]

    unflagged = [r for r in records if not r.get("risk_flags")]
    seed = int(input_hash(decision_paths, root)[:16], 16) ^ int(today.strftime("%Y%m%d"))
    sample = random.Random(seed).sample(unflagged, min(sample_k, len(unflagged)))
    lines += ["", f"## Spot-check sample (K={sample_k} from policy.yaml; deterministic seed = input-hash + date)", ""]
    lines += [
        f"- **{r['id']}** (tier {r['tier']}) {r['title']} — {effective_status(r, today, receipts_fresh)}"
        for r in sorted(sample, key=lambda r: r["id"])
    ] or ["- Nothing to sample."]
    rest = len(unflagged) - len(sample)
    if rest > 0:
        consent_note = (
            "auto-consent under the fresh receipt" if receipts_fresh
            else "would auto-consent, but the receipt is stale — Tier-B among them block instead"
        )
        lines += ["", f"{rest} further unflagged record(s) {consent_note}; all are listed in DECISIONS.md."]

    lines += ["", "## Tier-B queue", ""]
    tier_b = [r for r in records if r["tier"] == "B" and r["status"] == "provisional"]
    if tier_b:
        for rec in tier_b:
            veto_by = dt.date.fromisoformat(rec["veto_by"])
            days = (veto_by - today).days
            if days >= 0:
                clock = f"{days} day(s) left to veto (by {veto_by})"
            elif receipts_fresh:
                clock = f"lapsed {-days} day(s) ago → accepted"
            else:
                clock = f"veto window passed {-days} day(s) ago — BLOCKED (stale receipt)"
            lines.append(f"- **{rec['id']}** {rec['title']} [{clock}]")
    else:
        lines.append("- Queue empty.")

    lines += [
        "",
        "## Laws & evidence",
        "",
        "- No laws are frozen yet (pre-M0). `tannen laws report` joins `make verify` when "
        "the M0 law set is frozen (decision D0012). Graduated autonomy (BRIEF §9.2) has "
        "no evidence stream to widen on until then.",
        "",
        "## Ratchet metrics (must trend down, BRIEF §9.1)",
        "",
        f"- Unenforced decisions: **{len(unenforced)}**"
        + (f" (previous digest {prev[0]}: {prev[1]})" if prev else " (no previous digest)"),
        f"- Grade-P / S-pending residue: **{len(residue)}**"
        + (f" (previous digest {prev[0]}: {prev[2]})" if prev else " (no previous digest)"),
        f"<!-- metrics: unenforced={len(unenforced)} residue={len(residue)} -->",
    ]

    counts: dict[str, int] = {}
    for rec in records:
        counts[rec["tier"]] = counts.get(rec["tier"], 0) + 1
    lines += [
        "",
        "## Record counts",
        "",
        f"- {len(records)} decision record(s): "
        + ", ".join(f"Tier {t}: {n}" for t, n in sorted(counts.items()))
        + f"; {len(concepts)} concept record(s).",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--digest", action="store_true", help="also generate digest/<date>.md")
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args()
    root = args.root.resolve()

    changed = []
    if write_if_changed(root / "CONCEPTS.md", gen_concepts(root)):
        changed.append("CONCEPTS.md")
    if write_if_changed(root / "DECISIONS.md", gen_decisions(root, args.today)):
        changed.append("DECISIONS.md")
    if args.digest:
        digest_path = root / "digest" / f"{args.today.isoformat()}.md"
        if write_if_changed(digest_path, gen_digest(root, args.today)):
            changed.append(str(digest_path.relative_to(root)))
    print(f"gen_projections: {'regenerated ' + ', '.join(changed) if changed else 'all projections fresh'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
