# VMware Fleet Console — versão para Windows

**Esta pasta é a aplicação completa para Windows.** As versões de Linux e macOS
vivem nas pastas ao lado e não são precisas aqui.

*This folder is the complete Windows application. The Linux and macOS versions
live in the folders alongside and are not needed here.*

<sub>Created by Redfox using Claude</sub>

---

## Arrancar

Duplo clique em **`EXECUTAR.bat`**.

Na primeira execução cria o ambiente virtual e instala as dependências. Nas
seguintes arranca directamente. **Não pede elevação** — esta ferramenta não lê
nada da máquina local.

## Modo de texto

```
CLI.bat --servidor vcenter.empresa.local --utilizador administrator@vsphere.local
CLI.bat --json --seccao estado
```

Códigos de saída: **0** nada a apontar, **1** avisos, **2** críticos, **3** não
foi possível ligar.

## O que esta máquina precisa

```
EXECUTAR.bat --diagnostico
```

| Requisito | Porquê | Sem ele |
| :--- | :--- | :--- |
| Python 3.10+ | — | não arranca |
| Python que **não** seja o da Store | ver abaixo | não arranca |
| `pyvmomi` | a biblioteca da VMware | não há ligação nenhuma |
| `textual` | a interface de texto | resta o modo de texto |
| Windows Terminal | 24 bits de cor e UTF-8 | o `cmd.exe` desenha na mesma, com 16 cores |

## O que é diferente nesta versão

O `src\vfc\platform_support.py` é o único ficheiro que difere entre as três
versões. Nesta, o que ele sabe e as outras não são três armadilhas do Windows:

### O `python.exe` da Microsoft Store

Uma instalação limpa do Windows traz um `python.exe` no PATH que **não é o
Python**: é um atalho que abre a loja. Quem o corre vê a Microsoft Store
abrir-se sozinha e conclui que o programa está avariado.

O `EXECUTAR.bat` detecta-o antes de tentar seja o que for e diz o que fazer:
instalar de [python.org](https://www.python.org/downloads/) e desligar os aliases
em **Definições → Aplicações → Aliases de execução de aplicações**.

### A página de código

É a causa número um de "sai tudo aos quadradinhos". Uma consola portuguesa
arranca na página 850, onde os caracteres de desenho de caixas e os acentos saem
trocados. Os dois lançadores fazem `chcp 65001` (UTF-8) antes de arrancar, o que
resolve na sessão.

### O terminal

O `cmd.exe` clássico desenha a interface — com 16 cores e sem cor verdadeira.
Funciona e fica feio. O **Windows Terminal** e o PowerShell moderno não têm
nenhum dos dois problemas, e o `--diagnostico` diz qual está em uso.

### Onde ficam as definições

`%APPDATA%\VMwareFleetConsole` — a pasta **itinerante**, e não a local, de
propósito: as definições e as impressões digitais dos certificados aceites devem
seguir o utilizador para outra máquina do domínio.

**Não há nenhuma ramificação por sistema operativo dentro desta versão**, e há
um teste que falha se alguém acrescentar uma.

## Correr os testes

```
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest
python -m ruff check .
```

---

Toda a documentação — o que a aplicação faz, como decide, e o que não faz — está
no [README do projecto](../README.md).
