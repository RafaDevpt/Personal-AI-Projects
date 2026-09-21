#!/usr/bin/env python3
"""Stage 2 of the funnel: ask a local model to judge each regex candidate.

Sends a focused snippet per file rather than the whole file -- prompt processing
is the bottleneck on CPU (34 tok/s on the 7b), so context size dominates runtime.

Usage: llm_triage.py <model> <out.json>
"""
import json
import re
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

MODEL = sys.argv[1]
OUT = Path(sys.argv[2])
CORPUS = Path("corpus")
CTX = 8  # lines of context either side of a hit

SYSTEM = (
    "You are a security code reviewer. For each numbered candidate you are given, "
    "decide whether it is a REAL exploitable vulnerability or a FALSE_POSITIVE. "
    "Reply with one line per candidate in exactly this format:\n"
    "<number>|<REAL or FALSE_POSITIVE>|<short reason, max 15 words>\n"
    "Output nothing else. No preamble, no code, no markdown."
)


def snippet(path: Path, line: int) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    lo, hi = max(0, line - 1 - CTX), min(len(lines), line + CTX)
    return "\n".join(f"{n+1}: {lines[n]}" for n in range(lo, hi))


def ask(prompt: str) -> tuple[str, dict]:
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "system": SYSTEM,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 400, "num_ctx": 4096},
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return d.get("response", ""), d


data = json.loads(Path("prefilter.json").read_text())
by_file = defaultdict(list)
for f in data["findings"]:
    by_file[f["file"]].append(f)

results = []
t_all = time.time()
tok_in = tok_out = 0.0
dur_in = dur_out = 0.0

files = sorted(by_file)
for idx, fn in enumerate(files, 1):
    hits = by_file[fn]
    parts = [f"File: {fn}\n"]
    for i, h in enumerate(hits, 1):
        parts.append(
            f"--- candidate {i} ---\n"
            f"rule: {h['desc']}\n"
            f"line {h['line']}:\n{snippet(CORPUS / fn, h['line'])}\n"
        )
    parts.append(f"\nJudge all {len(hits)} candidates. One line each.")
    prompt = "\n".join(parts)

    t0 = time.time()
    try:
        text, meta = ask(prompt)
    except Exception as e:
        print(f"[{idx}/{len(files)}] {fn} ERROR {e}", flush=True)
        continue
    el = time.time() - t0

    tok_in += meta.get("prompt_eval_count", 0)
    dur_in += meta.get("prompt_eval_duration", 0) / 1e9
    tok_out += meta.get("eval_count", 0)
    dur_out += meta.get("eval_duration", 0) / 1e9

    # Models wander off-format; parse leniently.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    verdicts = {}
    for line in text.splitlines():
        m = re.match(r"\s*\(?(\d+)\)?\s*[|.:\-]\s*(REAL|FALSE_POSITIVE)\s*[|.:\-]?\s*(.*)",
                     line.strip(), re.I)
        if m:
            verdicts[int(m.group(1))] = (m.group(2).upper(), m.group(3).strip()[:120])

    for i, h in enumerate(hits, 1):
        v, reason = verdicts.get(i, ("UNPARSED", ""))
        results.append({**h, "verdict": v, "reason": reason})

    got = sum(1 for i in range(1, len(hits) + 1) if i in verdicts)
    print(f"[{idx}/{len(files)}] {el:5.1f}s  {got}/{len(hits)} parsed  {fn}", flush=True)

total = time.time() - t_all
summary = {
    "model": MODEL,
    "wall_seconds": round(total, 1),
    "files": len(files),
    "candidates": len(results),
    "prompt_tok_s": round(tok_in / dur_in, 1) if dur_in else 0,
    "gen_tok_s": round(tok_out / dur_out, 1) if dur_out else 0,
    "verdicts": {},
    "results": results,
}
for r in results:
    summary["verdicts"][r["verdict"]] = summary["verdicts"].get(r["verdict"], 0) + 1

OUT.write_text(json.dumps(summary, indent=2))
print(f"\n{MODEL}: {total/60:.1f} min | prompt {summary['prompt_tok_s']} tok/s | "
      f"gen {summary['gen_tok_s']} tok/s | {summary['verdicts']}")
