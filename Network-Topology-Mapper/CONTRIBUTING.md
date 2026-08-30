# Contribuir · Contributing

**PT** · Obrigado pelo interesse.
**EN** · Thank you for your interest.

---

## Antes de tudo · Before anything else

> **PT** · **Nunca** inclua num commit, issue ou pull request: output real de um
> equipamento seu, endereços MAC verdadeiros, endereçamento IP da sua rede,
> nomes de switches, comunidades SNMP, credenciais, ou relatórios gerados.
>
> Um mapa de rede é a planta do edifício: diz que VLANs existem, onde estão os
> servidores, em que porta está cada posto e o que é cada equipamento. É
> exactamente o que alguém precisaria para começar.
>
> Ao acrescentar um ficheiro de exemplo, **anonimize-o primeiro**: endereçamento
> de documentação (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, RFC 5737),
> MAC inventados que mantenham o OUI se ele for relevante para o teste, e nomes
> de equipamento inventados.
>
> **EN** · **Never** include real device output, real MAC addresses, your
> network's IP addressing, switch names, SNMP communities, credentials, or
> generated reports. A network map is the building's floor plan. Anonymise
> sample files first: RFC 5737 documentation addressing, invented MACs keeping
> the OUI only where the test needs it, and invented device names.

---

## Ambiente · Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

```bash
pytest                            # testes
pytest --cov=netmap               # com cobertura
ruff check src/ tests/            # análise estática
mypy src/                         # tipos
```

---

## Duas regras que não se negoceiam

### 1. Nenhum teste toca na rede

**PT** · A suite tem de correr numa máquina sem acesso a nenhum switch, num
runner de integração contínua, e em menos de um segundo.

Tudo o que abre ligações está em `collector.py` e em `unifi.py`, atrás de uma
fronteira que os testes não atravessam. O crawl completo é testado passando um
`collect_fn` que devolve os ficheiros de `tests/fixtures/` — ver
`tests/test_crawl_topology.py`. Um teste que precisasse de um switch a responder
não correria na integração contínua e, por isso, não correria nunca.

### 2. Nenhum comando que escreva

**PT** · Este programa promete não escrever em equipamento nenhum, e a promessa
está no caminho de execução: `collector.assert_read_only` verifica todos os
comandos antes de a ligação abrir. Há um teste que percorre os comandos de todas
as plataformas.

Se acrescentar um comando a um leitor, tem de começar por um verbo de leitura. Se
precisar mesmo de escrever alguma coisa, este não é o projecto — é o
[Network Config Builder](../../tree/Network-Config-Builder).

---

## Corrigir um leitor de CLI

É a contribuição mais provável e a mais útil. Se o seu firmware apresenta as
tabelas de outra maneira, o programa assinala-o — "N linhas de output não foram
interpretadas". Para corrigir:

1. Corra com `--verbose` e recolha o output do comando em causa
2. **Anonimize-o** (ver acima)
3. Guarde-o em `tests/fixtures/` com o nome `<plataforma>_<comando>.txt`
4. Acrescente um teste em `tests/test_parsers.py` que o leia e verifique o que
   deve sair
5. Ajuste o leitor até passar, sem partir os ficheiros que já lá estão

**PT** · A leitura é por reconhecimento de padrões em cada linha — procurar um
MAC, um nome de porta, um endereço — e não por posições de coluna. Se a correcção
precisar de contar colunas, é provável que exista uma forma mais robusta: as
colunas mudam entre modelos e entre versões de firmware.

---

## Acrescentar uma plataforma

1. Uma classe em `src/netmap/parsers/`, a estender `base.CliParser`
2. Declarar `platform`, `commands` (só de leitura) e `port_pattern`
3. Implementar `parse_lldp`, `parse_ports` e `parse_version`. As tabelas MAC e
   ARP costumam funcionar com a leitura genérica da classe base
4. Registar em `parsers/__init__.py` e acrescentar as palavras de reconhecimento
   em `_FINGERPRINTS`
5. Ficheiros de exemplo em `tests/fixtures/` e uma classe de testes própria

**PT** · Escreva no cabeçalho do módulo *porque* é que aquele fabricante é
diferente, não *o que* o código faz. O `no routing` do AOS-CX, a exclusão da VLAN
1 no EdgeSwitch, o `Trans-Bridge` que num Cisco é um AP e não um switch — quem
ler daqui a um ano precisa de saber que aquelas linhas não são decorativas.

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

- **Guardar credenciais em disco**, em qualquer formato
- **Verificação de TLS desligada por omissão**, por mais cómodo que seja
- **Uma classificação sem sinais registados.** Se o programa diz que aquilo é uma
  impressora, tem de dizer porquê
- **Apresentar um palpite com a mesma confiança de um facto.** É a única coisa
  que esta ferramenta faz melhor do que as alternativas

---

<sub>Created by Redfox using Claude</sub>
