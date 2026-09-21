#!/usr/bin/env python3
"""Stage 1 v2: regex triage plus whole-file rules for things that are ABSENT.

PT-PT: A v1 so procurava texto presente. Um painel de administracao sem
       `session_start()` nao tem texto nenhum para casar -- o defeito e a
       ausencia. Dai as FILE_RULES, que julgam o ficheiro inteiro.
EN-UK: v1 only ever matched text that is present. An admin panel with no
       `session_start()` has no text to match -- the defect is the absence.
       Hence FILE_RULES, which judge the whole file.

Emits prefilter_v2.json. Same over-report-on-purpose stance as v1: stage 2
(local LLM) and stage 3 (Claude) do the filtering.

Usage: prefilter_v2.py [corpus_dir]
"""
import json
import re
import sys
from pathlib import Path

CORPUS = Path(sys.argv[1] if len(sys.argv) > 1 else "corpus")

# ---------------------------------------------------------------------------
# Line rules -- carried over from v1 unchanged, so v1 candidates stay a subset.
# ---------------------------------------------------------------------------
RULES = [
    ("shell-true",   "high", "py",  r"subprocess\.(run|call|check_output|check_call|Popen)\((?:[^)]*?)shell\s*=\s*True", "subprocess with shell=True"),
    ("os-system",    "high", "py",  r"\bos\.(system|popen)\s*\(",                      "os.system/os.popen invocation"),
    ("py-eval",      "high", "py",  r"(?<![\w.])(eval|exec)\s*\(",                      "eval/exec on runtime value"),
    ("php-eval",     "high", "php", r"(?<![\w.])(eval|assert|system|exec|passthru|shell_exec)\s*\(", "PHP code/command execution"),

    ("pickle",       "high", "py",  r"pickle\.loads?\s*\(",                             "pickle deserialisation"),
    ("yaml-unsafe",  "high", "py",  r"yaml\.load\s*\((?![^)]*Safe)",                    "yaml.load without SafeLoader"),

    ("sql-fstring",  "high", "py",  r"(execute|executemany)\s*\(\s*f[\"']",             "SQL built with f-string"),
    ("sql-concat",   "high", "py",  r"(execute|executemany)\s*\([^)]*(%\s|\+\s*\w+|\.format\()", "SQL built by concat/format"),
    ("php-sql-var",  "high", "php", r"(mysql_query|mysqli_query|->query)\s*\(\s*[\"'][^\"']*\$",  "SQL string interpolating a variable"),
    ("php-superglob-sql", "high", "php", r"\$sql\s*=.*\$_(GET|POST|REQUEST|COOKIE)",    "superglobal flows straight into SQL"),
    ("php-sql-interp", "high", "php", r"\$\w+\s*=\s*[\"'].*\b(SELECT|INSERT|UPDATE|DELETE)\b.*\$\w+", "SQL string built with an interpolated variable"),
    ("py-sql-interp", "high", "py",  r"=\s*f?[\"'].*\b(SELECT|INSERT|UPDATE|DELETE)\b.*(\{\w|%s|[\"']\s*\+|\.format\()", "SQL string built by interpolation"),

    ("php-mysql-ext", "med", "php", r"\bmysql_(connect|query|select_db|num_rows|fetch_\w+|free_result|error)\s*\(", "removed mysql_* extension (dead on PHP>=7)"),

    ("hardcoded-secret", "high", "*", r"(?i)(password|passwd|api[_-]?key|secret|token|bearer)\s*[:=]\s*[\"'][^\"'{}$\s]{6,}[\"']", "possible hardcoded credential"),
    ("php-db-creds",  "high", "php", r"mysql(i)?_connect\s*\([^)]*[\"'][^\"']*[\"']\s*,\s*[\"'][^\"']*[\"']", "inline DB credentials"),

    ("verify-false", "high", "py",  r"verify\s*=\s*False",                              "TLS verification disabled"),
    ("ssl-unverified", "high", "py", r"ssl\._create_unverified_context|CERT_NONE",       "unverified SSL context"),
    ("weak-hash",    "med",  "*",   r"(?i)(md5|sha1)\s*\(",                             "weak hash (md5/sha1)"),
    ("paramiko-auto", "med", "py",  r"AutoAddPolicy",                                   "SSH host key auto-accept"),

    ("php-xss",      "high", "php", r"echo\s+\$_(GET|POST|REQUEST|COOKIE)",             "superglobal echoed unescaped (XSS)"),
    ("php-lfi",      "high", "php", r"(include|require)(_once)?\s*\(?\s*\$",            "dynamic include (LFI risk)"),
    ("flask-debug",  "med",  "py",  r"\.run\([^)]*debug\s*=\s*True",                    "Flask debug mode enabled"),
    ("bind-all",     "med",  "py",  r"[\"']0\.0\.0\.0[\"']",                            "binds all interfaces"),

    ("mktemp",       "med",  "py",  r"tempfile\.mktemp\s*\(",                           "insecure tempfile.mktemp"),
    ("chmod-777",    "med",  "*",   r"(chmod\s+777|0o777)",                             "world-writable permissions"),
]

