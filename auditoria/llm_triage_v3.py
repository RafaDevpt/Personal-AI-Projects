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

# PT-PT: A v3 e a v2 com tres coisas novas, e NADA MAIS. Os valores por
#        omissao sao exactamente os da v2, para as medicoes do 3b, do 7b e do
#        8b continuarem comparaveis com o que sair daqui. Trocar o motor a meio
#        de uma comparacao e a maneira mais facil de obter um numero que nao
#        quer dizer nada.
#
#        1. --host      : aponta a um Ollama noutra maquina (o portatil, pela
#                         tailnet). Sem isto, so se mede o que corre aqui.
#        2. --num-predict: tecto de fichas por candidato. A omissao (80) chega
#                         para um modelo que responde directamente e NAO chega
#                         para um que pensa primeiro -- o qwen3:8b gastou o
#                         orcamento todo no raciocinio e devolveu resposta vazia
#                         em 64 de 99 chamadas.
#        3. --sem-raciocinio: desliga o `think` nos modelos que o suportam, que
#                         e a outra saida para o mesmo problema.
#
# EN-UK: v3 is v2 plus three things and NOTHING ELSE. The defaults are exactly
#        v2's, so the 3b, 7b and 8b measurements stay comparable with whatever
#        comes out of here. Swapping the engine mid-comparison is the easiest
#        way to get a number that means nothing.
import argparse

_p = argparse.ArgumentParser(description="Triagem de candidatos por um modelo.")
_p.add_argument("modelo")
_p.add_argument("saida", type=Path)
_p.add_argument("prefiltro", type=Path, nargs="?", default=Path("prefilter_v2.json"))
_p.add_argument("--host", default="http://127.0.0.1:11434",
                help="Ollama a usar. Ex.: http://100.110.43.103:11434 (portátil).")
_p.add_argument("--num-predict", type=int, default=80,
                help="Fichas por candidato. 80 é o valor da v2; um modelo de "
                     "raciocínio precisa de muito mais (2000+).")
_p.add_argument("--num-ctx", type=int, default=4096)
_p.add_argument("--sem-raciocinio", action="store_true",
                help="Envia think=false, para modelos que gastam o orçamento a pensar.")
_p.add_argument("--lote", type=int, default=6,
                help="Candidatos por pedido. 6 é o valor da v2; 13 rebentou o 3b.")
_args = _p.parse_args()

MODEL = _args.modelo
OUT = _args.saida
PREFILTER = _args.prefiltro
HOST = _args.host.rstrip("/")
FICHAS_POR_CANDIDATO = _args.num_predict
NUM_CTX = _args.num_ctx
SEM_RACIOCINIO = _args.sem_raciocinio
RAW = OUT.with_name(OUT.stem + "_raw.jsonl")
CORPUS = Path("corpus")

CTX = 8               # lines of context either side of a line-anchored hit
BATCH = _args.lote    # candidates per request; 13 broke the 3b outright
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
    carga = {
        "model": MODEL,
        "prompt": prompt,
        "system": SYSTEM,
        "stream": False,
        # Budget per candidate rather than a flat cap, so a big batch is not
        # silently truncated mid-verdict.
        "options": {"temperature": 0,
                    "num_predict": FICHAS_POR_CANDIDATO * n_cands + 120,
                    "num_ctx": NUM_CTX},
    }
    if SEM_RACIOCINIO:
        # PT-PT: O Ollama ignora esta chave nos modelos que nao raciocinam, por
        #        isso e seguro manda-la sempre que o utilizador a pedir.
        # EN-UK: Ollama ignores this key on non-reasoning models, so it is safe
        #        to send whenever the user asks for it.
        carga["think"] = False
    body = json.dumps(carga).encode()
    req = urllib.request.Request(
        f"{HOST}/api/generate",
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
