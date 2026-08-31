# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [2.0.0] — 2026-08-31

**PT** · Três versões independentes, uma por sistema operativo.
**EN** · Three independent versions, one per operating system.

### A reorganização · The restructure

O projecto deixou de ter um `src/` partilhado. Passou a ter três pastas —
`Windows/`, `Linux/` e `macOS/` — e cada uma é uma **versão completa e
autónoma** da aplicação, com o seu código, os seus testes, os seus requisitos e
o seu lançador. Quem usa uma delas não precisa de nada do que está nas outras.

### Cada versão é especializada, não é uma cópia

O `platform_support.py` é diferente em cada uma, e **nenhuma tem uma única
ramificação por sistema operativo** — há um teste em cada versão que falha se
alguém acrescentar um `sys.platform` ou um `os.name`.

- **Windows** deteta o `python.exe` falso da Microsoft Store, que responde ao
  comando `python`, não é um interpretador, e abre a loja em vez de correr o
  programa — quem cai nisso vê uma janela da Store e nenhum erro que explique
  porquê
- **Linux** lê o `/etc/os-release` para escolher entre `apt`, `dnf`, `pacman`,
  `zypper` e `apk`, e pelo campo `ID_LIKE` acerta também em derivadas que não
  estão em lista nenhuma, como o Linux Mint. Deteta ainda o servidor gráfico,
  porque o Tk corre por XWayland e é isso que explica janelas com tamanhos
  estranhos
- **macOS** trata do Python do sistema, que traz um Tk antigo e vai ser retirado
  pela Apple, e dos dois prefixos do Homebrew — procurados directamente porque
  um processo lançado pelo Finder não herda o PATH da shell

### Novo · Added

- `--diagnostico` — verifica os requisitos deste sistema e diz o que falta, com
  o comando exacto para aquela máquina. Corre antes de tudo o resto, porque é o
  comando a que alguém recorre quando *nada* funciona
- Testes de plataforma em cada versão, que verificam o comando de instalação
  certo sem precisar de ter as três máquinas à frente

### Alterado · Changed

- A pasta de configuração em macOS passou a `~/Library/Application Support`.
  Antes caía no ramo do XDG e ia parar a `~/.config`, que é hábito de Linux e
  num Mac ninguém lá vai procurar
- Os pacotes passaram a ter nomes distintos por sistema, para não haver dúvidas
  sobre qual é que está instalada num ambiente
- Os lançadores passaram a tratar a própria pasta como raiz do projecto

### O custo, dito à cabeça · The cost, stated up front

Uma correcção ao código partilhado tem de ser aplicada **três vezes**, uma por
pasta. É o preço de três versões independentes em vez de uma com ramificações,
e é uma escolha deliberada. O `CONTRIBUTING.md` explica como manter as três
alinhadas.

### Integração contínua · Continuous integration

Passou a uma matriz de três: cada versão é testada no seu próprio sistema —
`windows-latest`, `ubuntu-latest` e `macos-latest`. Uma versão de Linux testada
num runner de Windows não prova nada sobre o que ela faz em Linux.

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
