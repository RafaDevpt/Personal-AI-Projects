# Changelog

Todas as alterações notáveis a este projecto.
*All notable changes to this project.*

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e
a numeração segue o [Versionamento Semântico](https://semver.org/lang/pt-BR/).

<sub>Created by Redfox using Claude</sub>

---

## [1.0.0] — 2026-09-08

Primeira versão. Três aplicações independentes — `Windows/`, `Linux/` e
`macOS/` — com **691 testes** a passar (235 + 225 + 231).

### Monitorização

- Inventário completo de **vCenter** ou de um **anfitrião ESXi** ligado
  directamente: anfitriões, máquinas, datastores, snapshots e alarmes, lidos
  numa chamada por tipo através do `PropertyCollector` do vSphere.
- Painel com cinco separadores, o primeiro dos quais é o dos achados — porque a
  pergunta que traz alguém aqui é "está tudo bem", não "quantas máquinas há".
- **Regras de saúde** com limiares editáveis: espaço em datastore, idade e
  profundidade de cadeia de snapshots, VMware Tools, uptime e carga de
  anfitrião, sensores de hardware e alarmes do vCenter.
- Regra de **capacidade do parque**: se o maior anfitrião cair, a memória em uso
  cabe no que resta? Ignora anfitriões em manutenção, que não recebem máquinas.
- Alarmes reconhecidos são **despromovidos a informação** — sem isso, um parque
  com um alarme reconhecido em Março nunca mais estaria verde.

### Operações

- Máquinas: ligar, encerrar e reiniciar pelo sistema convidado, desligar à
  força, reset e suspender.
- Snapshots: criar (com `quiesce` quando há Tools), apagar e reverter.
- Anfitriões: entrar e sair do modo de manutenção, reiniciar e desligar.
- Todas as operações passam por uma **guarda** que decide sem tocar na rede, e a
  execução verifica-a **outra vez** — um botão novo esbarra na mesma
  verificação.
- As operações destrutivas exigem que se **escreva o nome do objecto**. Não há
  botão de confirmar: um botão ensina a carregar em confirmar.

### Certificados

- **Confiança na primeira utilização** em vez de `CERT_NONE`: valida a cadeia,
  e quando não valida mostra a impressão digital SHA-256 e espera por uma
  decisão antes de enviar qualquer credencial.
- Uma **impressão digital diferente pára a ligação** e mostra as duas lado a
  lado.
- O modo de texto nunca aceita um certificado por omissão.

### Credenciais

- **Nenhuma senha é escrita em disco**, e não há campo para o fazer. Há testes
  que falham se alguém acrescentar um, e que verificam que uma senha metida à
  mão no ficheiro é ignorada.
- Não há opção `--senha` na linha de comandos: um argumento fica visível no
  `ps`. Para automação existe a variável `VFC_PASSWORD`.

### Modo de texto

- `--texto` e `--json`, com secções (`estado`, `anfitrioes`, `maquinas`,
  `datastores`, `snapshots`).
- Códigos de saída **0 / 1 / 2 / 3** — o 3 distingue "não liguei" de "está tudo
  mal".
- **Não escreve no vSphere**, por decisão, e há um teste que o garante.

### Por sistema

- **Windows** — detecta o `python.exe` da Microsoft Store antes de ele abrir a
  loja, distingue o Windows Terminal da consola clássica, e põe a página de
  código a 65001. Definições em `%APPDATA%` (itinerante).
- **Linux** — lê o `/etc/os-release` com queda para `ID_LIKE`, escolhendo entre
  `apt`, `dnf`, `pacman`, `zypper` e `apk`; verifica `TERM`, largura e
  codificação. Definições em XDG.
- **macOS** — trata do Python do sistema e dos dois prefixos do Homebrew
  (`/opt/homebrew` em Apple Silicon, `/usr/local` em Intel). Definições em
  `~/Library/Application Support`.
- Cada versão tem um teste que **falha se alguém acrescentar uma ramificação por
  sistema operativo** lá dentro.

### Infra-estrutura

- CI com matriz de três runners nativos — `windows-latest`, `ubuntu-latest`,
  `macos-latest`. Lint com `ruff`, testes com `pytest`, e o `--diagnostico` a
  correr contra o sistema verdadeiro.
- Nenhum teste precisa de um vCenter: o parque de testes é inventado no
  `conftest.py`.

[1.0.0]: https://github.com/RafaDevpt/Personal-AI-Projects/tree/VMware-Fleet-Console
