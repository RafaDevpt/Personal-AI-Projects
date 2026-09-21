# Auditoria de segurança — 2026-09-21/22

**PT-PT:** O relatório está em [`RELATORIO.md`](RELATORIO.md). Isto é o banco de
ensaio que o produziu, guardado aqui porque o contentor onde correu é efémero.

**EN-UK:** The report is in [`RELATORIO.md`](RELATORIO.md). This is the test rig
that produced it, kept here because the container it ran in is ephemeral.

## O funil / The funnel

```
corpus  ->  prefilter_v2.py  ->  llm_triage_v2.py  ->  score_triage.py
            (expressões          (modelo local,        (contra
             regulares +          em lotes de 6)        ground_truth.json)
             regras de
             ficheiro inteiro)
```

| ficheiro | o que faz |
|---|---|
| `prefilter.py` / `prefilter_v2.py` | Etapa 1. A v2 acrescenta regras de ficheiro inteiro, para defeitos que são uma **ausência** — um painel sem `session_start()` não tem texto para casar. |
| `llm_triage.py` / `llm_triage_v2.py` | Etapa 2. A v2 usa lotes de 6, guarda a resposta em bruto, e abre um canal `EXTRA` para o modelo relatar o que não lhe foi perguntado. |
| `build_ground_truth.py` → `ground_truth.json` | Os quatro achados confirmados à mão, com verificação de que as âncoras ainda apontam ao sítio certo. |
| `score_triage.py` → `scores.json` | Pontua cada corrida: taxa de excesso, recall, e o que precisa de um humano. |
| `run_v2.sh` | Corrida completa dos três modelos. Recusa arrancar com a v1 a correr. |

## Correr de novo / Re-running

```bash
python3 prefilter_v2.py            # etapa 1  (rápido, determinístico)
python3 build_ground_truth.py      # verifica as âncoras contra o corpus
./run_v2.sh                        # três modelos + pontuação
```

O `corpus/` **não** está aqui: são cópias dos próprios repositórios, e duplicá-las
no git não servia de nada. O `run_v2.sh` espera encontrá-lo em `./corpus`.

## O que isto mediu / What this measured

O ponto não era auditar o código — era medir os modelos locais. O número que
saiu: **96% dos veredictos do `qwen2.5-coder:3b` são previsíveis só a partir do
nome da regra**, e chamou `FALSE_POSITIVE` ao único contorno de autenticação
genuíno que lhe foi mostrado. Está tudo em `RELATORIO.md`.

---

*Created by Redfox using Claude*
