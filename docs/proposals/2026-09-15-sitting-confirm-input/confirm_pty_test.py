#!/usr/bin/env python3
"""Drive a confirm() implementation through a real pty with the keystroke shapes the M4 sitting
suffered, and report what it concluded. Usage: run.py <confirm-impl.sh>"""
import os, pty, sys, time, select

IMPL = sys.argv[1]

CASES = [
    # (name, keystrokes typed BEFORE the prompt appears, keystrokes typed after, expected)
    ("clean y", b"", b"y\r", "ACCEPT"),
    ("clean n", b"", b"n\r", "DECLINE"),
    ("Enter typed during a gate, then y", b"\r", b"y\r", "ACCEPT"),
    ("q typed during a gate, then y", b"q", b"y\r", "ACCEPT"),
    ("stray q on the prompt line, re-asked, y", b"", b"qy\ry\r", "ACCEPT"),
    ("empty line, re-asked, y", b"", b"\ry\r", "ACCEPT"),
    ("yes spelled out", b"", b"yes\r", "ACCEPT"),
    ("garbage then n", b"", b"maybe\rn\r", "DECLINE"),
]

SCRIPT = f"""
PROMPTS=/dev/null; PROMPT_N=0
note_prompt() {{ :; }}
note() {{ printf '   %s\n' "$*"; }}
source {IMPL!r}
sleep 0.4            # the long gate: keystrokes typed now queue in the tty
if confirm "Keep it?"; then echo RESULT=ACCEPT; else echo RESULT=DECLINE; fi
"""


def run(pre, post):
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp("bash", ["bash", "--norc", "-c", SCRIPT])
    out = b""
    os.write(fd, pre) if pre else None
    time.sleep(0.9)                     # after the prompt is up
    for chunk in post.split(b"\r"):
        if chunk or post:
            os.write(fd, chunk + b"\r")
            time.sleep(0.3)
    deadline = time.time() + 5
    while time.time() < deadline:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            out += data
            if b"RESULT=" in out and out.rstrip().endswith((b"ACCEPT", b"DECLINE")):
                break
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass
    os.waitpid(pid, 0)
    text = out.decode(errors="replace")
    res = "ACCEPT" if "RESULT=ACCEPT" in text else "DECLINE" if "RESULT=DECLINE" in text else "HUNG"
    return res, text


bad = 0
for name, pre, post, want in CASES:
    got, text = run(pre, post.rstrip(b"\r"))
    ok = got == want
    bad += not ok
    shown = " | ".join(l.strip() for l in text.splitlines() if l.strip() and "RESULT" not in l)
    print(f"{'ok  ' if ok else 'FAIL'} {name:42s} want {want:7s} got {got:7s}  [{shown[:90]}]")
print(f"{bad} failing")
sys.exit(1 if bad else 0)
