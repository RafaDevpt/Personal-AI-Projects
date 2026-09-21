#!/usr/bin/env python3
"""Stage 1 of the funnel: cheap regex triage over the corpus.

Emits candidate findings as JSON. No judgement here on purpose -- this stage is
tuned to over-report, because stage 2 (local LLM) and stage 3 (Claude) filter.
"""
import json
import re
import sys
from pathlib import Path

CORPUS = Path(sys.argv[1] if len(sys.argv) > 1 else "corpus")

# (id, severity, language, compiled pattern, description)
RULES = [
    # --- command / code execution -------------------------------------------
    ("shell-true",   "high", "py",  r"subprocess\.(run|call|check_output|check_call|Popen)\((?:[^)]*?)shell\s*=\s*True", "subprocess with shell=True"),
    ("os-system",    "high", "py",  r"\bos\.(system|popen)\s*\(",                      "os.system/os.popen invocation"),
    ("py-eval",      "high", "py",  r"(?<![\w.])(eval|exec)\s*\(",                      "eval/exec on runtime value"),
    ("php-eval",     "high", "php", r"(?<![\w.])(eval|assert|system|exec|passthru|shell_exec)\s*\(", "PHP code/command execution"),

    # --- deserialisation -----------------------------------------------------
    ("pickle",       "high", "py",  r"pickle\.loads?\s*\(",                             "pickle deserialisation"),
    ("yaml-unsafe",  "high", "py",  r"yaml\.load\s*\((?![^)]*Safe)",                    "yaml.load without SafeLoader"),

    # --- SQL -----------------------------------------------------------------
    ("sql-fstring",  "high", "py",  r"(execute|executemany)\s*\(\s*f[\"']",             "SQL built with f-string"),
    ("sql-concat",   "high", "py",  r"(execute|executemany)\s*\([^)]*(%\s|\+\s*\w+|\.format\()", "SQL built by concat/format"),
    ("php-sql-var",  "high", "php", r"(mysql_query|mysqli_query|->query)\s*\(\s*[\"'][^\"']*\$",  "SQL string interpolating a variable"),
    ("php-superglob-sql", "high", "php", r"\$sql\s*=.*\$_(GET|POST|REQUEST|COOKIE)",    "superglobal flows straight into SQL"),
    # The common real-world shape: query assembled into a var on one line, executed on
    # another. The two-line split is why a line-oriented matcher misses live SQLi.
    ("php-sql-interp", "high", "php", r"\$\w+\s*=\s*[\"'].*\b(SELECT|INSERT|UPDATE|DELETE)\b.*\$\w+", "SQL string built with an interpolated variable"),
    ("py-sql-interp", "high", "py",  r"=\s*f?[\"'].*\b(SELECT|INSERT|UPDATE|DELETE)\b.*(\{\w|%s|[\"']\s*\+|\.format\()", "SQL string built by interpolation"),

    # --- deprecated / dead APIs ---------------------------------------------
    ("php-mysql-ext", "med", "php", r"\bmysql_(connect|query|select_db|num_rows|fetch_\w+|free_result|error)\s*\(", "removed mysql_* extension (dead on PHP>=7)"),

    # --- secrets -------------------------------------------------------------
    ("hardcoded-secret", "high", "*", r"(?i)(password|passwd|api[_-]?key|secret|token|bearer)\s*[:=]\s*[\"'][^\"'{}$\s]{6,}[\"']", "possible hardcoded credential"),
    ("php-db-creds",  "high", "php", r"mysql(i)?_connect\s*\([^)]*[\"'][^\"']*[\"']\s*,\s*[\"'][^\"']*[\"']", "inline DB credentials"),

    # --- transport / crypto --------------------------------------------------
    ("verify-false", "high", "py",  r"verify\s*=\s*False",                              "TLS verification disabled"),
    ("ssl-unverified", "high", "py", r"ssl\._create_unverified_context|CERT_NONE",       "unverified SSL context"),
    ("weak-hash",    "med",  "*",   r"(?i)(md5|sha1)\s*\(",                             "weak hash (md5/sha1)"),
    ("paramiko-auto", "med", "py",  r"AutoAddPolicy",                                   "SSH host key auto-accept"),

    # --- web / templating ----------------------------------------------------
    ("php-xss",      "high", "php", r"echo\s+\$_(GET|POST|REQUEST|COOKIE)",             "superglobal echoed unescaped (XSS)"),
    ("php-lfi",      "high", "php", r"(include|require)(_once)?\s*\(?\s*\$",            "dynamic include (LFI risk)"),
    ("flask-debug",  "med",  "py",  r"\.run\([^)]*debug\s*=\s*True",                    "Flask debug mode enabled"),
    ("bind-all",     "med",  "py",  r"[\"']0\.0\.0\.0[\"']",                            "binds all interfaces"),

    # --- filesystem ----------------------------------------------------------
    ("mktemp",       "med",  "py",  r"tempfile\.mktemp\s*\(",                           "insecure tempfile.mktemp"),
    ("chmod-777",    "med",  "*",   r"(chmod\s+777|0o777)",                             "world-writable permissions"),
]

COMPILED = [(i, s, l, re.compile(p), d) for i, s, l, p, d in RULES]

EXT_LANG = {".py": "py", ".php": "php", ".sh": "sh", ".ps1": "ps1"}


def lang_matches(rule_lang, file_lang):
    return rule_lang == "*" or rule_lang == file_lang


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
        if not lang_matches(rlang, lang):
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
                })

by_file = {}
for f in findings:
    by_file.setdefault(f["file"], []).append(f)

out = {
    "scanned_files": scanned,
    "candidate_findings": len(findings),
    "files_with_hits": len(by_file),
    "findings": findings,
}
Path("prefilter.json").write_text(json.dumps(out, indent=2))

print(f"scanned files      : {scanned}")
print(f"files with hits    : {len(by_file)}  ({len(by_file)*100//max(scanned,1)}% of corpus)")
print(f"candidate findings : {len(findings)}")
print()
counts = {}
for f in findings:
    counts[(f["severity"], f["rule"], f["desc"])] = counts.get((f["severity"], f["rule"], f["desc"]), 0) + 1
print(f"{'sev':5} {'rule':22} {'n':>5}  description")
for (sev, rule, desc), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][1])):
    print(f"{sev:5} {rule:22} {n:>5}  {desc}")
print()
print("top files:")
for fn, fs in sorted(by_file.items(), key=lambda kv: -len(kv[1]))[:12]:
    print(f"  {len(fs):>3}  {fn}")
