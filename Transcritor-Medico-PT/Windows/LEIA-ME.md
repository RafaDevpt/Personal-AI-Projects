# Windows

**Transcritor Médico PT — arranque em Windows**

---

## Como abrir

Duplo clique em **`EXECUTAR.bat`**. Na primeira execução cria o ambiente e instala as dependências; nas seguintes arranca directamente.

---

## Pré-requisitos

| O quê | Como |
| :--- | :--- |
| **Python 3.10+** | [python.org/downloads](https://www.python.org/downloads/) — marque **Add Python to PATH** |
| **FFmpeg** | `winget install Gyan.FFmpeg` |

O **Tkinter** e o **PortAudio** não precisam de nada: o primeiro vem com o instalador oficial do Python, o segundo vem dentro do pacote `sounddevice`. É a razão por que em Windows há duas linhas nesta tabela e em Linux há quatro.

Se o Tkinter faltar, foi desmarcado durante a instalação do Python — reinstale com a opção *tcl/tk and IDLE* ligada.

---

## Verificar o que falta

```
CLI.bat --diagnostico
```

Diz o estado dos três requisitos e o comando exacto para instalar o que faltar.

---

## Sem interface gráfica

```
CLI.bat --batch --audio-dir "D:\Gravacoes" --output-dir "D:\Texto"
```

Códigos de saída: `0` tudo bem, `1` houve falhas, `2` nada para transcrever, `3` falta a interface gráfica, `130` interrompido.

### Agendar

Agendador de Tarefas → Criar Tarefa → Acção «Iniciar um programa» → `CLI.bat` com os argumentos `--batch`. Convém marcar *Executar independentemente de o utilizador ter sessão iniciada*.

---

## Onde ficam as coisas

| O quê | Onde |
| :--- | :--- |
| Configuração e correcções aprendidas | `%APPDATA%\PortugueseMedicalTranscriber` |
| Registo | `%APPDATA%\PortugueseMedicalTranscriber\transcriber.log` |
| Modelo descarregado | `%USERPROFILE%\.cache\huggingface` |
| Áudios e texto | conforme configurado; por omissão `%USERPROFILE%\Transcricoes` |

Nada é escrito dentro da pasta do programa.

---

## Problemas conhecidos

**«Python não encontrado no PATH».** O instalador do Python tem a caixa *Add Python to PATH* desmarcada por omissão. Reinstale com ela marcada, ou acrescente-o ao PATH à mão.

**O antivírus bloqueia o `.bat` na primeira execução.** Acontece em domínios com políticas restritivas. O ficheiro é texto simples — abra-o num editor para confirmar o que faz antes de autorizar.

**A primeira transcrição demora muito mais do que as seguintes.** É o modelo a ser descarregado (150 MB no `small`). Só acontece uma vez, e depois disso a aplicação é totalmente offline.

---

<sub>Created by Redfox using Claude</sub>
