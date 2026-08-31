# Contribuir · Contributing

**PT** · Obrigado pelo interesse.
**EN** · Thank you for your interest.

---

## Antes de tudo · Before anything else

> **PT** · **Nunca** inclua num commit, issue ou pull request: gravações reais,
> transcrições reais, nomes de doentes, dados clínicos, ou capturas de ecrã com
> qualquer uma dessas coisas.
>
> Este projecto trata de áudio de consultas médicas. Um ficheiro de exemplo com
> conteúdo verdadeiro é uma violação de dados, não um caso de teste. Use áudio
> inventado, gravado por si, sem nada que identifique ninguém.
>
> **EN** · **Never** include real recordings, real transcriptions, patient
> names, clinical data, or screenshots containing any of them. This project
> handles audio from medical consultations. A sample file with real content is a
> data breach, not a test case.

---

## A regra que define este projecto

**Há três versões independentes — `Windows/`, `Linux/` e `macOS/` — e cada uma
é uma cópia completa da aplicação.**

Isto é uma escolha deliberada, e tem um custo que não se pode ignorar: **uma
alteração ao código partilhado tem de ser aplicada três vezes.**

Não há aqui automatismo nenhum a proteger-nos disso. A única defesa é o hábito e
a lista abaixo.

### O que é partilhado e o que não é

| Ficheiro | Igual nas três? |
| :--- | :--- |
| `src/transcriber/platform_support.py` | **Não.** É o que distingue as versões |
| `tests/test_platform_support.py` | **Não.** Cada um testa o seu sistema |
| `pyproject.toml` | Quase — o `name` do pacote é diferente |
| `LEIA-ME.md` | **Não.** São instruções de sistemas diferentes |
| Lançadores (`.bat`, `.sh`, `.command`) | **Não** |
| **Todo o resto de `src/` e `tests/`** | **Sim.** `engine.py`, `corrections.py`, `config.py`, `exporters.py`, `recorder.py`, `languages/`, `gui/`… |

### Como aplicar uma alteração partilhada

1. Faça a alteração numa das versões — a do sistema em que está a trabalhar
2. Corra os testes **dessa** versão
3. Copie o ficheiro alterado para as outras duas
4. Corra os testes das outras duas — dá para as três a partir de uma máquina só,
   porque os testes passam os valores de sistema como argumentos
5. Confirme com `git diff --stat` que a alteração aparece em três sítios

```bash
# PT-PT: confirmar que os ficheiros partilhados estao alinhados.
#        O `-x` exclui o __pycache__ e o platform_support.py -- o primeiro
#        porque difere sempre e nao quer dizer nada, o segundo porque e o
#        ficheiro que *deve* ser diferente.
diff -r --brief -x '__pycache__' -x 'platform_support.py' \
     Windows/src/transcriber Linux/src/transcriber

diff -r --brief -x '__pycache__' -x 'test_platform_support.py' \
     Windows/tests Linux/tests
```

Se algum destes comandos devolver alguma coisa, as versões divergiram num
ficheiro que devia ser igual. Repita para o `macOS/`.

### Quando a alteração é específica de um sistema

Aí é o contrário: **fica só numa pasta**, e o sítio dela é o
`platform_support.py` dessa versão. Se sentir vontade de escrever um
`if sys.platform` dentro de uma das versões, é porque a alteração pertence a
outro sítio — e há um teste em cada versão que falha precisamente nesse caso.

---

## Ambiente · Environment

Trabalhe dentro da pasta da sua versão. Cada uma tem o seu ambiente virtual.

```bash
cd Linux            # ou Windows, ou macOS
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

```bash
pytest                            # testes
pytest --cov=transcriber          # com cobertura
ruff check .                      # análise estática
mypy src/                         # tipos
```

---

## Testes

**Nenhum teste precisa de áudio, de microfone ou de rede.** A suite tem de
correr numa máquina sem nada disso, num runner de integração contínua, e em
menos de dois segundos.

Os testes de plataforma recebem o sistema e o `/etc/os-release` como argumentos,
o que permite verificar as onze famílias de distribuição a partir de qualquer
máquina. Um teste que precisasse de uma Fedora a sério não correria na
integração contínua e, por isso, não correria nunca.

A integração contínua corre as três versões nos runners nativos —
`windows-latest`, `ubuntu-latest` e `macos-latest`. É aí que um erro de porte
aparece.

---

## Acrescentar uma língua

Um pacote clínico novo vive em `src/transcriber/languages/`, e é o exemplo
perfeito de alteração partilhada: **tem de entrar nas três versões**.

O pacote é só dados — correcções ortográficas, conversão de variante, pontuação
ditada, vocabulário protegido — e deve poder ser revisto por alguém com formação
clínica sem saber Python.

### Duas regras que não se negoceiam

**Nomes de fármacos parecidos entre si nunca entram nas tabelas de
substituição.** Trocar «hydralazine» por «hydroxyzine» mata pessoas, e um
dicionário automático não tem informação nenhuma para decidir qual era. Esses
nomes vão para o vocabulário protegido, que ajuda o modelo a ouvir bem à
primeira.

**As abreviaturas da lista proibida do ISMP não são expandidas.** Estão nessa
lista precisamente por serem ambíguas.

---

## Estilo · Style

- Documentação bilingue PT-PT / EN-UK em todos os módulos, classes e funções
- `from __future__ import annotations` no topo
- Tipos em todas as assinaturas públicas
- `ruff` limpo sob a configuração do `pyproject.toml`
- Nada de `print()` fora do `__main__.py`
- Nenhum módulo fora de `gui/` importa `customtkinter`

---

## O que não vai ser aceite

- **Um `if sys.platform` dentro de uma das versões.** É o que as três pastas
  existem para evitar, e há um teste que o apanha
- **Uma alteração partilhada aplicada só numa versão.** As outras duas passam a
  ter um defeito que já foi corrigido, e ninguém dá por isso até alguém reportar
  o mesmo problema outra vez
- **Áudio ou texto clínico verdadeiro**, em qualquer forma
- **Uma correcção automática entre nomes de fármacos semelhantes**

---

<sub>Created by Redfox using Claude</sub>
