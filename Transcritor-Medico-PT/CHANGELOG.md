# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [5.1.0] — 2026-08-31

**PT** · Suporte a Linux e macOS.
**EN** · Linux and macOS support.

### Um lançador por sistema · One launcher per system

- Três pastas — `Windows/`, `Linux/`, `macOS/` — cada uma com o seu lançador e
  um `LEIA-ME.md` com os pré-requisitos daquele sistema. O `src/` continua a ser
  um só: o que muda entre sistemas é o arranque e o que é preciso instalar
  antes, não a aplicação. Três cópias do código seriam três sítios para corrigir
  o mesmo erro
- `Linux/executar.sh` reconhece a distribuição pelo `/etc/os-release` e imprime
  o comando do gestor de pacotes certo — `apt`, `dnf`, `pacman`, `zypper` ou
  `apk`. Pelo campo `ID_LIKE`, funciona também em distribuições derivadas que
  não estão em lista nenhuma, como o Linux Mint ou o Pop!_OS
- `macOS/executar.command`, abrível com duplo clique no Finder, com os dois
  caminhos do Homebrew no PATH: um script aberto pelo Finder não herda o
  ambiente da shell, e o `brew` instala em `/opt/homebrew` nos Apple Silicon e
  em `/usr/local` nos Intel
- `.gitattributes` que fixa LF nos scripts e CRLF nos `.bat`. Sem isto, um clone
  numa máquina com `core.autocrlf=true` produz um `executar.sh` que falha em
  Linux com `bad interpreter: /usr/bin/env bash^M` — uma mensagem que não diz
  nada a quem a lê pela primeira vez, sobre um ficheiro que está correcto

### Novo · Added

- `platform_support.py` — o único sítio onde as diferenças entre sistemas
  existem. Detecta o sistema e a família da distribuição, e devolve o comando
  de instalação certo para cada componente
- `--diagnostico` — verifica os três requisitos que o `pip` não instala e diz o
  que falta, com o comando exacto. É o primeiro comando a que alguém recorre
  quando uma instalação nova não arranca, e corre antes de a configuração ser
  carregada precisamente por isso
- 40 testes das diferenças entre sistemas. Passando o sistema e o
  `/etc/os-release` como argumentos, os três caminhos verificam-se a partir de
  qualquer máquina — o que importa não é se o FFmpeg está instalado, é se a
  aplicação diz o comando certo quando ele falta

### Alterado · Changed

- **A pasta de configuração em macOS passou a `~/Library/Application Support`.**
  Antes caía no ramo do XDG e ia parar a `~/.config`, que é hábito de Linux e
  num Mac ninguém lá vai procurar
- **O FFmpeg é verificado antes de a transcrição começar.** Até aqui a sua
  ausência só aparecia como excepção no fim de uma tentativa, com o utilizador
  a olhar para uma barra de progresso que não ia a lado nenhum. É a causa mais
  comum de uma instalação nova não funcionar em Linux e macOS
- **O `sounddevice` passou a apanhar o `OSError`, e não só o `ImportError`.** Em
  Linux o pacote de Python instala-se sem problema e falha na importação porque
  falta a biblioteca de C do PortAudio. A mensagem antiga dizia que faltava um
  pacote de Python, e quem a lesse corria `pip install sounddevice` outra vez,
  com sucesso, e continuava sem ditado
- As mensagens de dependência em falta deixaram de assumir a Debian. Um
  utilizador de Fedora que leia «sudo apt install» conclui, com razão, que a
  aplicação não foi pensada para o sistema dele

---

## [5.0.0] — 2026-08-30

**PT** · Ditado pelo microfone e suporte multilingue.
**EN** · Microphone dictation and multilingual support.

### Adicionado · Added

- **Modo de ditado em ecrã inteiro** (`F2`). A aplicação passa a gravar do
  microfone: até aqui só transcrevia ficheiros gravados noutro lado, o que
  obrigava a um gravador de mão e a copiar ficheiros para uma pasta antes de
  ver texto. Cronómetro grande, medidor de nível, e aviso quando não se ouve
  nada há mais de três segundos — a diferença entre «a aplicação está viva» e
  «o microfone está ligado» é uma consulta inteira ditada para o vazio
- **Quatro pacotes clínicos**: português europeu, inglês britânico, espanhol de
  Espanha e francês de França, cada um com vocabulário protegido, conversão de
  variante regional e pontuação ditada próprios. A transcrição passa a
  funcionar em qualquer língua que o modelo reconheça; a camada clínica aplica-
  se nestas quatro
- `recorder.py` — gravação a 16 kHz mono, escrita em disco à medida que grava.
  O `sounddevice` é opcional: sem ele a aplicação transcreve ficheiros como
  sempre fez e o ditado explica o que falta
- Escolha de língua e interruptor de pontuação ditada nas definições

### Corrigido · Fixed

- **A pontuação ditada nunca era aplicada.** A tabela `SPOKEN_PUNCTUATION`
  existia desde a primeira versão, era validada pelos testes e estava
  documentada — mas nenhum código a usava. Dizer «ponto final» em voz alta
  deixava a palavra escrita no texto. Passa a ser convertida, nas quatro
  línguas, com um interruptor próprio por ser a transformação mais arriscada da
  aplicação

### Alterado · Changed

- **`medical_terms.py` deixou de existir.** Os dados vivem agora em
  `languages/`, um ficheiro por língua, com a mesma regra de sempre: apenas
  dados, revisíveis por pessoal clínico sem perceber de código
