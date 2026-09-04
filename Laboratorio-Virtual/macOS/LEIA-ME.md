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

## A Parallels e a Fusion que já cá estejam

Num Mac, quem virtualiza a sério quase sempre pagou por uma destas: a
**Parallels Desktop**, que é a mais usada, ou a **VMware Fusion**. O programa
reconhece as duas e sabe criar máquinas em ambas. Aparecem na lista dos
hipervisores, em primeiro.

Esta é a maior diferença entre esta versão e as outras duas: em Windows e em
Linux há **um** produto de terceiros a considerar, aqui há dois.

### E conduzem-se de maneiras opostas

A **Parallels** tem o `prlctl`, que é uma ferramenta de linha de comandos a
sério: cria, configura e liga. Escreve-se-lhe o que se quer e ela faz.

A **Fusion** não tem nada disso. Tem o `vmrun`, que liga e desliga mas não cria,
e um ficheiro de texto — o `.vmx` — que descreve a máquina inteira e se escreve à
mão. Parece frágil e não é: o formato é estável há mais de vinte anos, e a
alternativa (automatizar a interface gráfica) é que seria frágil.

Ou seja: para a Parallels chamam-se comandos, para a Fusion escreve-se um
ficheiro. **Não há aqui uma abstracção a partilhar entre as duas**, e tentar
inventá-la só tornaria as duas piores. Há um teste que confirma que os dois
vocabulários continuam diferentes — se alguém um dia os «simplificar» para um
só, falha.

### Dois pormenores de um Mac

Uma máquina de Fusion vive dentro de um pacote `.vmwarevm`, que é uma pasta que
o Finder mostra como um ficheiro só. Criá-la numa pasta simples funciona, mas
deixa ficheiros soltos no Finder — que não é o que quem usa um Mac espera.

E o `vmrun` da Fusion vive dentro do pacote da aplicação, e **não está no
PATH**. Procurar só no PATH dava «não instalada» num Mac onde está.

---

## Instalar um hipervisor

Sem hipervisor não há onde criar a máquina. A opção **5** do menu trata disso —
e o menu de criação também a oferece, quando não encontra nenhum.

### O QEMU vem do Homebrew

`brew install qemu`, e mais nada. Não há nada a verificar à mão: o Homebrew tem
as somas nas suas próprias fórmulas e confirma-as. Reescrever isso aqui era
substituir uma coisa que funciona por uma pior.

**O que este programa não faz é instalar o próprio Homebrew.** A forma de o
instalar é passar um script da Internet directamente a um interpretador —
exactamente o padrão que este programa inteiro existe para evitar. Recusá-lo com
imagens e aceitá-lo aqui não era coerente. Se o Homebrew não estiver cá, diz-se
onde está e porquê.

### O VirtualBox descarrega-se, e a Apple é que o valida

Como em Windows, a Oracle não assina o `SHA256SUMS` com GPG: a soma vem do mesmo
servidor que o ficheiro e só prova que ele chegou inteiro.

```
    [ok]  Domínio da Oracle, verificado a cada salto
    [ok]  HTTPS em todos os saltos
    [--]  Assinatura GPG do manifesto             ← a Oracle não a publica
    [ok]  Soma SHA-256 do ficheiro
    [ok]  Notarização da Apple, com a Oracle no certificado
```

**O que prova a origem é a assinatura da Apple.** O `.dmg` está notarizado e o
`.pkg` lá dentro está assinado com um Developer ID; as duas verificam-se contra
a cadeia de certificados **da Apple**, que não veio da Oracle. É a única camada
que não depende do canal que trouxe o ficheiro, e por isso é uma condição e não
um aviso: não passa, apaga-se.

Não basta estar assinado — o nome no certificado tem de ser o da Oracle.

### Num Mac com chip da Apple, o VirtualBox não aparece

A Oracle passou a publicar uma versão para Apple Silicon. Não é oferecida aqui,
e a razão não é a de haver ou não ficheiro: **num anfitrião ARM só há aceleração
por hardware para convidados ARM**. Quem procura o VirtualBox procura-o quase
sempre para correr um convidado x86 — que teria de ser emulado.

O QEMU emula melhor, e diz que está a emular.

### Depois de instalar

O macOS pode pedir autorização para a extensão de sistema da Oracle, em
**Definições do Sistema › Privacidade e Segurança**. Sem isso o VirtualBox
instala-se e depois recusa-se a arrancar máquinas — e a mensagem que dá não
aponta para ali.

---

## Trazer uma imagem sua

O catálogo cobre o que é comum. Para o resto — um Proxmox, um TrueNAS, uma
appliance, a ISO que a empresa fornece — a opção **1** do menu pergunta se a
imagem vem do catálogo ou se já a tem.

**Aqui não há garantias nenhumas, e o programa diz isso em vez de as fingir.**
O relatório de verificação mostra quatro camadas por aplicar e, quando muito,
a soma:

```
    [--]  Domínio na lista de confiança
    [--]  Assinatura do manifesto
    [ok]  Soma SHA-256 do ficheiro
```

### Uma ISO é o instalador. Uma imagem de disco é a máquina.

| Formato | O que o programa faz |
| :--- | :--- |
| `.iso` | Liga como CD e cria um disco vazio ao lado |
| `.img` `.raw` `.qcow2` `.vdi` `.vmdk` `.vhd` `.vhdx` | **É** o disco. Não cria nada e não liga CD nenhum |
| `.ova` `.ovf` | Importa-se. Já traz a máquina toda feita |

Criar um disco vazio ao lado de uma imagem que já é o disco, e arrancar de um CD
que não existe, dá exactamente o *no bootable device* que ninguém sabe explicar.

**A imagem é copiada para a pasta da máquina**, e não ligada onde está: a
primeira arrancada escreveria por cima da cópia limpa que descarregou.

### O que o macOS sabe sobre a origem — e é bastante

O Gatekeeper põe uma quarentena em tudo o que é descarregado, e o Spotlight
guarda ao lado o endereço de onde veio:

```bash
xattr -p com.apple.metadata:kMDItemWhereFroms a-sua-imagem.iso | xxd -r -p | plutil -p -
```

Não é um texto — é um plist binário, e por isso passa pelo `plutil` para se
conseguir ler. O programa faz isso e mostra o endereço. Sem ele, ainda diz qual
foi a aplicação que trouxe o ficheiro, que é menos mas não é nada.

### Uma nota do `stat`

O `stat` de um Mac é o do BSD e não o do GNU: é `stat -f '%z'` e não
`stat -c '%s'`. É das diferenças que mais depressa parte um script copiado de
Linux, e por isso está escrita aqui e no código.

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
