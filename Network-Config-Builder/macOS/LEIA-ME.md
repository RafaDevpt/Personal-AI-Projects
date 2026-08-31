# macOS

**Network Config Builder — arranque em macOS**

---

## Como abrir

Duplo clique em **`executar.command`** no Finder.

Se o bit de execução não tiver vindo do Git:

```bash
chmod +x macOS/executar.command macOS/cli.sh
```

Na primeira vez o macOS pode recusar abrir o ficheiro por ter vindo de fora. **Botão direito → Abrir** e confirme; é preciso uma vez só.

---

## Pré-requisitos

Tudo vem do [Homebrew](https://brew.sh):

```bash
brew install python python-tk
```

| O quê | Para quê | Sem ele |
| :--- | :--- | :--- |
| **Python 3.10+** | A aplicação | Não arranca |
| **python-tk** | Base da interface gráfica | A janela não abre; resta o `cli.sh` |

### Não use o Python do sistema

O `/usr/bin/python3` existe para uso interno da Apple, traz uma versão de Tk antiga que desenha janelas com aspecto errado, e a Apple já anunciou que o vai retirar. O lançador avisa quando detecta que está a ser usado.

---

## Apple Silicon e Intel

Ambos funcionam, sem Rosetta. A única diferença prática é onde o Homebrew instala — `/opt/homebrew` nos Apple Silicon, `/usr/local` nos Intel — e o lançador acrescenta os dois ao PATH.

---

## Sem interface gráfica

```bash
./macOS/cli.sh --help
```

Para agendar, o `launchd` é o caminho certo em macOS. O `cli.sh` acrescenta os caminhos do Homebrew ao PATH por causa disso: o `launchd` arranca com um PATH mínimo, e sem essa linha uma tarefa agendada falha todas as noites enquanto o mesmo comando corre perfeitamente no Terminal.

---

## Onde ficam as coisas

Configuração e registo em `~/Library/Application Support`, que é a convenção do macOS. Nada é escrito dentro da pasta do programa.

---

## Problemas conhecidos

**«não pode ser aberto porque provém de um programador não identificado».** É o Gatekeeper. Botão direito → Abrir, uma vez.

**A janela abre desfocada num ecrã Retina.** Acontece com o Python do sistema. Com o Python do Homebrew não acontece.

---

<sub>Created by Redfox using Claude</sub>
