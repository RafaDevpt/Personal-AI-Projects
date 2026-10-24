# Network Twin 3D

**Gémeo digital da rede — guia de utilização, ficheiros e formatos**

<!-- Created by Redfox using Claude -->

---

## Índice

1. [Como abrir](#como-abrir)
2. [Ecrãs e vistas](#ecrãs-e-vistas)
3. [Bastidores e sala de servidores](#bastidores-e-sala-de-servidores)
4. [Editor de edifícios (importar plantas)](#editor-de-edifícios-importar-plantas)
5. [De onde vêm os dados](#de-onde-vêm-os-dados)
6. [`projeto.json`](#projetojson)
7. [`edificio-*.json` — o contrato do edifício](#edificio-json--o-contrato-do-edifício)
8. [O que é verificado](#o-que-é-verificado)
9. [Sem janela (linha de comandos)](#sem-janela-linha-de-comandos)
10. [Limites conhecidos](#limites-conhecidos)

---

## Como abrir

| Sistema | Como |
| :--- | :--- |
| **Windows** | Duplo clique em **`EXECUTAR.bat`** (ou arraste um `projeto.json` para cima dele) |
| **macOS** | `./executar.sh` |
| **Linux** | `./executar.sh` — precisa do WebKitGTK: `sudo apt install python3-gi gir1.2-webkit2-4.1` |

Pré-requisito: **Python 3.10+**. Na primeira execução cria o ambiente e instala o `pywebview`. A janela é HTML com Three.js servido **localmente** — não carrega nada da Internet.

**Importar DXF ou PDF** no editor precisa de duas bibliotecas opcionais (imagens funcionam sem elas):

```
.venv\Scripts\pip install -r requirements-importacao.txt      (Windows)
.venv/bin/pip install -r requirements-importacao.txt          (Linux / macOS)
```

No início, **Abrir o hotel de exemplo** mostra tudo a funcionar com dados sintéticos: dois edifícios, sala de servidores com três bastidores, bastidores de piso, plantas em imagem, e um erro plantado por tipo de verificação.

---

## Ecrãs e vistas

### Início — escolher o edifício

Ao abrir um projeto aparece um cartão por edifício, com a planta em miniatura (todos os pisos sobrepostos), o número de pisos, salas, bastidores e equipamentos, e os erros que lá estão. **Clicar num edifício abre-o inteiro**, com todos os pisos.

Há também os cartões **Rede lógica** (a rede sem edifício) e **Novo edifício** (abre o editor). O logótipo no canto volta sempre ao início.

### Menus do topo

| Menu | Faz |
| :--- | :--- |
| **🏢 Edifício** | Muda de edifício |
| **≡ Piso** | *Todos os pisos* (empilhados e afastados) ou um piso só — com as paredes à altura real e os nomes das salas |
| **Rede · Edifício · Bastidor** | As três vistas (atalhos `1` `2` `3`) |

### Vista do edifício

- **Pisos empilhados**, afastáveis com o controlo *Afastar pisos*.
- **A planta original no chão** de cada piso (se o edifício tiver plantas em imagem), com opacidade ajustável. É o que torna o modelo reconhecível.
- **Paredes** tiradas dos polígonos das salas, em vidro fosco para não taparem o interior.
- **Bastidores** à escala real, com as máquinas lá dentro.
- **Cabos** com a cor da pior constatação: sobem à esteira no tecto, ou pela coluna montante entre pisos. Um cabo para **outro edifício** sai pela fachada com a etiqueta `↗ equipamento · edifício` — clicar leva lá. Com um piso só à vista, um cabo para outro piso acaba em `↑ P0 · equipamento`.
- **Clicar numa sala** aproxima a câmara e mostra a sala: área, bastidores, equipamentos, e o formulário **Novo bastidor nesta sala**.
- Botões: *Rótulos*, *Tráfego* (animação nos cabos), *Brilho* (desligar em PCs lentos), *Planta*, *Vista de cima* (`T`), *Enquadrar* (`F`).

### Vista lógica

A rede por camadas — borda → core → distribuição → acesso → APs — sem edifício. Os switches são o mesmo modelo 1U da vista de bastidor, ampliado; os LEDs acesos são as portas activas que o mapper observou.

### Constatações

O painel da direita lista tudo o que o motor encontrou, do pior para o melhor, com filtros por gravidade e procura. **Clicar numa constatação** esbate tudo o resto e leva a câmara ao problema — muda de edifício, se for preciso; num problema de bastidor, abre o bastidor. Cada uma diz **o que fazer**.

---

## Bastidores e sala de servidores

### Criar um bastidor

1. Na vista do edifício, escolher o piso e **clicar na sala** (a sala de servidores, ou o bastidor de piso).
2. No painel: nome e altura (42 U, 24 U, …) → **+ Adicionar bastidor**.
3. Para o pôr no sítio exacto: painel do bastidor → **✥ Mover no mapa** → clicar no chão. A sala é detectada pelo sítio do clique.

Vários bastidores na mesma sala sem posição exacta alinham-se em fila, como numa sala de servidores.

### Montar e desmontar máquinas

**▤ Abrir bastidor** (ou a vista *Bastidor*) mostra o bastidor de perto, sem porta:

- numeração das U no montante;
- cada máquina com etiqueta e linha guia;
- **espaços livres** marcados (`livre U4–U29 · 26U`);
- os outros bastidores da sala ao lado, esbatidos — clicar troca de bastidor.

No painel, a lista de máquinas de cima para baixo com os espaços livres intercalados, e o formulário **Montar máquina**:

| Campo | Notas |
| :--- | :--- |
| Nome, tipo | Switch, router, firewall, servidor, storage, UPS, patch panel, organizador, PDU, KVM, prateleira, outro — cada tipo tem o seu modelo 3D |
| Altura e U | O menu de U só oferece as posições onde a máquina **cabe** |
| Equipamento de rede | Liga a máquina a um equipamento do mapa/perfis: passa a estar **posicionado no bastidor**, com a cor do estado dele, e os cabos dele saem do tampo do bastidor |
| Modelo, n.º de série, nota | Inventário |

Clicar numa máquina permite editá-la (incluindo mudar de U) ou **desmontá-la**. Tudo fica em memória até **Guardar** (aparece *● por gravar* no topo).

A aplicação **recusa** gravar uma máquina sobreposta a outra, fora da altura do bastidor, ou um equipamento de rede montado em dois sítios — com a mensagem a dizer qual é o conflito. Num `projeto.json` editado à mão, os mesmos problemas aparecem como constatações (B03, B04, B08).

---

## Editor de edifícios (importar plantas)

Abre com **✎ Editor de edifícios** (no topo) ou com o cartão **Novo edifício**. Com um edifício aberto na vista, edita esse edifício.

### Com uma planta em imagem (PNG, JPG, WebP) ou PDF

1. **⇪ Importar planta…** — escolhe o ficheiro. Num PDF com várias páginas, a primeira é desenhada; as outras ficam acessíveis.
2. **📏 Calibrar** (`C`) — clicar nas duas pontas de uma medida conhecida (uma parede com cota) e escrever a distância em metros. *Sem escala nada sai em metros.*
3. **⊕ Origem** (`G`) — clicar num canto de referência. **Usar o mesmo canto em todos os pisos** — é o que alinha os pisos entre si em 3D.
4. **✨ Detetar todas as salas** e **⬚ Detetar contorno**. Ou, uma a uma, a **✨ Varinha** (`W`): clicar dentro de uma sala.
5. Corrigir à mão o que falhar (ver *Desenhar e editar*), e dar **nome e tipo** a cada sala na lista à esquerda — o tipo é sugerido pelo nome ("Sala de Servidores" → servidores, "Quarto 214" → quarto…).
6. **⧉ Duplicar** o piso para pisos iguais (torres de quartos): copia salas, contorno e planta; ajusta-se o que muda.
7. **Guardar edifício** — valida tudo antes de escrever e junta o edifício ao projeto aberto.

**Parâmetros da detecção** (painel da direita), em unidades reais:

| Parâmetro | Para quê |
| :--- | :--- |
| Limiar das paredes | O que é escuro o suficiente para ser parede. Plantas a lápis claro: subir |
| Fechar portas até | Aberturas até este tamanho contam como porta (fechadas). Se uma sala se juntar ao corredor: subir |
| Sala mínima | Regiões menores são ruído (cotas, símbolos) |
| Simplificar | Tolerância do contorno |
| Paredes a direito | Arestas quase horizontais/verticais ficam exactas |

O texto das plantas (nomes de salas, cotas) é reconhecido como *não parede* pela forma e ignorado. Um nome **maior do que a própria sala** e encostado às paredes pode fundir-se com elas — nesse caso, desenha-se a sala à mão.

### Com um DXF (AutoCAD)

A via mais fiel: uma polilinha fechada numa camada de salas *é* a sala, com as medidas reais.

1. **⇪ Importar planta…** → o ficheiro `.dxf`.
2. Aparece a lista de **camadas** com polígonos fechados: marcar as que são salas (☑) e, opcionalmente, a do contorno (◉).
3. Se o DXF não disser as unidades, escolher **mm / cm / m**.
4. **Aplicar a este piso** — cada texto (TEXT/MTEXT) que cai dentro de um polígono dá-lhe o nome. Polilinhas minúsculas (pilares, símbolos) são ignoradas.

### Sem planta nenhuma

- **🗺 Contorno OSM…** — escrever as coordenadas do edifício (no Google Maps: botão direito → copiar coordenadas) → *Procurar*. Mostra os edifícios mapeados no OpenStreetMap à volta; **Usar** aplica o contorno ao piso, e **+N pisos** cria logo os pisos (quando o OSM sabe quantos são). Precisa de Internet; dados © contribuidores do OpenStreetMap (ODbL).
- Desenhar as salas sobre a grelha em metros.

### Desenhar e editar

| Ferramenta | Tecla | Uso |
| :--- | :--- | :--- |
| Editar | `V` | Clicar numa sala; arrastar vértices; duplo clique numa aresta acrescenta um vértice; `Delete` apaga o vértice (ou a sala) |
| Retângulo | `R` | Arrastar de canto a canto |
| Polígono | `P` | Clicar nos cantos; `Enter` ou duplo clique fecha; `Backspace` desfaz; `Shift` força ângulos rectos |
| Contorno | `O` | Como o polígono, para o contorno do piso |
| Navegar | — | Roda: zoom. Botão direito, do meio, ou `Espaço` + arrastar: mover. `F`: enquadrar |

Os vértices **encaixam** nos das salas vizinhas — é o que faz duas salas partilharem a mesma parede em 3D. A **pré-visualização 3D** no canto mostra o edifício a crescer à medida que se desenha.

---

## De onde vêm os dados

| Fonte | Ficheiro | Diz |
| :--- | :--- | :--- |
| **Network Topology Mapper** | exportação **JSON** (botão *Guardar JSON*, ou `--json`) | O que **existe**: cabos (e quem os anunciou), portas, VLAN e PoE em produção, pontos finais |
| **Network Config Builder** | perfis `.json` (um por equipamento) | O que **devia existir**: VLANs, modo e VLANs de cada porta |
| **Editor de edifícios** | `edificio-*.json` + `plantas/` | **Onde**: edifícios, pisos, salas, plantas |
| **Esta aplicação** | `projeto.json` | Liga tudo + cablagem desenhada, bastidores, posições, orçamentos PoE |

Os perfis casam com os equipamentos descobertos pelo **hostname** (sem distinguir maiúsculas) ou pelo **IP de gestão**.

> **Os projetos reais não vão para o repositório.** Juntam topologia, endereços, plantas e a localização de cada bastidor. O `.gitignore` bloqueia `projetos/`, `*.csv` e `plantas/` fora do exemplo; guarde-os fora daqui.

---

## `projeto.json`

```json
{
  "formato": 1,
  "tipo": "nettwin-project",
  "nome": "Hotel X",
  "mapa": "mapa-rede.json",
  "perfis": ["perfis/SW-CORE.json", "perfis/SW-P1.json"],
  "edificios": ["edificio-principal.json", "edificio-pavilhao.json"],
  "cablagem": [
    { "a": "SW-CORE", "a_port": "Gi1/0/48", "b": "SW-P1", "b_port": "1/1/48", "nota": "uplink principal" }
  ],
  "equipamentos": {
    "SW-P1":   { "orcamento_poe_w": 370 },
    "FW-EDGE": { "tipo": "router", "camada": "borda" }
  },
  "bastidores": [
    {
      "id": "srv-a1", "nome": "SRV-A1", "edificio": "principal", "piso": "P-1", "sala": "sala-servidores",
      "x": 3.0, "y": 3.0, "rotacao_graus": 0, "altura_u": 42, "largura_mm": 600, "profundidade_mm": 1000,
      "equipamentos": [
        { "nome": "SW-CORE", "tipo": "switch", "u": 39, "altura_u": 1, "equipamento_rede": "SW-CORE", "modelo": "…" },
        { "nome": "UPS", "tipo": "ups", "u": 1, "altura_u": 3 }
      ]
    }
  ],
  "posicoes": {
    "AP-LOBBY": { "edificio": "principal", "piso": "P0", "sala": "lobby" }
  }
}
```

| Secção | Regras |
| :--- | :--- |
| Caminhos | Relativos à pasta do projeto — a pasta pode mudar de PC |
| `edificios` | Lista de ficheiros. O formato antigo (`"edificio": "…"`, um só) continua a abrir |
| `cablagem` | Opcional. Sem ela, não há verificações de "não documentado" / "em falta" |
| `orcamento_poe_w` | Da **ficha técnica do modelo** — a aplicação nunca o inventa |
| `camada` | `borda`, `core`, `distribuicao`, `acesso`, `ap` — se faltar, é calculada pela topologia |
| `bastidores[].u` | A U **mais baixa** que a máquina ocupa (a U 1 é a de baixo) |
| `bastidores[].x/y` | Metros, opcionais. Sem eles, os bastidores da sala alinham-se em fila |
| `posicoes` | Para equipamentos **fora** de bastidor (APs, switches de secretária). Com um só edifício, `edificio` pode faltar |

---

## `edificio-*.json` — o contrato do edifício

É o que o editor escreve — e o que qualquer outra ferramenta (uma futura importação de BIM, por exemplo) tem de escrever para abrir aqui.

```json
{
  "formato": 1,
  "tipo": "nettwin-building",
  "id": "principal",
  "nome": "Hotel X — Edifício Principal",
  "gerado_por": "planta",
  "origem": { "lat": 38.72, "lon": -9.14, "rotacao_graus": 0 },
  "pisos": [
    {
      "id": "P0", "nome": "Piso 0", "nivel": 0, "altura_m": 4.2,
      "contorno": [[0, 0], [60, 0], [60, 24], [0, 24]],
      "planta": { "imagem": "plantas/principal-P0.png", "escala_px_m": 25, "origem_px": [40, 40] },
      "salas": [
        { "id": "rececao", "nome": "Receção", "tipo": "publica", "poligono": [[0, 0], [14, 0], [14, 10], [0, 10]] }
      ]
    }
  ]
}
```

| Campo | Regras |
| :--- | :--- |
| `id` | Único no projeto; letras, números, `-`, `_`, `.`. Sem ele, usa-se o nome do ficheiro |
| Coordenadas | **Metros**, sistema local do edifício: `x` para a direita, `y` para baixo na planta |
| `nivel` | Inteiro único por piso. `0` rés-do-chão, `-1` cave |
| `cota_m` | Opcional. Sem ela, os pisos empilham-se por nível com as alturas |
| `contorno` | Opcional. Sem ele, usa o rectângulo que envolve as salas |
| `poligono` | ≥ 3 pontos, área não nula, qualquer forma (salas em L servem) |
| `tipo` da sala | `servidores`, `tecnica`, `escritorio`, `publica`, `quarto`, `eventos`, `restauracao`, `circulacao`, `exterior`, `outra` |
| `planta` | Opcional. `imagem` relativa ao ficheiro; `escala_px_m` > 0; `origem_px` = o pixel que é o (0, 0). Imagem em falta no disco não é erro (o piso desenha-se sem ela) |

Erros param a leitura com o sítio exacto (ex.: `pisos[0].salas[3].poligono: um polígono precisa de pelo menos 3 pontos`).

---

## O que é verificado

| Código | Gravidade | O quê |
| :--- | :--- | :--- |
| **L01** | aviso / info | Cabo visto só de um lado (LLDP desligado numa ponta, ou ponta inalcançável) |
| **L02** | aviso | Cabo existe mas não está na cablagem desenhada |
| **L03** | erro / aviso | Cabo desenhado não encontrado |
| **L04** | aviso | Provável cabo na porta errada |
| **V00** | aviso | Porta do cabo ausente do perfil |
| **V01** | erro | Cabo numa porta desactivada no desenho |
| **V02** | erro | Trunk de um lado, acesso do outro |
| **V03** | erro | VLANs de acesso diferentes nas pontas |
| **V04** | erro | VLAN nativa diferente |
| **V05** | erro | VLAN usada que não atravessa o trunk |
| **V06** | info | VLANs só de um lado do trunk, sem uso hoje |
| **P01** | erro | Porta usa VLAN não declarada no perfil |
| **P02** | aviso | Porta em produção numa VLAN diferente do perfil |
| **P03** | aviso | Porta desligada no desenho mas com ligação activa |
| **P04** | aviso | Ponto final numa VLAN que a porta não serve |
| **E01** | erro / aviso / info | Consumo PoE vs orçamento (> 100 % / > 80 % / sem orçamento) |
| **E02** | aviso | PoE a sair de uma porta com PoE desligado no perfil |
| **R01** | aviso | Ponto único de falha entre comutadores (ponte no grafo; LACP não conta) |
| **D01** | aviso | Perfil sem equipamento na rede |
| **D02** | info | Equipamento sem perfil |
| **D03** | aviso | Equipamento não alcançado pelo mapper |
| **B01** | info | Equipamentos sem posição no edifício |
| **B02** | erro | Posição num edifício, piso ou sala que não existe |
| **B03** | erro | Duas máquinas nas mesmas U de um bastidor |
| **B04** | erro | Máquina fora da altura do bastidor |
| **B05** | erro / aviso | Bastidor num sítio que não existe / fora do polígono da sala |
| **B06** | info | Equipamento com posição no projeto e também num bastidor (vale o bastidor) |
| **B07** | aviso | Máquina ligada a um equipamento de rede que não existe |
| **B08** | erro | O mesmo equipamento de rede montado em dois sítios |
| **M01** | — | Problemas já encontrados pelo mapper |

A cor de cada cabo é a da pior constatação que lhe diz respeito. Verde-acinzentado quer dizer que o cabo existe mas **não havia perfis para comparar a configuração** — um cabo verde a sério foi verificado nas duas pontas.

---

## Sem janela (linha de comandos)

```
EXECUTAR.bat --validar projeto.json
EXECUTAR.bat --validar projeto.json --csv-constatacoes c.csv --csv-cabos cabos.csv
EXECUTAR.bat --cena cena.json projeto.json
```

| Opção | Faz |
| :--- | :--- |
| `--validar` | Lista erros e avisos. Código de saída: **0** sem erros · **1** há erros na rede · **2** não leu o projeto |
| `--csv-constatacoes` | Constatações em CSV (`;`, UTF-8 com BOM — abre bem no Excel) |
| `--csv-cabos` | Lista de cabos: edifício, piso, sala ou bastidor e U, portas e VLANs de cada ponta — para levar ao bastidor |
| `--cena` | A cena 3D em JSON, com as plantas embutidas — abre-se num browser com `index.html?cena=cena.json` (só leitura) |

---

## Limites conhecidos

- O mapper lê a VLAN de acesso de cada porta, não as listas de trunk: as verificações de trunk comparam **desenho contra desenho** nas duas pontas de um cabo real.
- Pontos finais são resumidos por equipamento, não desenhados um a um.
- A detecção de salas em imagem não lê texto (OCR): os nomes dão-se na lista, ou vêm do DXF.
- Fotografias do **exterior** do edifício não servem para gerar o modelo — isso é fotogrametria, outro problema. O que gera o modelo são **plantas** (imagem, PDF, DXF) e o contorno do OpenStreetMap.
- Uma base de código para Windows, Linux e macOS (a janela é HTML via pywebview), em vez das três pastas dos outros projetos: aqui o código seria literalmente igual nas três.
