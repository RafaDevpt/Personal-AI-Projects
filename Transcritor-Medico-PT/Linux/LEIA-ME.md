# Linux

**Transcritor Médico PT — arranque em Linux**

---

## Como abrir

```bash
chmod +x Linux/executar.sh      # só na primeira vez, se o bit não tiver vindo do Git
./Linux/executar.sh
```

Na primeira execução verifica os pré-requisitos, cria o ambiente virtual e instala as dependências. Nas seguintes arranca directamente.

---

## Pré-requisitos

Três coisas que o `pip` **não** instala, e que em Linux não vêm por omissão em nenhuma distribuição.

| O quê | Para quê | Sem ele |
| :--- | :--- | :--- |
| **FFmpeg** | Descodifica o mp3, o m4a e o wav antes de o modelo os ouvir | Não há transcrição nenhuma |
| **Tkinter** | Base da interface gráfica | A janela não abre; resta o `cli.sh --batch` |
| **PortAudio** | Gravação pelo microfone | O ditado fica indisponível; transcrever ficheiros funciona |

### Debian, Ubuntu, Mint, Pop!_OS, Raspberry Pi OS

```bash
sudo apt install python3 python3-venv python3-tk ffmpeg libportaudio2
```

### Fedora, RHEL, Rocky, Alma

```bash
sudo dnf install python3 python3-tkinter ffmpeg-free portaudio
```

*O `ffmpeg-free` está nos repositórios oficiais. Se precisar de codecs que ele não traz, o RPM Fusion tem o `ffmpeg` completo.*

### Arch, Manjaro, EndeavourOS

```bash
sudo pacman -S python tk ffmpeg portaudio
```

### openSUSE

```bash
sudo zypper install python3 python3-tk ffmpeg portaudio
```

### Alpine

```bash
sudo apk add python3 python3-tkinter ffmpeg portaudio
```

O lançador reconhece a distribuição pelo `/etc/os-release` e, se faltar alguma coisa, imprime o comando certo para **a sua** máquina — incluindo em distribuições derivadas que não estão nesta lista, pelo campo `ID_LIKE`.

---

## Verificar o que falta

```bash
./Linux/cli.sh --diagnostico
```

---

## Sem interface gráfica

```bash
./Linux/cli.sh --batch --audio-dir ~/Gravacoes --output-dir ~/Texto
```

Códigos de saída: `0` tudo bem, `1` houve falhas, `2` nada para transcrever, `3` ambiente por preparar, `130` interrompido.

### Agendar com o cron

```cron
0 2 * * * /caminho/para/Transcritor-Medico-PT/Linux/cli.sh --batch >> ~/transcricoes.log 2>&1
```

O `cli.sh` não prepara o ambiente de propósito. Um script agendado que decide instalar dependências a meio da noite é um script que um dia enche o disco sem ninguém dar por isso — se o ambiente faltar, ele diz e sai com `3`.

---

## Onde ficam as coisas

| O quê | Onde |
| :--- | :--- |
| Configuração e correcções aprendidas | `~/.config/PortugueseMedicalTranscriber` |
| Registo | `~/.config/PortugueseMedicalTranscriber/transcriber.log` |
| Modelo descarregado | `~/.cache/huggingface` |
| Áudios e texto | conforme configurado; por omissão `~/Transcricoes` |

O `XDG_CONFIG_HOME` é respeitado se estiver definido.

---

## Problemas conhecidos

**`ensurepip is not available` ao criar o ambiente virtual.** É o Debian e o Ubuntu a separarem o `venv` do Python base:

```bash
sudo apt install python3-venv
```

**A janela abre mas as letras estão erradas ou minúsculas.** Falta uma fonte que a interface conheça. A aplicação tem alternativas, mas a mais segura é ter a DejaVu:

```bash
sudo apt install fonts-dejavu     # ou o equivalente da sua distribuição
```

**O microfone não aparece, mas o `sounddevice` importa.** Em sistemas com PipeWire falta muitas vezes a camada de compatibilidade:

```bash
sudo apt install pipewire-alsa
```

**Em Wayland a janela abre com um tamanho estranho.** O Tk ainda corre por XWayland na maioria das distribuições. Não há volta a dar do lado da aplicação; redimensionar uma vez resolve para essa sessão.

**A transcrição é muito lenta.** Verifique que não está a usar o modelo `large-v3` numa máquina sem GPU. O `small` é o recomendado e chega para ditado clínico.

---

<sub>Created by Redfox using Claude</sub>
