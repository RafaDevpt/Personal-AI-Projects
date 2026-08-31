# Contribuir · Contributing

**PT** · Obrigado pelo interesse. Este documento descreve como propor
alterações.
**EN** · Thank you for your interest. This document describes how to propose
changes.

---

## A regra que define este projecto

**Há três versões independentes — `Windows/`, `Linux/` e `macOS/` — e cada uma é
uma cópia completa da aplicação.**

Isto é uma escolha deliberada, e tem um custo que não se pode ignorar: **uma
alteração ao código partilhado tem de ser aplicada três vezes.** Não há
automatismo nenhum a proteger-nos disso; a única defesa é o hábito e a lista
abaixo.

### O que é partilhado e o que não é

| Ficheiro | Igual nas três? |
| :--- | :--- |
| `src/tonermon/platform_support.py` | **Não.** É o que distingue as versões |
| `tests/test_platform_support.py` | **Não.** Cada um testa o seu sistema |
| `pyproject.toml` | Quase — o `name` do pacote é diferente |
| `LEIA-ME.md` e lançadores | **Não.** São instruções de sistemas diferentes |
| **Todo o resto de `src/` e `tests/`** | **Sim** |

### Como aplicar uma alteração partilhada

1. Faça a alteração na versão do sistema em que está a trabalhar
2. Corra os testes **dessa** versão
3. Copie o ficheiro alterado para as outras duas
4. Corra os testes das outras duas — dá para as três a partir de uma máquina só,
   porque os testes passam os valores de sistema como argumentos
5. Confirme que a alteração aparece em três sítios:

```bash
diff -r --brief -x '__pycache__' -x 'platform_support.py' \n     Windows/src/tonermon Linux/src/tonermon

diff -r --brief -x '__pycache__' -x 'test_platform_support.py' \n     Windows/tests Linux/tests
```

Se algum destes comandos devolver alguma coisa, as versões divergiram num
ficheiro que devia ser igual. Repita para o `macOS/`.

### Quando a alteração é específica de um sistema

Aí é o contrário: **fica só numa pasta**, e o sítio dela é o
`platform_support.py` dessa versão. Se sentir vontade de escrever um
`if sys.platform` dentro de uma das versões, é porque a alteração pertence a
outro sítio — e há um teste em cada versão que falha precisamente nesse caso.

---

## Antes de tudo · Before anything else

> **PT** · **Nunca** inclua o ficheiro de inventário, endereços IP reais,
> hostnames, números de série ou capturas de ecrã com o parque visível num
> commit, issue ou pull request. É um mapa de rede interna: útil para quem lá
> trabalha, e igualmente útil para quem não devia lá entrar. Ao reportar um
> problema, substitua os endereços por `10.0.0.x` e as localizações por nomes
> inventados.
>
> **EN** · **Never** include the inventory file, real IP addresses, hostnames,
> serial numbers or screenshots showing the estate in a commit, issue or pull
> request. It is an internal network map. When reporting a problem, replace
> addresses with `10.0.0.x` and locations with invented names.

---

## Ambiente · Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

```bash
pytest                            # testes
pytest --cov=tonermon             # com cobertura
ruff check src/ tests/            # análise estática
```

**PT** · Em Windows, o `VERIFICAR.bat` faz as três coisas de uma vez.

---

## Testes · Tests

**PT** · Regra única e inegociável: **nenhum teste toca na rede**. As respostas
das impressoras são fixtures — XML do LEDM, pacotes SNMP em bytes, HTML do EWS.
Se precisar de uma resposta nova, acrescente a fixture; não vá buscá-la a uma
impressora real durante a execução dos testes.

**PT** · O `customtkinter` não é instalado na integração contínua, de propósito.
A lógica de inventário, SNMP, PDF e email tem de continuar a funcionar sem
interface gráfica — é disso que o modo `--cli` depende. Se um módulo fora de
`gui/` passar a importar `customtkinter`, a CI parte, e é para isso que lá está.

---

## Estilo de código · Code style

- **Comentários e docstrings em PT-PT e EN-UK**, nesta ordem. É a convenção do
  projeto e aplica-se a todo o código novo.
- Comentar o **porquê**, não o **quê**. `# soma 1 ao contador` não acrescenta
  nada; `# capacidade -2 significa desconhecido, não zero` sim.
- Type hints em todas as funções públicas.
- `pathlib.Path` em vez de `os.path`.
- Exceções específicas. Nunca `except:` nu.
- `logging`, nunca `print()` — exceto na saída do modo `--cli`.
- Linhas até 100 caracteres.

---

## Acrescentar suporte a uma impressora · Adding printer support

**PT** · Antes de escrever código, descubra o que a impressora responde:

```bash
python -m tonermon --discover 10.0.0.50 --verbose
```

Depois escolha o sítio certo:

| Situação | Onde mexer |
|---|---|
| Responde LEDM mas com nomes de campo diferentes | `collectors.py`, função de leitura do XML |
| Responde SNMP mas com OIDs de fabricante | `snmp.py`, e só se o Printer-MIB padrão não chegar |
| Só tem página HTML, com um formato novo | `collectors.py`, acrescente um padrão à lista |
| É de um fabricante que a descoberta não reconhece | `discovery.py`, `KNOWN_VENDORS` |

**PT** · Prefira sempre o Printer-MIB padrão a OIDs de fabricante. O padrão
sobrevive a mudanças de firmware; os OIDs privados nem sempre.

---

## Acrescentar uma coluna ao Excel · Adding an Excel column

**PT** · As colunas são procuradas pelo nome, com aliases em português e inglês,
em `inventory.py`. Ao acrescentar uma, aceite as duas línguas e mantenha-a
opcional — ficheiros já preenchidos pelos utilizadores não podem deixar de ser
lidos por causa de uma coluna nova.

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

Inclua: sistema operativo, versão do Python, marca e modelo da impressora,
versão do firmware se a souber, o que esperava, o que aconteceu, e as linhas
relevantes do registo (`--verbose`) **depois de substituir os endereços reais**.

---

*Created by Redfox using Claude*
