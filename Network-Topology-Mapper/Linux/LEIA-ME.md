# Linux

**Network Topology Mapper — arranque em Linux**

---

## Como abrir

```bash
chmod +x executar.sh      # só na primeira vez, se o bit não tiver vindo do Git
./executar.sh
```

Na primeira execução verifica os pré-requisitos, cria o ambiente virtual e instala as dependências.

---

## Pré-requisitos

| O quê | Para quê | Sem ele |
| :--- | :--- | :--- |
| **Python 3.10+** | A aplicação | Não arranca |
| **Tkinter** | Base da interface gráfica | A janela não abre; resta o `cli.sh` |

### Por distribuição

```bash
# Debian, Ubuntu, Mint, Pop!_OS
sudo apt install python3 python3-venv python3-tk

# Fedora, RHEL, Rocky, Alma
sudo dnf install python3 python3-tkinter

# Arch, Manjaro
sudo pacman -S python tk

# openSUSE
sudo zypper install python3 python3-tk
```

O lançador reconhece a distribuição pelo `/etc/os-release` e, se faltar alguma coisa, imprime o comando certo para **a sua** máquina — incluindo em derivadas que não estão nesta lista, pelo campo `ID_LIKE`.

---

## Sem interface gráfica

```bash
./cli.sh --help
```

Para agendar com o cron:

```cron
0 2 * * * /caminho/para/o/projecto/Linux/cli.sh [argumentos] >> ~/registo.log 2>&1
```

O `cli.sh` não prepara o ambiente de propósito. Um script agendado que decide instalar dependências a meio da noite é um script que um dia enche o disco sem ninguém dar por isso — se o ambiente faltar, ele diz e sai com `3`.

---

## Onde ficam as coisas

Configuração e registo em `~/.config`, respeitando o `XDG_CONFIG_HOME` se estiver definido. Nada é escrito dentro da pasta do programa.

---

## Problemas conhecidos

**`ensurepip is not available`.** É o Debian e o Ubuntu a separarem o `venv` do Python base: `sudo apt install python3-venv`.

**A janela abre com letras erradas.** Falta uma fonte que a interface conheça: `sudo apt install fonts-dejavu`.

**Em Wayland a janela abre com um tamanho estranho.** O Tk ainda corre por XWayland na maioria das distribuições. Redimensionar uma vez resolve para essa sessão.

---

<sub>Created by Redfox using Claude</sub>
