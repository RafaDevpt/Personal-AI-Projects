#!/usr/bin/env bash
# Detached triage run. Survives terminal close: launched via setsid, and the
# ollama backend is a lingering systemd --user service.
set -u
cd /data/llm-audit

export PATH="$HOME/.local/bin:$PATH"

echo "=== started $(date -Is) ==="
for model in qwen2.5-coder:3b qwen2.5-coder:7b qwen3:8b; do
  out="triage_$(echo "$model" | tr ':.' '__').json"
  echo "--- $model -> $out"
  python3 llm_triage.py "$model" "$out"
  echo "--- $model done rc=$? $(date -Is)"
done
echo "=== finished $(date -Is) ==="
