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
| `src/netconfig/platform_support.py` | **Não.** É o que distingue as versões |
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
diff -r --brief -x '__pycache__' -x 'platform_support.py' \n     Windows/src/netconfig Linux/src/netconfig

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

> **PT** · **Nunca** inclua num commit, issue ou pull request: configurações
> reais de equipamento, endereçamento verdadeiro da sua rede, comunidades SNMP,
> nomes de utilizador, palavras-passe, chaves, ou capturas de ecrã com qualquer
> uma destas coisas.
>
> Uma `running-config` é um mapa da rede: diz que VLANs existem, onde estão os
> servidores, que portas estão abertas e quem gere o quê. É exactamente o que
> alguém precisaria para começar. Ao reportar um problema, use endereçamento de
> documentação — `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` (RFC 5737)
> — e nomes inventados.
>
> **EN** · **Never** include real device configurations, your network's actual
> addressing, SNMP communities, usernames, passwords, keys, or screenshots
> containing any of these. A `running-config` is a map of the network. Use
> RFC 5737 documentation addressing and invented names instead.

Os perfis de exemplo produzidos por `python -m netconfig modelo` foram feitos
para isto — não trazem endereçamento nem nomes.

---

## Ambiente · Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

```bash
pytest                            # testes
pytest --cov=netconfig            # com cobertura
ruff check src/ tests/            # análise estática
mypy src/                         # tipos
```

---

## Nenhum teste toca na rede · No test touches the network

**PT** · É a regra que não se negoceia. A suite tem de correr numa máquina sem
acesso a nenhum switch, num runner de integração contínua, e em quinze segundos.

Tudo o que fala com equipamento está em `transport.py`, atrás de uma fronteira
que os testes não atravessam. O que se testa é o que decide **o que** seria
enviado — `commands_for_push`, a validação, os geradores — porque é aí que um
erro se transforma numa configuração aplicada a meio.

**EN** · This is the non-negotiable rule. The suite must run on a machine with
no access to any switch, on a CI runner, in fifteen seconds. Everything that
talks to equipment lives in `transport.py`, behind a boundary the tests do not
cross.

---

## Acrescentar um fabricante · Adding a vendor

1. Uma classe em `src/netconfig/vendors/`, a estender `base.VendorGenerator`
2. Declarar `platform`, `comment_prefix` e `save_command`
3. Implementar `body()` — a ordem das secções vem da classe base e não deve ser
   alterada: criar uma VLAN depois de a referenciar numa porta falha em todos os
   fabricantes
4. Acrescentar a entrada em `models.Platform` e no registo de `vendors/__init__.py`
5. Acrescentar o padrão de nome de porta em `validation._PORT_NAME_HINTS`
6. Testes: o `TestTodasAsPlataformas` em `tests/test_vendors.py` corre
   automaticamente para a plataforma nova. Acrescente uma classe própria para as
   particularidades — que é onde está o valor

**PT** · Escreva no cabeçalho do módulo *porque* é que o fabricante é diferente,
não *o que* o código faz. O `no routing` do AOS-CX e a exclusão da VLAN 1 no
EdgeSwitch estão documentados assim: quem lê daqui a um ano precisa de saber que
aquelas linhas não são decorativas.

---

## Estilo · Style

- Documentação bilingue PT-PT / EN-UK em todos os módulos, classes e funções
- `from __future__ import annotations` no topo
- Tipos em todas as assinaturas públicas
- `ruff` limpo sob a configuração do `pyproject.toml`
- Nada de `print()` fora do `__main__.py` — o resto usa `logging`
- Nenhum módulo fora de `gui/` importa `customtkinter`

---

## O que não vai ser aceite · What will not be accepted

- **Um campo para a palavra-passe no formulário.** Está explicado em
  `models.Security`. Os ficheiros saem com um marcador e é assim que fica.
- **Gravar credenciais em disco**, em qualquer formato, incluindo "encriptado"
  com uma chave que também está no disco.
- **`dry_run=False` por omissão** em qualquer caminho de código.
- **Um envio que não faça backup primeiro.**

---

<sub>Created by Redfox using Claude</sub>
