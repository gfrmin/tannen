#!/usr/bin/env python3
"""Generate the owner's sitting agenda FROM the driver, so it cannot go stale.

D0209's rule reaches prose, and a hand-written briefing listing the driver's prompts would
be one more hand-maintained enumeration. This reads the driver instead.

    python3 gen_agenda.py boundary_sitting.sh > AGENDA.md
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

STEP = re.compile(r'^\s*say "Step ([^ ]+) — (.*)"\s*$')
CONFIRM = re.compile(r'confirm "([^"]+)"')
NOTE = re.compile(r'^\s*note "(.*)"\s*$')
CITE = re.compile(r'\((?:see )?((?:D0\d+|RT-[A-Z0-9-]+)[^)]*)\)\s*$')

# What makes a step consequential, derived from the call it makes rather than asserted.
ACTS = (
    # Anchored on the CALL, not the line start: step 7 signs custody as `|| sign_owner …`,
    # and an earlier spelling of this table anchored at ^ and silently omitted step 7 —
    # the custody signature — from the list of consequential steps.
    ("uses your key", re.compile(r'(?<![\w#])(sign_owner|sign_tier_c_records)\b')),
    # `git tag -s` appears ONLY inside comments in this driver; the mint is a continuation
    # line of a multi-line git invocation. Matching the documented spelling found nothing
    # and dropped step 10 — the close tag itself — off the list.
    ("mints the close tag", re.compile(r'(?<![\w#])tag -s\b')),
    ("writes a commit", re.compile(r'(?<![\w#])commit_with_hook_retry\b')),
    ("signs the receipt", re.compile(r'^\s*bash scripts/custodian\.sh\s*\|\|')),
)


def decline_notes(lines: list[str], at: int) -> list[str] | None:
    """The `else` arm's notes — the cost of answering n. None when there is no else arm,
    which means the prompt only gates a display and n is free."""
    depth = 0
    for j in range(at + 1, min(at + 90, len(lines))):
        s = lines[j].strip()
        if s.startswith(("if ", "case ")):
            depth += 1
        elif s in ("fi", "esac"):
            if depth == 0:
                return None
            depth -= 1
        elif s == "else" and depth == 0:
            out: list[str] = []
            for k in range(j + 1, min(j + 40, len(lines))):
                n = NOTE.match(lines[k])
                t = lines[k].strip()
                if n:
                    if n.group(1):
                        out.append(n.group(1))
                elif t in ("fi", "else"):
                    break
            return out
    return None


def then_action(lines: list[str], at: int) -> str:
    """First real command of the `then` arm — what answering y actually does."""
    for k in range(at + 1, min(at + 12, len(lines))):
        t = lines[k].strip()
        if not t or t.startswith("#"):
            continue
        if t in ("fi", "else"):
            return ""
        return t[:70]
    return ""


def parse(src: str) -> list[dict]:
    steps: list[dict] = []
    lines = src.splitlines()
    for i, line in enumerate(lines):
        m = STEP.match(line)
        if m:
            title = m.group(2)
            cite = CITE.search(title)
            steps.append({"id": m.group(1), "title": CITE.sub("", title).strip(),
                          "cites": cite.group(1) if cite else "",
                          "prompts": [], "acts": set()})
            continue
        if not steps:
            continue
        for label, pat in ACTS:
            if pat.search(line) and not line.strip().startswith("#"):
                steps[-1]["acts"].add(label)
        c = CONFIRM.search(line)
        if c:
            steps[-1]["prompts"].append({"q": c.group(1),
                                         "decline": decline_notes(lines, i),
                                         "then": then_action(lines, i)})
    return steps


def step8_queue(root: Path) -> list[str]:
    """Step 8's own filter, re-run here: every Tier-C record still blocked-on-owner. One
    prompt each. Derived rather than quoted, because quoting the clearance run's prompt
    count goes stale the moment a record is added — which it did, the same day."""
    out = []
    for f in sorted((root / "decisions").glob("*.yaml")):
        t = f.read_text(encoding="utf-8")
        if re.search(r"^tier: C$", t, re.M) and re.search(r"^status: blocked-on-owner$", t, re.M):
            m = re.search(r"^id: *(\S+)", t, re.M)
            if m:
                out.append(m.group(1))
    return out


def main() -> int:
    driver = Path(sys.argv[1] if len(sys.argv) > 1 else "boundary_sitting.sh")
    src = driver.read_text(encoding="utf-8")
    steps = parse(src)
    decisions = [(s, p) for s in steps for p in s["prompts"] if p["decline"] is not None]
    displays = [(s, p) for s in steps for p in s["prompts"] if p["decline"] is None]
    keyed = [s for s in steps if s["acts"]]

    print("# M3 boundary sitting — the owner's agenda\n")
    print(f"Generated from `{driver.name}`, sha256 "
          f"`{hashlib.sha256(driver.read_bytes()).hexdigest()[:7]}…` — the bytes the "
          f"clearance run of 2026-09-10 cleared.\n")
    print(f"**{len(steps)} steps. {len(decisions)} prompts state a cost for declining, "
          f"{len(displays)} do not.** A prompt with no `else` arm simply skips its action — "
          f"usually a printout, but NOT always: step 0's `make verify` has no else arm and "
          f"declining it skips the precondition gate. Not every site fires — several "
          f"sit inside conditionals, so the number you meet depends on repo state.\n")
    queue = step8_queue(Path(__file__).resolve().parents[3])
    if queue:
        print(f"**Step 8 will ask you {len(queue)} times**, once per Tier-C record still "
              f"blocked-on-owner — derived from `decisions/` just now, not copied from a "
              f"previous run: {', '.join(queue)}.\n")
    print(f"**{len(keyed)} steps do something consequential**, and only these:\n")
    for s in keyed:
        print(f"- **Step {s['id']}** — {', '.join(sorted(s['acts']))}")
    print("\nEverything else edits files you can revert. Every prompt is decline-and-continue "
          "except step 10's: decline there and the sitting stops without a close tag.\n")
    print("---\n")

    for s in steps:
        flag = f"  ⚠ {', '.join(sorted(s['acts']))}" if s["acts"] else ""
        print(f"## Step {s['id']} — {s['title']}{flag}\n")
        if s["cites"]:
            print(f"*Resolves: {s['cites']}*\n")
        if not s["prompts"]:
            print("No prompt — the driver acts or skips on its own.\n")
            continue
        for p in s["prompts"]:
            if p["decline"] is None:
                act = f" (**y** runs `{p['then']}`)" if p.get("then") else ""
                print(f"- *no stated consequence* — {p['q']} — **n** skips the action{act}.")
                continue
            print(f"\n**{p['q']}**\n")
            if p["decline"]:
                print("Answering **n**:\n")
                for d in p["decline"]:
                    print(f"> {d}")
            else:
                print("Answering **n**: reverts the edit, leaves the item open.")
            print()
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
