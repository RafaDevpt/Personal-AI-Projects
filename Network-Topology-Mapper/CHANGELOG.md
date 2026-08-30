# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [1.0.0] — 2026-08-31

**PT** · Primeira versão.
**EN** · First release.

### Descoberta · Discovery

- Travessia em largura a partir de uma ou mais sementes, seguindo LLDP e CDP
- Semeadura opcional a partir de um controlador UniFi, que também fornece a
  localização exacta dos clientes com fios que conhece
- Pontos de acesso ficam no mapa mas não são visitados: não têm tabela MAC para
  dar e as credenciais de switch não servem lá
- Telefones IP também não são visitados, apesar de se anunciarem como `bridge`
  — têm mesmo um switch de duas portas lá dentro. Sem esta excepção, mapear um
  hotel tentaria autenticar-se em cada telefone dos quartos
- Detecção automática da plataforma a partir da descrição publicada no LLDP,
  com `desconhecida` quando nada corresponde: um palpite errado faria correr os
  comandos de outro fabricante e registaria o equipamento como problemático
- Limites de profundidade e de número de equipamentos, para um erro de dedução
  não pôr o crawl a andar em círculos

### Correlação · Correlation

- Localização de cada endereço MAC na porta a que está realmente ligado,
  descartando as portas de uplink identificadas pelo LLDP
- Inferência que resolve a ausência de capacidades no LLDP do EdgeSwitch: se o
  vizinho de uma porta é um equipamento que nós próprios visitámos, aquela porta
  é um uplink. Sem isto, o uplink para o core seria tomado por uma tomada de
  utilizador e receberia meia rede
- Endereços em mais do que uma porta de acesso ficam marcados como ambíguos, com
  as duas localizações, em vez de se escolher uma à sorte
- Endereços que só aparecem em uplinks são reportados como estando para lá de um
  switch que não foi alcançado
- Clientes sem fios não recebem uma localização com fios que não existe

### Classificação · Classification

- Nível de confiança e lista de sinais em cada classificação. Um AP identificado
  pelo LLDP é um facto; um "posto de trabalho" deduzido de um OUI da Intel é um
  palpite razoável que pode ser uma impressora com placa Intel
- Sinais em conflito baixam a confiança e ficam registados, em vez de se escolher
  o mais bonito. O caso que obrigou à regra é a HP, que fabrica postos e
  impressoras com o mesmo OUI
- Detecção de switches não geridos como conclusão sobre a **porta** e não sobre
  os equipamentos que aparecem nela — dos seis endereços numa dessas portas,
  nenhum *é* o switch
- Tabela de fabricantes curada, com importação opcional do ficheiro completo do
  IEEE. Um OUI desconhecido devolve vazio, e não "fabricante desconhecido"
- Reconhecimento de MAC administrado localmente como privacidade de MAC activada,
  que é informação a sério — e não um fabricante em falta

### Leitura dos equipamentos · Device reading

- Leitores de CLI para Aruba AOS-CX, Cisco IOS/IOS-XE e Ubiquiti
  EdgeSwitch/UniFi, escritos por reconhecimento de padrões em cada linha e não
  por posições fixas de coluna, que mudam entre modelos e firmwares
- Contagem das linhas de output não interpretadas, para se poder dizer
  honestamente que o mapa pode estar incompleto
- Normalização de endereços MAC entre as três escritas que os fabricantes usam,
  e de nomes de porta entre a forma abreviada e a forma por extenso. Sem isto o
  cruzamento não encontra nada e o mapa sai vazio sem dar erro

### Segurança · Security

- Verificação de que todos os comandos são de leitura, antes de a ligação abrir,
  com um teste que percorre os comandos de todas as plataformas
- Comandos encadeados com `;`, `&&` ou `||` são recusados
- Credenciais nunca gravadas em disco, `repr` sem segredos, e filtro no registo
  que substitui `password`, `secret` e `community`
- Verificação do certificado do controlador UniFi ligada por omissão, com a
  explicação do que se perde ao desligá-la

### Relatórios · Reports

- Excel com cinco folhas, filtro automático e cabeçalho fixo, incluindo a coluna
  dos sinais que sustentam cada classificação
- PDF com o diagrama da topologia desenhado em árvore e as listagens agrupadas
  por switch. Quando a rede é grande de mais para caber legivelmente, o PDF
  di-lo na própria página em vez de produzir um desenho ilegível

### Interface · Interface

- Cinco separadores: mapeamento, topologia, pontos finais, problemas, definições
- Registo ao vivo durante o mapeamento, que além de tranquilizar mostra
  exactamente onde parou quando pára
- Listas em `ttk.Treeview` e não em widgets do customtkinter: uma rede de hotel
  dá dois mil pontos finais, e desenhar dois mil conjuntos de etiquetas demora
  dezenas de segundos

### Infra-estrutura · Infrastructure

- 155 testes, nenhum dos quais abre uma ligação de rede
- Leitores testados contra ficheiros de output guardados em `tests/fixtures`
- Crawl completo testado com um recolector substituído, percorrendo uma rede de
  três fabricantes de ponta a ponta
- Integração contínua em GitHub Actions: `ruff` e `pytest` em `windows-latest`
- Código-fonte bilingue PT-PT / EN-UK
