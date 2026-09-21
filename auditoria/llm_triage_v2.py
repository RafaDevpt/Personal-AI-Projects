#!/usr/bin/env python3
"""Stage 2 v2: ask a local model to judge each candidate, in survivable batches.

PT-PT: Tres correccoes face a v1:
       1. Lotes de 6 candidatos. O 3b entrava em ciclo de repeticao com 13 e
          devolvia 13 linhas iguais, sem veredicto nenhum.
       2. Guarda a resposta em bruto. Sem isso, diagnosticar exige repetir a
          corrida inteira.
       3. Canal EXTRA, para o modelo relatar defeitos que ve na janela mas que
          nao estao na lista de candidatos -- era impossivel na v1.
EN-UK: Three fixes over v1:
       1. Batches of 6 candidates. The 3b fell into a repetition loop at 13 and
          returned 13 identical lines with no verdict at all.
       2. Persists the raw response. Without it, diagnosis means re-running.
       3. An EXTRA channel, so the model can report defects it sees in the
          window but which are not in the candidate list -- impossible in v1.

Usage: llm_triage_v2.py <model> <out.json> [prefilter.json]
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
PREFILTER = Path(sys.argv[3] if len(sys.argv) > 3 else "prefilter_v2.json")
RAW = OUT.with_name(OUT.stem + "_raw.jsonl")
CORPUS = Path("corpus")

CTX = 8               # lines of context either side of a line-anchored hit
BATCH = 6             # candidates per request; 13 broke the 3b outright
RETRY_BATCH = 2       # on a zero-parse batch, retry this much smaller
WHOLE_FILE_MAX = 120  # absence findings need the file, but cap it

SYSTEM = (
    "You are a security code reviewer. For each numbered candidate you are given, "
    "decide whether it is a REAL exploitable vulnerability or a FALSE_POSITIVE. "
    "Reply with one line per candidate in exactly this format:\n"
    "<number>|<REAL or FALSE_POSITIVE>|<short reason, max 15 words>\n"
    "If you notice a SEPARATE defect in the code shown that is not one of the "
    "numbered candidates, add lines in this format after the verdicts:\n"
    "EXTRA|<line number>|<short description, max 15 words>\n"
    "Output nothing else. No preamble, no code, no markdown."
)

VERDICT_RE = re.compile(
    r"\s*\(?(\d+)\)?\s*[|.:\-]\s*(REAL|FALSE_POSITIVE)\s*[|.:\-]?\s*(.*)", re.I)
EXTRA_RE = re.compile(r"\s*EXTRA\s*[|:]\s*(\d+)\s*[|:]\s*(.*)", re.I)


def snippet(path: Path, line: int, whole: bool) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    if whole and len(lines) <= WHOLE_FILE_MAX:
        lo, hi = 0, len(lines)
    else:
        lo, hi = max(0, line - 1 - CTX), min(len(lines), line + CTX)
    return "\n".join(f"{n+1}: {lines[n]}" for n in range(lo, hi))


def ask(prompt: str, n_cands: int) -> tuple[str, dict]:
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "system": SYSTEM,
        "stream": False,
        # Budget per candidate rather than a flat cap, so a big batch is not
        # silently truncated mid-verdict.
        "options": {"temperature": 0, "num_predict": 80 * n_cands + 120,
                    "num_ctx": 4096},
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return d.get("response", ""), d


def build_prompt(fn: str, hits: list) -> str:
    parts = [f"File: {fn}\n"]
    for i, h in enumerate(hits, 1):
        if h.get("evidence_kind") == "absence":
            parts.append(
                f"--- candidate {i} ---\n"
                f"rule: {h['desc']}\n"
                f"This candidate is about something MISSING from the file below. "
                f"Judge whether its absence is a real vulnerability.\n"
                f"{snippet(CORPUS / fn, h['line'], True)}\n"
            )
        else:
            parts.append(
                f"--- candidate {i} ---\n"
                f"rule: {h['desc']}\n"
                f"line {h['line']}:\n{snippet(CORPUS / fn, h['line'], False)}\n"
            )
    parts.append(f"\nJudge all {len(hits)} candidates. One line each.")
    return "\n".join(parts)


def parse(text: str) -> tuple[dict, list]:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    verdicts, extras = {}, []
    for line in text.splitlines():
        line = line.strip()
        m = EXTRA_RE.match(line)
        if m:
            extras.append({"line": int(m.group(1)), "note": m.group(2).strip()[:120]})
            continue
        m = VERDICT_RE.match(line)
        if m:
            verdicts[int(m.group(1))] = (m.group(2).upper(), m.group(3).strip()[:120])
    return verdicts, extras


def chunks(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield i, seq[i:i + n]


data = json.loads(PREFILTER.read_text())
by_file = defaultdict(list)
for f in data["findings"]:
    by_file[f["file"]].append(f)

results, extra_findings = [], []
raw_fh = RAW.open("w")
t_all = time.time()
tok_in = tok_out = dur_in = dur_out = 0.0
n_retried = n_unparsed = 0

files = sorted(by_file)
for idx, fn in enumerate(files, 1):
    hits = by_file[fn]
    got_total, t_file = 0, time.time()

    for offset, batch in chunks(hits, BATCH):
        size = BATCH
        while True:
            for sub_off, sub in chunks(batch, size):
                prompt = build_prompt(fn, sub)
                t0 = time.time()
                try:
                    text, meta = ask(prompt, len(sub))
                except Exception as e:
                    print(f"[{idx}/{len(files)}] {fn} ERROR {e}", flush=True)
                    text, meta = "", {}
                el = time.time() - t0

                tok_in += meta.get("prompt_eval_count", 0)
                dur_in += meta.get("prompt_eval_duration", 0) / 1e9
                tok_out += meta.get("eval_count", 0)
                dur_out += meta.get("eval_duration", 0) / 1e9

                verdicts, extras = parse(text)
                raw_fh.write(json.dumps({
                    "file": fn, "batch_offset": offset + sub_off, "batch_size": len(sub),
                    "seconds": round(el, 1), "parsed": len(verdicts),
                    "prompt_eval_count": meta.get("prompt_eval_count"),
                    "eval_count": meta.get("eval_count"),
                    "done_reason": meta.get("done_reason"),
                    "response": text,
                }) + "\n")
                raw_fh.flush()

                # A batch that parsed nothing means the model derailed. Retry it
                # smaller once; a 2-candidate prompt is much harder to loop on.
                if not verdicts and len(sub) > RETRY_BATCH and size == BATCH:
                    continue

                for j, h in enumerate(sub, 1):
                    v, reason = verdicts.get(j, ("UNPARSED", ""))
                    if v == "UNPARSED":
                        n_unparsed += 1
                    results.append({**h, "verdict": v, "reason": reason})
                got_total += sum(1 for j in range(1, len(sub) + 1) if j in verdicts)
                for e in extras:
                    extra_findings.append({"file": fn, **e})

            # Decide whether the whole batch needs a smaller second pass.
            if size == BATCH and got_total == 0 and len(batch) > RETRY_BATCH:
                n_retried += 1
                size = RETRY_BATCH
                results = [r for r in results if not (
                    r["file"] == fn and r.get("verdict") == "UNPARSED")]
                n_unparsed -= len(batch)
                continue
            break

    print(f"[{idx}/{len(files)}] {time.time()-t_file:5.1f}s  {got_total}/{len(hits)} parsed  {fn}",
          flush=True)

raw_fh.close()
total = time.time() - t_all
summary = {
    "model": MODEL,
    "prefilter": str(PREFILTER),
    "batch_size": BATCH,
    "wall_seconds": round(total, 1),
    "files": len(files),
    "candidates": len(results),
    "batches_retried_smaller": n_retried,
    "unparsed": n_unparsed,
    "prompt_tok_s": round(tok_in / dur_in, 1) if dur_in else 0,
    "gen_tok_s": round(tok_out / dur_out, 1) if dur_out else 0,
    "verdicts": {},
    "extra_findings": extra_findings,
    "results": results,
}
for r in results:
    summary["verdicts"][r["verdict"]] = summary["verdicts"].get(r["verdict"], 0) + 1

OUT.write_text(json.dumps(summary, indent=2))
print(f"\n{MODEL}: {total/60:.1f} min | prompt {summary['prompt_tok_s']} tok/s | "
      f"gen {summary['gen_tok_s']} tok/s | {summary['verdicts']} | "
      f"{len(extra_findings)} EXTRA | raw -> {RAW.name}")
