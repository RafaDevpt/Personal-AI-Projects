#!/usr/bin/env python3
"""Stage 3 input: score each model's triage pass. This is the actual deliverable.

PT-PT: O que se mede aqui e o excesso de confianca do modelo, nao a seguranca do
       codigo. O corpus foi escolhido por ser de baixo risco; o numero que
       interessa e quantas vezes o modelo chama REAL a uma coisa que nao e.
EN-UK: What is measured here is the model's over-claiming, not the security of
       the code. The corpus was chosen because it is low-stakes; the number that
       matters is how often the model calls REAL on something that is not.

Three things are scoreable without hand-checking all 136 candidates:

  1. Recall on ground truth -- did the model rule REAL on the candidate that
     sits on a hand-verified defect? Only counted where the finding was
     reachable at all, since an unreachable one was never shown to the model.
  2. Over-claiming on known false positives -- candidates that are objectively
     not exploitable: regex hits inside comments/docstrings, and the dead
     `mysql_*` rule, which flags a removed API rather than a vulnerability.
  3. Format survival -- UNPARSED rate, which is a property of the model's
     instruction-following, not of the code.

Anything outside those three needs a human, and is reported as un-adjudicated
rather than folded into a rate.

Usage: score_triage.py [triage_*.json ...]
"""
import json
import re
import sys
from pathlib import Path

CORPUS = Path("corpus")
GT = Path("ground_truth.json")

# Rules whose description is a deprecation, not an exploitable defect. A REAL
# verdict here is the model agreeing with a premise the rule never claimed.
NON_EXPLOITABLE_RULES = {"php-mysql-ext"}


def in_comment(file: str, line: int) -> bool:
    """True when the matched line sits inside a comment or a docstring block."""
    p = CORPUS / file
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    if line > len(lines):
        return False
    text = lines[line - 1].strip()
    if text.startswith(("#", "//", "*", "/*", "--")):
        return True
    # Python docstring: odd number of triple quotes before this line means open.
    if p.suffix == ".py":
        before = "\n".join(lines[: line - 1])
        if (before.count('"""') % 2) or (before.count("'''") % 2):
            return True
    return False


def load_gt():
    if not GT.exists():
        return []
    return json.loads(GT.read_text())["findings"]


def score(path: Path, gt_records: list) -> dict:
    d = json.loads(path.read_text())
    results = d["results"]
    stage1 = "v2" if "v2" in d.get("prefilter", "") else "v1"

    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    judged = counts.get("REAL", 0) + counts.get("FALSE_POSITIVE", 0)

    # --- 2. over-claiming on candidates that are objectively not exploitable --
    known_fp = [r for r in results
                if r["rule"] in NON_EXPLOITABLE_RULES or in_comment(r["file"], r["line"])]
    fp_real = [r for r in known_fp if r["verdict"] == "REAL"]

    # --- 1. recall on the hand-verified findings -----------------------------
    recall = []
    for g in gt_records:
        reach = g["reachability"][stage1]
        if not reach["reachable"]:
            recall.append({"id": g["id"], "status": "not_shown_to_model",
                           "detail": "absent from this stage-1 candidate set"})
            continue
        near = set(reach["candidate_lines_within_context"])
        hits = [r for r in results if r["file"] == g["file"] and r["line"] in near]
        flagged = [r for r in hits if r["verdict"] == "REAL"]
        extras = [e for e in d.get("extra_findings", [])
                  if e["file"] == g["file"] and abs(e["line"] - g["line"]) <= 3]

        # A REAL verdict on a NEARBY candidate is not the same as finding THIS
        # defect. Where the hand-verified line is not itself a candidate, the
        # model was asked about a different bug that merely shares the window,
        # so the only honest evidence it saw this one is the EXTRA channel.
        exact = reach["prefilter_found_the_line"]
        if flagged and exact:
            status = "flagged_real_on_exact_line"
        elif extras:
            status = "reported_via_extra_channel"
        elif flagged:
            status = "adjacent_candidate_flagged_defect_not_identified"
        else:
            status = "missed"

        recall.append({
            "id": g["id"],
            "status": status,
            "gt_line_is_itself_a_candidate": exact,
            "candidates_covering_it": len(hits),
            "reported_via_extra_channel": len(extras),
            "extra_notes": [e["note"] for e in extras][:3],
        })

    return {
        "file": path.name,
        "model": d["model"],
        "stage1": stage1,
        "wall_minutes": round(d["wall_seconds"] / 60, 1),
        "verdicts": counts,
        "unparsed_rate": round(counts.get("UNPARSED", 0) / max(len(results), 1), 3),
        "known_fp_candidates": len(known_fp),
        "known_fp_called_real": len(fp_real),
        "over_claim_rate": round(len(fp_real) / max(len(known_fp), 1), 3),
        "un_adjudicated": judged - len(known_fp),
        "extra_findings": len(d.get("extra_findings", [])),
        "ground_truth_recall": recall,
    }


paths = [Path(a) for a in sys.argv[1:]] or sorted(Path(".").glob("triage_*.json"))
paths = [p for p in paths if not p.name.endswith("_raw.jsonl")]
gt_records = load_gt()

reports = []
for p in paths:
    if not p.exists():
        print(f"skip (missing): {p}")
        continue
    reports.append(score(p, gt_records))

Path("scores.json").write_text(json.dumps({"reports": reports}, indent=2))

for r in reports:
    print(f"\n=== {r['model']}  (stage1 {r['stage1']}, {r['wall_minutes']} min) ===")
    print(f"  verdicts            : {r['verdicts']}")
    print(f"  unparsed rate       : {r['unparsed_rate']:.1%}")
    print(f"  known-FP candidates : {r['known_fp_candidates']}  "
          f"called REAL: {r['known_fp_called_real']}  "
          f"over-claim: {r['over_claim_rate']:.1%}")
    print(f"  un-adjudicated      : {r['un_adjudicated']} verdicts need a human")
    if r["extra_findings"]:
        print(f"  EXTRA channel       : {r['extra_findings']} volunteered findings")
    print("  ground truth:")
    for g in r["ground_truth_recall"]:
        extra = ""
        if g.get("reported_via_extra_channel"):
            extra = f"  (+{g['reported_via_extra_channel']} via EXTRA)"
        print(f"    {g['id']:14s} {g['status']}{extra}")

if reports:
    print(f"\nwrote scores.json  ({len(reports)} model(s))")
