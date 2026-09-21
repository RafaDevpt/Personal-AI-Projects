#!/usr/bin/env bash
# Detached v2 sweep. Survives terminal close: launch via setsid, and the ollama
# backend is a lingering systemd --user service.
#
# PT-PT: Nao arrancar isto com a corrida v1 ainda a andar. O llama-server corre
#        com -np 1, portanto os dois pedidos ficam em fila e cada corrida fica
#        ao dobro do tempo, sem ganho nenhum.
# EN-UK: Do not start this while the v1 sweep is still going. llama-server runs
#        with -np 1, so the two would queue behind each other and both runs take
#        twice as long for no gain.
set -u
cd /data/llm-audit

export PATH="$HOME/.local/bin:$PATH"

if pgrep -f 'llm_triage\.py' >/dev/null; then
  echo "refusing to start: the v1 sweep is still running" >&2
  exit 1
fi

# Stage 1 is cheap and deterministic; regenerate so the candidate set matches.
python3 prefilter_v2.py || exit 1
python3 build_ground_truth.py || exit 1

echo "=== v2 started $(date -Is) ==="
for model in qwen2.5-coder:3b qwen2.5-coder:7b qwen3:8b; do
  out="triage_v2_$(echo "$model" | tr ':.' '__').json"
  echo "--- $model -> $out"
  python3 llm_triage_v2.py "$model" "$out" prefilter_v2.json
  echo "--- $model done rc=$? $(date -Is)"
done
echo "=== v2 finished $(date -Is) ==="

python3 score_triage.py triage_v2_*.json