COMPILED = [(i, s, l, re.compile(p), d) for i, s, l, p, d in RULES]

EXT_LANG = {".py": "py", ".php": "php", ".sh": "sh", ".ps1": "ps1"}

# ---------------------------------------------------------------------------
# File rules -- the defect is what the file does NOT do.
# ---------------------------------------------------------------------------
RENDERS_UI = re.compile(r"<(html|body|table|form|a\s+href)", re.I)
LINKS_PHP = re.compile(r"href\s*=\s*[\"'][^\"']+\.php", re.I)
HAS_SESSION_START = re.compile(r"session_start\s*\(")
READS_SESSION = re.compile(r"\$_SESSION\s*\[")
# Pages whose name or content says "privileged". Kept deliberately broad.
PRIVILEGED = re.compile(
    r"(admin|administrador|gerir|gestao|backoffice|painel|"
    r"adicionar_|remover_|apagar_|eliminar_|editar_|atualizar_|estado_encomenda)", re.I)


def rule_unauthenticated_page(path, text, lines):
    """PHP page that renders UI but establishes no session and checks nothing."""
    if path.suffix.lower() != ".php":
        return None
    if not RENDERS_UI.search(text) or not LINKS_PHP.search(text):
        return None
    if HAS_SESSION_START.search(text) or READS_SESSION.search(text):
        return None
    privileged = bool(PRIVILEGED.search(path.name) or PRIVILEGED.search(text))
    return {
        "rule": "php-no-auth-gate",
        "severity": "high" if privileged else "med",
        "desc": ("privileged page with no session_start() and no authorisation check"
                 if privileged else
                 "page renders UI with no session_start() and no authorisation check"),
        "line": 1,
        "code": (lines[0].strip()[:200] if lines else ""),
        "evidence_kind": "absence",
        "whole_file": True,
    }


def rule_session_read_without_start(path, text, lines):
    """Reads $_SESSION for a decision but never starts the session."""
    if path.suffix.lower() != ".php":
        return None
    if not READS_SESSION.search(text) or HAS_SESSION_START.search(text):
        return None
    m = READS_SESSION.search(text)
    line_no = text[:m.start()].count("\n") + 1
    return {
        "rule": "php-session-no-start",
        "severity": "high",
        "desc": "reads $_SESSION without session_start(); the value is always empty",
        "line": line_no,
        "code": lines[line_no - 1].strip()[:200] if line_no <= len(lines) else "",
        "evidence_kind": "absence",
        "whole_file": True,
    }


FILE_RULES = [rule_unauthenticated_page, rule_session_read_without_start]


findings = []
scanned = 0

for path in sorted(CORPUS.rglob("*")):
    if not path.is_file():
        continue
    lang = EXT_LANG.get(path.suffix.lower())
    if lang is None:
        continue
    scanned += 1
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue

    lines = text.splitlines()

    for rule_id, sev, rlang, rx, desc in COMPILED:
        if not (rlang == "*" or rlang == lang):
            continue
        for n, line in enumerate(lines, 1):
            if len(line) > 400:
                continue
            if rx.search(line):
                findings.append({
                    "rule": rule_id,
                    "severity": sev,
                    "desc": desc,
                    "file": str(path.relative_to(CORPUS)),
                    "line": n,
                    "code": line.strip()[:200],
                    "evidence_kind": "line",
                    "whole_file": False,
                })

    for fr in FILE_RULES:
        hit = fr(path, text, lines)
        if hit:
            hit["file"] = str(path.relative_to(CORPUS))
            findings.append(hit)

by_file = {}
for f in findings:
    by_file.setdefault(f["file"], []).append(f)

out = {
    "scanned_files": scanned,
    "candidate_findings": len(findings),
    "files_with_hits": len(by_file),
    "findings": findings,
}
Path("prefilter_v2.json").write_text(json.dumps(out, indent=2))

print(f"scanned files      : {scanned}")
print(f"files with hits    : {len(by_file)}  ({len(by_file)*100//max(scanned,1)}% of corpus)")
print(f"candidate findings : {len(findings)}")
print()
counts = {}
for f in findings:
    k = (f["severity"], f["rule"], f["desc"])
    counts[k] = counts.get(k, 0) + 1
print(f"{'sev':5} {'rule':22} {'n':>5}  description")
for (sev, rule, desc), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][1])):
    print(f"{sev:5} {rule:22} {n:>5}  {desc}")
