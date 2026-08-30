# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [1.0.0] — 2026-08-30

**PT** · Primeira versão.
**EN** · First release.

### Geração de configurações · Configuration generation

- Descrição neutra da configuração — VLANs, portas, gestão, serviços, segurança
  — traduzida por um gerador por plataforma. A mesma VLAN é descrita uma vez,
  independentemente de a rede ter switches de três marcas
- **Aruba AOS-CX** — com o `no routing` que o AOS-CX exige antes de aceitar uma
  VLAN numa porta física, e a VLAN de voz feita com nativa + marcada, que é a
  única forma de a fazer nesta plataforma
- **Cisco IOS / IOS-XE** — com `spanning-tree portfast` e `bpduguard` nas portas
  de acesso, e o `switchport trunk encapsulation dot1q` comentado, por ser
  obrigatório num 3560 e rejeitado num Catalyst 9300
- **Ubiquiti EdgeSwitch** — VLANs na base de dados própria, participação e PVID
  em vez de modos de porta, e `vlan participation exclude 1` sempre escrito nas
  portas de acesso: sem ele a porta fica na VLAN 1 e na de acesso ao mesmo tempo
- **Ubiquiti UniFi** — mesma sintaxe do EdgeSwitch, com aviso de configuração
  temporária no cabeçalho e sem `write memory`, porque num UniFi a configuração
  pertence ao controlador e o que for escrito por SSH desaparece no
  provisionamento seguinte
- Compactação das listas de VLAN (`10,11,12,20` → `10-12,20`): uma lista de
  trunk com quarenta VLANs numa linha só é ilegível e alguns firmwares cortam-na
- Remoção de acentos e de aspas das descrições e dos nomes de VLAN — as CLIs
  destes equipamentos são ASCII
- Quatro modelos de partida: switch de acesso, escritórios com voz, switch de
  pontos de acesso, formulário vazio. Nenhum traz endereçamento ou nomes

### Validação · Validation

- Distinção entre `ERRO` (impede gerar) e `AVISO` (fica registado no cabeçalho
  do ficheiro). Uma ferramenta que se recusa a gerar por uma escolha invulgar
  acaba contornada à mão, e aí não há validação nenhuma
- Gateway fora da sub-rede de gestão — o erro que deixa o switch inacessível
  assim que a sessão actual cair
- Endereço de gestão sem prefixo. `10.0.10.2` é lido como `/32` por qualquer
  biblioteca de rede, e um `/32` numa VLAN de gestão não fala com ninguém
- VLAN referenciada numa porta mas não declarada — o switch aceita a linha e a
  porta fica sem rede
- Nome de porta com a notação de outro fabricante, por plataforma
- Portfast num trunk, VLAN de gestão por declarar, comunidade SNMP de fábrica,
  ausência de NTP

### Ligação ao equipamento · Device connection

- Leitura da configuração em execução, por SSH, via Netmiko
- Backup com data ao segundo no nome — numa intervenção fazem-se vários backups
  do mesmo switch em poucos minutos
- Comparação normalizada: sem o cabeçalho do firmware, sem contadores, sem
  certificados e sem indentação, porque um diff em bruto marca tudo como
  diferença e não é lido por ninguém
- Envio em simulação por omissão, com o backup como condição de entrada: se a
  leitura falhar, não se escreve
- Confirmação que obriga a escrever o nome do equipamento

### Interface · Interface

- Cinco separadores pela ordem segura do trabalho: construtor, portas,
  equipamentos, comparar e enviar, definições
- Tudo o que fala com a rede corre noutra linha de execução — uma janela
  congelada leva a fechar a aplicação a meio de um envio
- O botão de envio é o único vermelho da aplicação

### Inventário · Inventory

- Leitura e escrita em `.xlsx`, `.csv` (vírgula ou ponto e vírgula) e `.json`
- Nomes de plataforma tolerantes: `aruba`, `AOS-CX`, `cisco`, `Catalyst`,
  `EdgeSwitch`, `unifi`, `USW`
- Teste de alcance por TCP, sem credenciais

### Segurança · Security

- Nenhuma palavra-passe é escrita nos ficheiros gerados: sai
  `<DEFINIR-PALAVRA-PASSE>` no lugar
- Credenciais apenas em memória, nunca em disco. Sem caixa de "memorizar"
- `repr` das credenciais sem segredos, para um traceback não as deixar no registo
- Filtro no registo que substitui `password`, `secret`, `community` e `key`
  antes de qualquer coisa chegar ao disco — o Netmiko em depuração escreve tudo
  o que envia
- Na linha de comandos, credenciais por variável de ambiente ou perguntadas sem
  eco, nunca por argumento

### Linha de comandos · Command line

- Subcomandos `modelo`, `validar`, `gerar`, `backup`, `comparar`, `enviar`,
  `inventario`
- Códigos de saída distintos (`0` limpo, `1` problemas, `2` inalcançável,
  `3` erro) para um agendador poder reagir

### Infra-estrutura · Infrastructure

- 216 testes, nenhum dos quais abre uma ligação de rede
- Integração contínua em GitHub Actions: `ruff` e `pytest` em `windows-latest`
- Código-fonte bilingue PT-PT / EN-UK
