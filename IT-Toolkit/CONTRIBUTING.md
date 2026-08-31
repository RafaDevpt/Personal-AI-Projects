# Contribuir · Contributing

**PT** · Obrigado pelo interesse. Este documento descreve como propor
alterações.
**EN** · Thank you for your interest. This document describes how to propose
changes.

---

## A regra que define este projecto

**Há três versões independentes — `Windows/`, `Linux/` e `macOS/` — e cada uma é
uma aplicação completa.**

Aqui isto vai mais longe do que nos projectos irmãos deste repositório. Nos
outros, as três versões partilham quase todo o `src/` e distinguem-se num
ficheiro. **Neste, quase nada é partilhado**, e não podia ser: a versão de
Windows lê event logs por `wevtutil` e WMI, a de Linux lê o diário do systemd e
o `/sys`, a de macOS lê o diário unificado, o `launchd` e o `diskutil`. São três
aplicações que respondem à mesma pergunta em sítios diferentes.

### O que é partilhado e o que não é

| Ficheiro | Igual nas três? |
| :--- | :--- |
| `shell.py`, `events.py`, `knowledge.py` | **Não.** São o sistema operativo |
| `services.py`, `disks.py`, `network.py`, `inventory.py`, `system.py` | **Não.** Idem |
| `actions.py`, `platform_support.py` | **Não.** Idem |
| `models.py` | Quase — o `Gravidade` e o `Achado` são iguais, o `Regra` e o `GrupoEventos` têm chaves diferentes |
| `reports.py`, `config.py`, `logging_setup.py`, `gui/` | Quase — a estrutura é a mesma, o vocabulário muda |
| `LEIA-ME.md` e lançadores | **Não.** São instruções de sistemas diferentes |

### O que isto custa, e como se paga

Uma correcção ao HTML dos relatórios, ao carregamento da configuração ou ao
comportamento da interface **tem de ser aplicada três vezes**. Não há
automatismo nenhum a proteger-nos disso; a única defesa é o hábito.

1. Faça a alteração na versão do sistema em que está a trabalhar
2. Corra os testes **dessa** versão
3. Aplique o equivalente nas outras duas — equivalente, e não cópia: o mesmo
   ficheiro fala de event logs numa, do diário do systemd noutra
4. Corra os testes das outras duas. Dá para as três a partir de uma máquina só,
   porque nenhum teste toca no sistema
5. Confirme o que devia ficar mesmo igual:

```bash
diff Windows/src/ittoolkit/logging_setup.py Linux/src/ittoolkit/logging_setup.py
diff Windows/src/ittoolkit/gui/theme.py Linux/src/ittoolkit/gui/theme.py
```

### Quando a alteração é específica de um sistema

Aí é o contrário: **fica só numa pasta**. Se sentir vontade de escrever um
`if sys.platform` dentro de uma das versões, é porque a alteração pertence a
outro sítio — e há um teste em cada versão que falha precisamente nesse caso.

---

## Antes de tudo · Before anything else

> **PT** · **Nunca** inclua relatórios gerados, nomes de máquina, endereços IP
> reais, números de série, nomes de utilizador ou capturas de ecrã com o
> ambiente visível num commit, issue ou pull request. Um relatório desta
> ferramenta é um retrato completo de uma máquina interna. Ao reportar um
> problema, substitua os endereços por `10.0.0.x`, os nomes de máquina por
> `PC-EXEMPLO` e apague as mensagens de erro que contenham caminhos de rede.
>
> **EN** · **Never** include generated reports, machine names, real IP
> addresses, serial numbers, user names or screenshots showing the environment
> in a commit, issue or pull request. A report from this tool is a complete
> portrait of an internal machine.

---

## Ambiente · Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

```bash
pytest                            # testes
pytest --cov=ittoolkit            # com cobertura
ruff check src/ tests/            # análise estática
```

**PT** · Os testes das três versões correm em qualquer sistema operativo, de
propósito. O que depende do sistema entra por argumento — o conteúdo do
`/etc/os-release`, o UID, a saída do `launchctl list` — e é por isso que se
consegue verificar as três a partir de uma máquina só antes de as mandar para a
integração contínua, onde cada uma corre no seu runner nativo.

---

## Testes · Tests

**PT** · Duas regras inegociáveis.

**Nenhum teste toca no sistema.** As respostas das ferramentas do sistema são
fixtures — dicionários com a forma que o `ConvertTo-Json`, o `journalctl -o
json` ou o `log show --style ndjson` produzem. Se precisar de uma resposta nova,
acrescente a fixture; não vá buscá-la a uma máquina real durante a execução dos
testes.

É por isso que o módulo `events` está partido em duas metades nas três versões:
a leitura toca no sistema, a análise só vê dicionários. A divisão é a mesma em
Windows, Linux e macOS, e é o que permite testar o agrupamento, a recorrência e
o veredicto sem um event log, sem um diário e sem um Mac.

**O `customtkinter` não é instalado na integração contínua.** A lógica de
recolha e de relatórios tem de continuar a funcionar sem interface gráfica — é
disso que o modo `--cli` depende. Se um módulo fora de `gui/` passar a importar
`customtkinter`, a CI parte, e é para isso que lá está.

---

## Estilo de código · Code style

