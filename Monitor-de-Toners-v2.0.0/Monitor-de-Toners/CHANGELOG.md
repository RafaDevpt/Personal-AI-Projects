# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [2.0.0] — 2026-08-27

**PT** · Reescrita completa. A versão anterior (1.5, ficheiro único) fica
descontinuada.
**EN** · Complete rewrite. The previous version (1.5, single file) is
discontinued.

> **PT** · Alteração incompatível: as impressoras deixaram de estar escritas
> dentro do código. Ao arrancar pela primeira vez é criado um ficheiro Excel
> vazio — o parque tem de ser preenchido à mão ou descoberto na rede.
>
> **EN** · Breaking change: printers are no longer hard-coded. On first run an
> empty Excel file is created — the estate must be filled in by hand or
> discovered on the network.

### Adicionado · Added

- **Inventário em Excel** (`Impressoras.xlsx`), criado automaticamente na
  primeira execução, com folha de instruções, listas pendentes e linha de
  exemplo desactivada
- **Procura na rede** por gama CIDR, intervalo ou endereço isolado, com
  identificação por SNMP e 64 pedidos em paralelo
- **Fusão de inventário** que acrescenta as impressoras novas sem tocar nas
  localizações já escritas à mão
- Leitura de `.csv` além de `.xlsx`, com vírgula ou ponto e vírgula
- Coluna **Activa**, para manter uma impressora na lista sem a consultar
- Colunas **MAC**, **Número de série** e **Notas**
- Modo `--cli` para o Agendador de Tarefas, com códigos de saída distintos
  (`0` sem alertas, `1` com alertas, `2` inventário vazio, `3` sem interface)
- `--criar-modelo`, `--discover`, `--no-email`, `--no-pdf`, `--verbose`
- Relatório PDF de resumo do parque inteiro, além do PDF por impressora
- Registo rotativo em ficheiro
- 49 testes automatizados, nenhum toca na rede

### Alterado · Changed

- **Arranque**: a tabela é preenchida a partir do Excel **antes** de qualquer
  contacto com a rede. A 1.5 abria uma janela vazia durante cerca de 30
  segundos e parecia bloqueada
- **Estrutura**: ficheiro único de ~2000 linhas → pacote com módulos separados
  para inventário, descoberta, SNMP, recolha, relatórios e email
- **SNMP**: implementado de raiz sobre a biblioteca padrão (BER + v2c), em vez
  do `pysnmp`. Numa máquina de domínio com instalação de pacotes bloqueada, uma
  dependência a menos é uma dependência a menos
- **Cascata de leitura**: só pára quando uma estratégia devolve pelo menos um
  consumível com percentagem conhecida
- **Pedido de toners**: agrupado por referência de cartucho, não por impressora
- **Proxy**: ignorado por omissão nos pedidos às impressoras
- **Consultas em paralelo**, em vez de uma impressora de cada vez
- Vermelho reservado exclusivamente para alertas em toda a interface

### Corrigido · Fixed

- **Capacidade máxima `-2` no SNMP** (HP M527 e semelhantes): significa
  «desconhecido». A 1.5 calculava `100 × 7 ÷ -2`, obtinha um número negativo,
  aceitava-o como leitura válida e nunca chegava a tentar o HTML. Agora
  devolve *desconhecido* e a cascata prossegue
- Timeouts sistemáticos causados pelo proxy corporativo em endereços internos
- Certificados self-signed rejeitados, impedindo a leitura por HTTPS em
  firmware antigo
- Parêntesis e acentos no nome da localização corrompiam o PDF gerado
- Uma impressora desligada interrompia a verificação das restantes
- Interface bloqueada durante a verificação

### Removido · Removed

- Os 24 endereços IP do parque, escritos no código
- Dependência de `pysnmp`
- Dependência de bibliotecas externas de PDF

### Segurança · Security

- A password do EWS deixou de ser gravada em disco; é mantida apenas em memória
  durante a sessão
- `.gitignore` exclui o inventário (`*.xlsx`, `*.csv`), os PDF, os `.eml`, os
  registos e o `config.json`
- O envio de email continua a **não** ser automático: é gerado um rascunho que
  abre no Outlook por enviar

---

## [1.5.0] — 2026

**PT** · Versão anterior, ficheiro único, com o parque de impressoras escrito
no código. Não mantida.
**EN** · Previous version, single file, with the printer estate hard-coded.
Not maintained.

---

*Created by Redfox using Claude*
