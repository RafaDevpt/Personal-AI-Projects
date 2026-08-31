# macOS

**Transcritor Médico PT — arranque em macOS**

---

## Como abrir

Duplo clique em **`executar.command`** no Finder.

Se o bit de execução não tiver vindo do Git:

```bash
chmod +x macOS/executar.command macOS/cli.sh
```

Na primeira execução o macOS pode recusar abrir o ficheiro por ter vindo de fora. **Clique com o botão direito → Abrir** e confirme; é preciso uma vez só.

---

## Pré-requisitos

O macOS não traz nenhum deles. Todos vêm do [Homebrew](https://brew.sh).

```bash
brew install python ffmpeg portaudio python-tk
```

| O quê | Para quê | Sem ele |
| :--- | :--- | :--- |
| **Python 3.10+** | A aplicação | Não arranca |
| **FFmpeg** | Descodifica o áudio | Não há transcrição nenhuma |
| **python-tk** | Base da interface gráfica | A janela não abre; resta o `cli.sh --batch` |
| **PortAudio** | Gravação pelo microfone | O ditado fica indisponível |

### Não use o Python do sistema

O `/usr/bin/python3` que vem com o macOS existe para uso interno da Apple, traz uma versão de Tk antiga que desenha janelas com aspecto errado, e a Apple já anunciou que o vai retirar. O lançador avisa quando detecta que está a ser usado.

```bash
brew install python
```

---

## O microfone

Na primeira vez que ditar, o macOS pergunta se a aplicação pode usar o microfone. **A pergunta aparece uma vez.** Se for recusada, o ditado deixa de funcionar sem explicação nenhuma, e a permissão só se repõe em:

> Definições do Sistema → Privacidade e Segurança → Microfone

A autorização fica associada ao **Terminal** (ou ao iTerm), e não à aplicação — é o Terminal que está a correr o Python.

---

## Apple Silicon e Intel

Ambos funcionam. O `faster-whisper` tem pacotes nativos para arm64, por isso um M1 ou superior corre à velocidade que se espera, sem Rosetta.

A única diferença prática é onde o Homebrew instala — `/opt/homebrew` nos Apple Silicon, `/usr/local` nos Intel — e o lançador acrescenta os dois ao PATH, para que o FFmpeg seja encontrado em qualquer dos casos.

---

## Verificar o que falta

```bash
./macOS/cli.sh --diagnostico
```

---

## Sem interface gráfica

```bash
./macOS/cli.sh --batch --audio-dir ~/Gravacoes --output-dir ~/Texto
```

### Agendar com o launchd

Em macOS o caminho certo é o `launchd`, não o cron. Grave isto como
`~/Library/LaunchAgents/pt.redfox.transcritor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>pt.redfox.transcritor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/UTILIZADOR/Transcritor-Medico-PT/macOS/cli.sh</string>
        <string>--batch</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>2</integer>
        <key>Minute</key><integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/transcritor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/transcritor.err</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/pt.redfox.transcritor.plist
```

O `cli.sh` acrescenta os caminhos do Homebrew ao PATH por causa disto: o `launchd` arranca com um PATH mínimo, e sem essa linha a tarefa falha todas as noites com «FFmpeg não encontrado» enquanto o mesmo comando corre perfeitamente no Terminal.

---

## Onde ficam as coisas

| O quê | Onde |
| :--- | :--- |
| Configuração e correcções aprendidas | `~/Library/Application Support/PortugueseMedicalTranscriber` |
| Registo | `~/Library/Application Support/PortugueseMedicalTranscriber/transcriber.log` |
| Modelo descarregado | `~/.cache/huggingface` |
| Áudios e texto | conforme configurado; por omissão `~/Transcricoes` |

A pasta de configuração segue a convenção do macOS, e não a do Linux. Uma pasta `.config` escondida na raiz da conta é hábito de Linux; num Mac ninguém a vai lá procurar.

---

## Problemas conhecidos

**«não pode ser aberto porque provém de um programador não identificado».** É o Gatekeeper. Botão direito → Abrir, uma vez.

**A janela abre desfocada num ecrã Retina.** Acontece com o Python do sistema. Com o Python do Homebrew não acontece.

**O ditado grava silêncio.** Quase sempre é a permissão do microfone negada ao Terminal — ver acima. O medidor de nível na janela de ditado confirma-o: se não mexe enquanto fala, não está a chegar áudio nenhum.

---

<sub>Created by Redfox using Claude</sub>
