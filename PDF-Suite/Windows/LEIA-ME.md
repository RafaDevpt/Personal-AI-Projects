# Windows

**PDF Suite — arranque em Windows**

---

## Como abrir

Duplo clique em **`EXECUTAR.bat`**. Na primeira execução cria o ambiente e instala as dependências; nas seguintes arranca directamente.

---

## Pré-requisitos

| O quê | Como |
| :--- | :--- |
| **Python 3.10+** | [python.org/downloads](https://www.python.org/downloads/) — marque **Add Python to PATH** |
| **poppler** *(opcional)* | `winget install oschwartz10612.Poppler` — só para o editor visual de campos |

O **Tkinter** vem com o instalador oficial do Python. Se faltar, foi desmarcado durante a instalação — reinstale com a opção *tcl/tk and IDLE* ligada.

---

## Sem interface gráfica

```
Windows\CLI.bat --help
```

Para agendar: Agendador de Tarefas → Criar Tarefa → Acção «Iniciar um programa» → `CLI.bat` com os argumentos.

---

## Onde ficam as coisas

Configuração e registo em `%APPDATA%`. **Nada é escrito dentro da pasta do programa** — ela pode estar numa partilha só de leitura, e o que a aplicação produz não deve acabar num repositório por distracção.

---

## Problemas conhecidos

**«Python não encontrado no PATH».** O instalador tem a caixa *Add Python to PATH* desmarcada por omissão. Reinstale com ela marcada.

**O antivírus bloqueia o `.bat` na primeira execução.** Acontece em domínios com políticas restritivas. O ficheiro é texto simples — abra-o num editor para confirmar o que faz antes de autorizar.

---

<sub>Created by Redfox using Claude</sub>