- **Comentários e docstrings em PT-PT e EN-UK**, nesta ordem. É a convenção do
  projeto e aplica-se a todo o código novo.
- Comentar o **porquê**, não o **quê**. `# converte para inteiro` não acrescenta
  nada; `# o Id vem como string em algumas versões do PowerShell` sim.
- Type hints em todas as funções públicas.
- `pathlib.Path` em vez de `os.path`.
- Exceções específicas. Nunca `except:` nu.
- `logging`, nunca `print()` — excepto na saída do modo `--cli`.
- Linhas até 100 caracteres.

---

## Acrescentar uma regra à base · Adding a knowledge-base rule

**PT** · O ficheiro `src/ittoolkit/knowledge.py` contém apenas dados. Uma regra
nova é uma entrada na lista `REGRAS`:

**A forma da chave muda com o sistema, e a razão é de fundo.** Em Windows um
evento tem um número — o Event ID — e a chave é o par `(número, provider)`. Em
Linux e em macOS não há número nenhum: o diário guarda texto livre, e o que
identifica um problema é um **padrão no texto** somado a **quem o escreveu**.

```python
# Windows/src/ittoolkit/knowledge.py
Regra(
    event_id=1234,
    providers=("nome-do-provider",),      # obrigatório, em minúsculas
    titulo="Frase curta que descreve o evento",
    causa="Porque é que isto acontece, em linguagem de operador.",
    solucao="O que verificar, por ordem de probabilidade.",
    gravidade=Gravidade.ALTA,
    ruido=False,                          # True para ruído conhecido do sistema
)

# Linux/src/ittoolkit/knowledge.py
Regra(
    padrao=r"Out of memory: Killed process",   # expressão regular
    unidades=("kernel",),                      # fragmento do nome da unidade
    ...
)

# macOS/src/ittoolkit/knowledge.py
Regra(
    padrao=r"panic\(cpu|kernel panic",
    processos=("kernel",),                     # fragmento do nome do processo
    ...
)
```

Regras da casa:

| Regra | Porquê |
|---|---|
| O `providers` / `unidades` / `processos` raramente fica vazio | Um Event ID ou um padrão sozinho não identifica nada: o mesmo «I/O error» do kernel é um disco a falhar, e vindo de uma aplicação qualquer não é nada. |
| A `solucao` diz o que **verificar**, não o que fazer | A decisão é sempre do operador; esta ferramenta não repara nada sozinha. |
| Ordene as causas por probabilidade | Quem lê o relatório às três da manhã segue a primeira linha. |
| `ruido=True` para o que o sistema produz sem haver problema | Sem isso, o relatório perde credibilidade e o operador aprende a ignorá-lo. Em macOS isto é obrigatório: as negações de sandbox sozinhas são centenas por dia num Mac saudável. |
| `CRITICA` só para perda de dados, avaria de hardware ou compromisso de segurança | Se tudo for crítico, nada é. |

**PT** · Em cada versão há um teste que percorre a base inteira à procura de
entradas sem causa, sem solução ou duplicadas — e, nas de Linux e macOS, um que
confirma que todas as expressões regulares compilam. Corra o `pytest` antes de
submeter.

**PT** · Uma regra nova vale para **um** sistema. O `Kernel-Power 41` do Windows
e o `panic(cpu` do macOS descrevem a mesma experiência para o utilizador, mas
são duas entradas em duas bases diferentes, com soluções diferentes. Não
traduza uma para as outras sem confirmar que a solução se aplica mesmo.

---

## Acrescentar uma verificação · Adding a check

**PT** · Uma verificação nova devolve `Achado`, não texto. Assim entra no
relatório, na contagem por gravidade e nos códigos de saída do `--cli` sem ter
de mexer em mais nada:

```python
Achado(
    modulo="Discos",
    titulo="Frase curta",
    detalhe="Os números concretos.",
    gravidade=Gravidade.ALTA,
    solucao="O que verificar.",
)
```

**PT** · Se a verificação depender de uma ferramenta que pode não estar
instalada, trate a ausência devolvendo lista vazia ou um `Achado`
`INFORMATIVA` que diga o que ficou por ver — não levante excepção, e não
devolva silêncio. O `_recolher` apanha excepções para que um módulo partido não
derrube os outros, mas contar com isso é desleixo.

**PT** · E há aqui uma distinção que atravessa o projecto todo: **«não
encontrei» e «não consegui olhar» não são a mesma coisa.** Um `smartctl` que
não está instalado, um diário que o utilizador não pode ler, uma pasta que o
TCC do macOS esconde — nenhum desses casos é uma máquina saudável, e apresentá-
-los como tal é o pior que esta ferramenta pode fazer.

---

## Pull requests

1. Ramo a partir de `main`: `git checkout -b feat/descricao-curta`
2. Testes a passar e um teste novo por cada correcção de bug
3. Commits no formato [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
4. Actualize o `CHANGELOG.md` na secção *Unreleased*
5. Descreva **o problema** que resolve, não apenas o que alterou

---

## Reportar problemas · Reporting issues

Inclua: versão do Windows, versão do Python, se correu com ou sem elevação, o
que esperava, o que aconteceu, e as linhas relevantes do registo (`--verbose`)
**depois de substituir nomes de máquina e endereços reais**.

---

*Created by Redfox using Claude*
