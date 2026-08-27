# Contribuir · Contributing

**PT** · Obrigado pelo interesse. Este documento descreve como propor
alterações.
**EN** · Thank you for your interest. This document describes how to propose
changes.

---

## Antes de tudo · Before anything else

> **PT** · **Nunca** inclua áudio, transcrições, nomes de doentes ou o
> ficheiro `learned_corrections.json` num commit, issue ou pull request. São
> dados de saúde ao abrigo do artigo 9.º do RGPD. Ao reportar um problema, use
> texto de exemplo inventado.
>
> **EN** · **Never** include audio, transcriptions, patient names or the
> `learned_corrections.json` file in a commit, issue or pull request. These are
> health data under Article 9 of the GDPR. When reporting a problem, use
> invented sample text.

---

## Ambiente · Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

```bash
pytest                            # testes
pytest --cov=transcriber          # com cobertura
ruff check src/ tests/            # análise estática
```

---

## Estilo de código · Code style

- **Comentários e docstrings em PT-PT e EN-UK**, nesta ordem. É a convenção do
  projeto e aplica-se a todo o código novo.
- Comentar o **porquê**, não o **quê**. `# incrementa i` não acrescenta nada;
  `# ordena por comprimento para os termos compostos ganharem` sim.
- Type hints em todas as funções públicas.
- `pathlib.Path` em vez de `os.path`.
- Exceções específicas. Nunca `except:` nu.
- `logging`, nunca `print()` — exceto na saída do modo `--batch`.
- Linhas até 100 caracteres.

---

## Acrescentar termos médicos · Adding medical terms

**PT** · O ficheiro `src/transcriber/medical_terms.py` contém apenas dados e é
o único que pode ser editado sem saber programar. Tem três estruturas:

| Estrutura | Para quê |
|---|---|
| `SPELLING_CORRECTIONS` | Erros de transcrição frequentes. Só pares em que a chave difere do valor. |
| `BRAZILIAN_TO_EUROPEAN` | Formas pt-BR que o modelo produz. |
| `PROTECTED_TERMS` | Vocabulário entregue ao modelo antes da descodificação. Mantenha abaixo de ~200 termos: o prompt está limitado a 224 tokens. |

**PT** · Não acrescente pares idênticos (`"febre": "febre"`) — não fazem nada.
Se um termo sai mal transcrito, o sítio certo é `PROTECTED_TERMS`.

---

## Pull requests

1. Ramo a partir de `main`: `git checkout -b feat/descricao-curta`
2. Testes a passar e um teste novo por cada correção de bug
3. Commits no formato [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
4. Atualize o `CHANGELOG.md` na secção *Unreleased*
5. Descreva **o problema** que resolve, não apenas o que alterou

---

## Reportar problemas · Reporting issues

Inclua: sistema operativo, versão do Python, modelo usado, o que esperava, o
que aconteceu, e as linhas relevantes do registo (`--verbose`) **depois de
confirmar que não contêm dados de doentes**.

---

*Created by Redfox using Claude*
