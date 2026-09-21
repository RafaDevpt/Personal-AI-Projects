#!/usr/bin/env python3
"""Records the findings Claude confirmed by hand, for scoring the triage passes.

PT-PT: Verdade de referencia. Cada achado foi confirmado a ler o codigo, nao por
       regex nem por modelo. As arvores Python vem triplicadas (Linux/Windows/
       macOS), por isso o achado 2 expande-se para as tres copias.
EN-UK: Ground truth. Each finding was confirmed by reading the code directly,
       not by regex nor by a model. The Python trees ship triplicated, so
       finding 2 expands across all three copies.

Writes ground_truth.json. Re-runnable; verifies every anchor against the corpus.
"""
import json
from collections import defaultdict
from pathlib import Path

CORPUS = Path("corpus")
VFC = "VMware-Fleet-Console/VMware-Fleet-Console/{os}/src/vfc/connection.py"

FINDINGS = [
    {
        "id": "GT-1",
        "file": "Projecto-de-escola/menu_admin.php",
        "line": 1,
        "severity": "high",
        "title": "admin panel has no session_start() and no auth check",
        "detail": (
            "menu_admin.php is 10 lines of pure HTML. It never calls session_start() "
            "and never tests $_SESSION['nivel_utilizador']. Anyone who types the URL "
            "gets the admin menu; login is bypassable outright."
        ),
        "evidence_kind": "absence",
        "expect_text": None,
    },
    {
        "id": "GT-2",
        "file": VFC,
        "line": 627,
        "severity": "high",
        "title": "TOCTOU in certificate pinning: pin checked on one connection, credentials sent on another",
        "detail": (
            "fetch_certificate() (line 168) opens a connection with CERT_NONE at 186-187 "
            "to read the fingerprint, and evaluate_trust() (line 222) judges it. connect() "
            "(line 528) then opens a NEW connection via _build_context() (line 607), which "
            "sets CERT_NONE again at 626-627, and sends the password without re-checking the "
            "pin during the handshake. Fix: load_verify_locations(cadata=...) plus "
            "verify_mode=CERT_REQUIRED so OpenSSL enforces the pin in-handshake."
        ),
        "evidence_kind": "line",
        "expect_text": "verify_mode = ssl.CERT_NONE",
    },
    {
        "id": "GT-3",
        "file": "Projecto-de-escola/verifica_login.php",
        "line": 19,
        "severity": "high",
        "title": "$_SESSION populated before the row-count guard",
        "detail": (
            "Lines 19-21 assign $_SESSION['id_cliente'], ['nome_cliente'] and "
            "['nivel_utilizador'] before the mysql_num_rows($consulta)!=1 guard at line 22. "
            "A failed login has already written session state by the time the guard redirects."
        ),
        "evidence_kind": "line",
        "expect_text": "$_SESSION['id_cliente']=$resultado['id_utilizador'];",
    },
    {
        "id": "GT-4",
        "file": "Projecto-de-escola/verifica_login.php",
        "line": 19,
        "severity": "med",
        "title": "session read from column names the query never selects",
        "detail": (
            "Line 15 selects id_cliente, nome_login, palavra_passe, nivel_utilizador. "
            "Lines 19-20 read $resultado['id_utilizador'] and ['nome_utilizador'] -- keys "
            "that never exist in the row, so those session values are always NULL."
        ),
        "evidence_kind": "line",
        "expect_text": "$resultado['id_utilizador']",
    },
]


def expand(f: dict) -> list[dict]:
    """Triplicated Python trees: one hand-verified finding is three on disk."""
    if "{os}" not in f["file"]:
        return [dict(f)]
    out = []
    for os_name in ("Linux", "Windows", "macOS"):
        c = dict(f)
        c["file"] = f["file"].format(os=os_name)
        c["id"] = f"{f['id']}-{os_name}"
        c["duplicate_of"] = f["id"]
        out.append(c)
    return out


def verify(f: dict) -> str:
    """Confirm the anchor still points at what was verified by hand."""
    p = CORPUS / f["file"]
    if not p.exists():
        return "MISSING FILE"
    if f["evidence_kind"] == "absence":
        return "ok (absence)" if "session_start" not in p.read_text(
            encoding="utf-8", errors="replace") else "STALE: session_start now present"
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    if f["line"] > len(lines):
        return "LINE OUT OF RANGE"
    return "ok" if f["expect_text"] in lines[f["line"] - 1] else "STALE: text moved"


# Which findings could the LLM stage ever surface? It only ever sees stage-1
# candidates, so anything absent from the prefilter is unreachable by design.
# Tracked per stage-1 version, because that is exactly what v2 set out to change.
def candidates(fname: str) -> defaultdict:
    cand = defaultdict(list)
    p = Path(fname)
    if not p.exists():
        return cand
    for c in json.loads(p.read_text())["findings"]:
        cand[c["file"]].append(c["line"])
    return cand


STAGE1 = {"v1": candidates("prefilter.json"), "v2": candidates("prefilter_v2.json")}

records = []
for f in FINDINGS:
    for item in expand(f):
        item["verified"] = True
        item["verified_by"] = "claude-read-the-code"
        item["anchor_check"] = verify(item)
        item["reachability"] = {}
        for ver, cand in STAGE1.items():
            near = sorted(l for l in cand.get(item["file"], [])
                          if abs(l - item["line"]) <= 8)
            item["reachability"][ver] = {
                "file_in_candidate_set": item["file"] in cand,
                "prefilter_found_the_line": item["line"] in cand.get(item["file"], []),
                "candidate_lines_within_context": near,
                "reachable": bool(near),
            }
        records.append(item)

doc = {
    "purpose": (
        "Hand-verified ground truth for scoring triage_<model>.json. The metric that "
        "matters is each model's hallucination rate on candidates it WAS shown, plus "
        "its recall on the findings it could reach."
    ),
    "established": "2026-09-21",
    "corpus_note": (
        "Python projects ship triplicated Linux/Windows/macOS trees, so ~615 scanned "
        "files are ~205 unique ones and each Python finding appears three times."
    ),
    "unique_findings": len(FINDINGS),
    "records": len(records),
    "findings": records,
}
Path("ground_truth.json").write_text(json.dumps(doc, indent=2))

print(f"{len(FINDINGS)} hand-verified findings -> {len(records)} records\n")
print(f"  {'id':14s} {'anchor':14s} {'v1':>11s} {'v2':>11s}  file:line")
for r in records:
    v1 = "reachable" if r["reachability"]["v1"]["reachable"] else "UNREACHABLE"
    v2 = "reachable" if r["reachability"]["v2"]["reachable"] else "UNREACHABLE"
    print(f"  {r['id']:14s} {r['anchor_check']:14s} {v1:>11s} {v2:>11s}  "
          f"{r['file']}:{r['line']}")
