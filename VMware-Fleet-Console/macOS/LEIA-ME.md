# VMware Fleet Console — versão para macOS

**Esta pasta é a aplicação completa para macOS.** As versões de Windows e Linux
vivem nas pastas ao lado e não são precisas aqui.

*This folder is the complete macOS application. The Windows and Linux versions
live in the folders alongside and are not needed here.*

<sub>Created by Redfox using Claude</sub>

---

## Arrancar

Duplo clique em **`executar.command`**.

Se o repositório foi clonado por uma máquina Windows, o bit de execução perde-se
e o duplo clique não faz nada:

```bash
chmod +x executar.command cli.command
```

Na primeira execução cria o ambiente virtual e instala as dependências.

**Não pede elevação e não precisa de Acesso Total ao Disco** — esta ferramenta
não lê nada da máquina local. Fala com o vCenter pela rede, e as permissões que
lhe interessam são as da conta do vSphere.

## Modo de texto

```bash
./cli.command --servidor vcenter.empresa.local --utilizador administrator@vsphere.local
./cli.command --json --seccao estado
```

Códigos de saída: **0** nada a apontar, **1** avisos, **2** críticos, **3** não
foi possível ligar.

## O que este Mac precisa

```bash
./executar.command --diagnostico
```

| Requisito | Porquê | Sem ele |
| :--- | :--- | :--- |
| Python 3.10+ | — | não arranca |
| `pyvmomi` | a biblioteca da VMware | não há ligação nenhuma |
| `textual` | a interface de texto | resta o modo de texto |
| Homebrew | **não é preciso** | os conselhos de instalação ficam genéricos |

## O que é diferente nesta versão

O `src/vfc/platform_support.py` é o único ficheiro que difere entre as três
versões. Nesta, o que ele sabe e as outras não são duas coisas:

### O Python do sistema

O macOS traz um `/usr/bin/python3` que serve as ferramentas de linha de comandos
da Apple. Instalar pacotes nele é desaconselhado pela própria Apple, e nas
versões recentes o `pip` recusa-se com um erro —
`externally-managed-environment` — que ninguém percebe à primeira.

O lançador prefere um Python do Homebrew quando existe, e cria sempre um
ambiente virtual, o que resolve o problema de qualquer maneira.

### Os dois prefixos do Homebrew

`/opt/homebrew` em **Apple Silicon**, `/usr/local` em **Intel**. É a razão de
metade dos "funciona no meu Mac e não no teu": o mesmo comando, dois sítios,
conforme o processador. O lançador e o diagnóstico escolhem o certo.

### Onde ficam as definições

`~/Library/Application Support/VMwareFleetConsole` — a convenção da Apple, e não
o `~/.config` do Linux. Não é gosto: é onde o Time Machine procura e onde um
utilizador de Mac espera encontrar as definições de uma aplicação. Um
`XDG_CONFIG_HOME` definido por outra ferramenta é ignorado, e há um teste que o
garante.

**Não há nenhuma ramificação por sistema operativo dentro desta versão**, e há
um teste que falha se alguém acrescentar uma.

## Correr os testes

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
python -m ruff check .
```

---

Toda a documentação — o que a aplicação faz, como decide, e o que não faz — está
no [README do projecto](../README.md).
