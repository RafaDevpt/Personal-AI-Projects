# VMware Fleet Console — versão para Linux

**Esta pasta é a aplicação completa para Linux.** As versões de Windows e macOS
vivem nas pastas ao lado e não são precisas aqui.

*This folder is the complete Linux application. The Windows and macOS versions
live in the folders alongside and are not needed here.*

<sub>Created by Redfox using Claude</sub>

---

## Arrancar

```bash
./executar.sh
```

Na primeira execução cria o ambiente virtual e instala as dependências. Nas
seguintes arranca directamente.

Se o repositório foi clonado por uma máquina Windows, o bit de execução
perde-se:

```bash
chmod +x executar.sh cli.sh
```

## Modo de texto

```bash
./cli.sh --servidor vcenter.empresa.local --utilizador administrator@vsphere.local
./cli.sh --json --seccao estado
```

Códigos de saída: **0** nada a apontar, **1** avisos, **2** críticos, **3** não
foi possível ligar.

## O que esta máquina precisa

```bash
./executar.sh --diagnostico
```

| Requisito | Porquê | Sem ele |
| :--- | :--- | :--- |
| Python 3.10+ | — | não arranca |
| `pyvmomi` | a biblioteca da VMware | não há ligação nenhuma |
| `textual` | a interface de texto | resta o modo de texto |
| `TERM` a sério e UTF-8 | desenhar a interface | cai no modo de texto |

O `python3-venv` é um pacote à parte em Debian e Ubuntu. O `executar.sh` diz o
comando certo para a sua distribuição se faltar.

## O que é diferente nesta versão

O `src/vfc/platform_support.py` é o único ficheiro que difere entre as três
versões. Nesta, o que ele sabe e as outras não é **qual é a distribuição** — lê
o `/etc/os-release` para escolher entre `apt`, `dnf`, `pacman`, `zypper` e `apk`,
e usa o `ID_LIKE` para cobrir derivadas que não estão na lista.

Também é aqui que se verifica se o terminal aguenta a interface: `TERM`,
largura, e se a codificação é UTF-8. Numa consola série ou numa sessão com
`LANG=C`, os caracteres de desenho saem trocados — e mais vale saber antes.

A pasta de dados segue o XDG: `$XDG_CONFIG_HOME/VMwareFleetConsole`, ou
`~/.config/VMwareFleetConsole`.

**Não há nenhuma ramificação por sistema operativo dentro desta versão**, e há
um teste que falha se alguém acrescentar uma.

## Correr os testes

```bash
pip install -r requirements-dev.txt
python -m pytest
python -m ruff check .
```

---

Toda a documentação — o que a aplicação faz, como decide, e o que não faz — está
no [README do projecto](../README.md).
