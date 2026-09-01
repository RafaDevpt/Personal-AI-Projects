# macOS

**Laboratório Virtual — arranque em macOS**

Esta pasta é uma versão completa e independente, escrita em `bash`. Não partilha código com as pastas `Windows/` e `Linux/`: fala com o QEMU e com a Hypervisor.framework da Apple.

---

## Como abrir

Duplo clique em **`executar.command`**.

Se o Finder recusar — acontece quando o repositório foi copiado por uma máquina Windows, que não preserva a permissão de execução:

```bash
chmod +x executar.command src/laboratorio-virtual.sh
```

Na primeira vez, o Gatekeeper pode avisar que o ficheiro foi descarregado da Internet. Botão direito › Abrir autoriza-o de uma vez por todas.

---

## Escrito para o bash 3.2

**O `bash` de um Mac é o 3.2, de 2007.** A Apple congelou-o quando o bash passou para GPLv3 e nunca mais lhe tocou. Não é uma curiosidade: significa que aqui não há `mapfile`, não há arrays associativos, não há `${variável^^}`.

Toda esta versão está escrita para o 3.2, de propósito, para não obrigar ninguém a instalar um bash do Homebrew só para correr um programa. Um ficheiro copiado da versão de Linux que use qualquer uma dessas coisas rebenta com um erro de sintaxe que parece um erro de escrita.

E **não há `sha256sum` num Mac** — é o `shasum -a 256`. É a diferença mais silenciosa entre as duas versões: um script de Linux corre num Mac até à linha em que verifica a soma, e falha exactamente no passo que não pode falhar.

---

## Os hipervisores, e porque a escolha é mais estreita aqui

| | Serve | Notas |
| :--- | :--- | :--- |
| **QEMU** | Todos os Macs | Usa a Hypervisor.framework para acelerar. É o que este programa conduz |
| **VirtualBox** | Só Macs Intel | A pré-visualização para Apple Silicon é uma pré-visualização há anos |
| **UTM** | Todos os Macs | A melhor opção para quem quer janelas. O programa aponta, não conduz |

Num Mac com chip da Apple, o programa **nem sequer oferece** o VirtualBox — oferecer é deixar alguém perder uma tarde a perceber porque é que não arranca.

O UTM não é conduzido daqui porque criar uma máquina de UTM a partir de um script exige montar um pacote `.utm` à mão, e um pacote mal montado dá uma máquina que abre e não arranca. Apontar é mais honesto do que fingir.

---

## A arquitectura manda mais aqui do que em qualquer outro sítio

Num Mac com chip da Apple, o QEMU acelerado **só corre convidados ARM**. Uma imagem de x86_64 corre por emulação pura — dez a vinte vezes mais devagar, o suficiente para uma instalação de Ubuntu passar de vinte minutos a uma tarde.

Por isso o catálogo é filtrado pela arquitectura **antes** de aparecer no ecrã, e o aviso da emulação aparece **antes** da confirmação e não depois: depois de descarregar três gigabytes já não é um aviso, é uma desculpa.

Há imagens ARM64 no catálogo para o Ubuntu Server e para o Debian.

---

## Pré-requisitos

| O quê | Como |
| :--- | :--- |
| **macOS** | 11 (Big Sur) ou superior |
| **bash** | 3.2, que vem no sistema |
| **jq** | `brew install jq` |
| **QEMU** | `brew install qemu` |
| **gpg** *(opcional)* | `brew install gnupg` |
| **UTM** *(alternativa)* | `brew install --cask utm` |

O `curl` e o `shasum` já vêm no macOS.

O lançador acrescenta ao `PATH` os dois prefixos do Homebrew — `/opt/homebrew` nos Apple Silicon e `/usr/local` nos Intel. Sem isso, um script aberto pelo Finder não herda o ambiente da shell, e o QEMU está instalado e o programa jura que não está.

```bash
./executar.command --diagnostico
```

---

## macOS como convidado

O acordo de licença da Apple **só permite virtualizar o macOS sobre equipamento da Apple**, e no máximo duas instâncias por máquina. Num Mac, isto é legítimo — e é por isso que esta versão do programa avança onde as outras duas recusam.

O instalador vem da própria Apple:

```bash
softwareupdate --list-full-installers
sudo softwareupdate --fetch-full-installer --full-installer-version 15.0
```

É a única origem legítima, e a única em que o ficheiro vem assinado pela Apple. **Imagens de macOS oferecidas por terceiros não são legítimas, mesmo quando funcionam.**

Depois de o ter, o caminho mais curto é a UTM, que sabe criar uma máquina de macOS a partir do instalador em três cliques.

---

## A máquina de QEMU é um script

Uma máquina de QEMU não é um objecto registado em lado nenhum: **é um comando**. Este programa grava-o num script ao lado do disco, e é esse script que se corre a seguir:

```
~/LaboratorioVirtual/Maquinas/<nome>/arrancar-<nome>.sh
```

Guarde-o. Um programa que executasse o comando e o deitasse fora deixava o utilizador sem nada no dia seguinte.

Depois de instalar o sistema, apague a linha do `-cdrom` para a máquina passar a arrancar do disco em vez de voltar ao instalador. O script tem essa nota lá dentro.

Duas opções que não são óbvias e que o script leva:

- **`-accel hvf`** é a aceleração da Apple. Sem ela o QEMU emula.
- **`-cpu host`** passa as capacidades do processador real ao convidado. Num Apple Silicon é obrigatório — sem isso o convidado ARM não arranca.
- **`-bios` com o firmware UEFI**, só em ARM, onde não há BIOS nenhuma. Um convidado ARM sem firmware fica num ecrã preto e não diz porquê.

---

## Onde ficam as coisas

```
~/LaboratorioVirtual/
├── Imagens/      as ISO descarregadas e verificadas
└── Maquinas/     um directório por máquina, com o disco e o script
```

Nada é escrito dentro da pasta do programa. Para outro sítio, `--pasta`.

---

<sub>Created by Redfox using Claude</sub>