- Configurações antigas continuam a funcionar: o código curto `"pt"` é
  reconhecido e convertido para `"pt-PT"` ao carregar
- Escala tipográfica subiu um ponto em todos os níveis. Não é estética: a 12
  pontos, num painel de 14 polegadas, o corpo de texto obrigava a aproximar-se
  do ecrã — e aproximar-se do ecrã durante uma consulta é tempo em que não se
  está a olhar para o doente

---

## [4.0.1] — 2026-08-30

**PT** · Correcções, saneamento e integração contínua.
**EN** · Fixes, sanitisation and continuous integration.

### Infra-estrutura · Infrastructure

- `.gitignore` — o repositório não tinha nenhum. Impede que `config.json`,
  relatórios gerados, `.venv/` e `__pycache__/` cheguem a ser versionados
- Integração contínua em GitHub Actions: `ruff` e `pytest` em `windows-latest`
  a cada `push` e cada `pull request` sobre este branch
- Árvore limpa de avisos do `ruff` sob a configuração que o projecto já
  declarava em `pyproject.toml`, que até aqui não passava

### Corrigido · Fixed

- `medical_terms.py` — a validação da ordem das expressões de pontuação passa a
  usar `itertools.pairwise`, que diz o que faz, em vez de `zip(l, l[1:])`
- `corrections.py` — o `zip()` sobre os blocos alinhados declara `strict=True`.
  A guarda acima já garante comprimentos iguais; agora essa garantia está
  escrita no código
- `gui/dialogs.py` — a reposição do cursor após substituição passa a
  `contextlib.suppress`, com a razão documentada: perder a posição do cursor é
  aceitável, rebentar com a caixa de texto não é

### Adicionado · Added

- `CLI.bat` — lançador de linha de comandos, para transcrever lotes de
  gravações sem abrir a interface gráfica

---

## [4.0.0] — 2026-08-27

**PT** · Reescrita completa. Versão anterior (3.0 Premium) descontinuada.
**EN** · Complete rewrite. The previous version (3.0 Premium) is discontinued.

### Adicionado · Added

- Interface CustomTkinter com tema claro/escuro e paleta de baixa saturação
- Localizar e substituir no editor (`Ctrl+F`), com substituição em bloco
  anulável num só `Ctrl+Z`
- Janela de gestão das correções aprendidas, com remoção individual de regras
- Modo lote via `--batch`, para transcrever pastas sem interface
- Escrita incremental: o texto aparece no editor à medida que é transcrito
- Cabeçalho de proveniência nos `.txt` (modelo, duração, idioma, data)
- Exportação para Markdown com metadados YAML
- Registo rotativo em ficheiro, com garantia de não conter texto clínico
- Deteção automática de GPU CUDA com recuo silencioso para CPU
- Cancelamento de transcrição em curso
- Aviso ao fechar ou mudar de ficheiro com texto por exportar
- 30 testes automatizados

### Alterado · Changed

- **Motor**: `openai-whisper` → `faster-whisper`. Cerca de 4× mais rápido em
  CPU, aproximadamente metade da memória, e dispensa o PyTorch (menos ~2,5 GB
  de instalação)
- **Vocabulário clínico**: agora entregue ao modelo como contexto inicial,
  corrigindo à cabeça em vez de remendar com regex depois
- **Dicionário**: uma única expressão regular compilada substitui uma passagem
  por termo; ordenação por comprimento para os termos compostos ganharem
- **Aprendizagem**: `difflib` substitui a comparação posicional, funcionando
  quando o utilizador acrescenta ou remove palavras
- **Capitalização**: normalização por frase, com lista de abreviaturas, em vez
  de acrescentar um ponto no fim do texto
- **Caminhos**: configuráveis e persistidos, em vez do `A:\` fixo no código
- **Codificação**: `.txt` gravado em UTF-8 com BOM e quebras de linha Windows,
  para o Bloco de Notas mostrar os acentos corretamente

### Corrigido · Fixed

- Erros ortográficos no próprio dicionário: `ultrasssom` → `ultrassom`,
  `biópia` → `biópsia`
- Substituições destruíam a maiúscula inicial da frase
- `except:` nu no carregamento de configuração engolia `KeyboardInterrupt`
- Cerca de 150 entradas do tipo `"paciente" → "paciente"`, sem efeito, que
  custavam uma passagem de regex cada
- Transcrição bloqueava a interface por não correr em fio separado
- Ficheiro de saída existente era sobreposto em silêncio
- Botões de formatação do editor sem efeito no ficheiro exportado (removidos)

### Removido · Removed

- `openai-whisper` e a dependência de PyTorch
- Formatação a negrito/itálico no editor (não sobrevive ao `.txt`)
- Caminho fixo para a unidade `A:`
- Ficheiros `.bat` de diagnóstico dispersos, substituídos por `--verbose`

### Segurança · Security

- `.gitignore` bloqueia áudios, transcrições, correções aprendidas e registos
- Registo nunca escreve texto transcrito, apenas contagens
- Configuração gravada em `%APPDATA%`, fora da árvore do repositório

---

## [3.0.0] — 2025-12-06

**PT** · Versão anterior, baseada em `openai-whisper`. Não mantida.
**EN** · Previous version, based on `openai-whisper`. Not maintained.

---

*Created by Redfox using Claude*
