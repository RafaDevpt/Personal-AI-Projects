# Windows

**Laboratório Virtual — arranque em Windows**

Esta pasta é uma versão completa e independente, escrita em PowerShell. Não partilha código com as pastas `Linux/` e `macOS/`: fala com o Hyper-V pelo módulo do PowerShell e com o VirtualBox pelo `VBoxManage`.

---

## Como abrir

Duplo clique em **`EXECUTAR.bat`**.

O lançador usa `-ExecutionPolicy Bypass` **só para aquele processo**. Não altera a política da máquina e não pede elevação para o fazer — há instruções na Internet que ensinam a mudar a política do sistema para correr um script, e isso é uma alteração permanente à configuração de segurança de alguém para resolver um problema temporário.

**Não é pedida elevação à cabeça.** O programa corre sem ela e diz o que não consegue fazer. Só o Hyper-V precisa de administrador, e só na altura de criar a máquina. Pedir elevação sempre, para depois não ser preciso, ensina o utilizador a carregar em «Sim» sem ler.

---

## Os dois hipervisores, e porque não convivem bem

| | Hyper-V | VirtualBox |
| :--- | :--- | :--- |
| **Onde está** | Faz parte do Windows. Activa-se, não se instala | Instala-se como um programa |
| **Edições** | Pro, Enterprise, Education, Server | Todas, Home incluída |
| **Velocidade** | Mais rápido | Mais lento |
| **Facilidade** | Menos amigável | Mais simples, melhor com USB e pastas partilhadas |

**E aqui está o que ninguém avisa a tempo: com o Hyper-V activo, o VirtualBox fica visivelmente mais lento.** O Windows inteiro passa a correr como convidado, e o VirtualBox deixa de falar directamente com o processador — passa a usar a interface do Hyper-V. A versão 7 do VirtualBox melhorou isto, mas não o resolveu.

Pior: **o Hyper-V não se activa só pelo painel de funcionalidades.** O WSL 2, o Docker Desktop, a Sandbox do Windows e a Integridade de Memória activam-no todos por baixo, sem o dizer. Uma máquina com o Docker Desktop instalado já tem o hipervisor a correr, e quem instalar o VirtualBox nessa máquina vai achar que o VirtualBox é lento — quando o que se passa é outra coisa.

O programa detecta essa situação e di-la, em vez de deixar descobrir.

### E a armadilha do lado de lá

Numa máquina com o Hyper-V ligado, o WMI reporta as extensões de virtualização do processador como **desligadas**. Não é um erro: com o Hyper-V activo, o Windows que o utilizador vê já é ele próprio um convidado, e um convidado não vê as extensões do processador. Um programa que leia só aquele campo conclui «esta máquina não suporta virtualização» precisamente na máquina onde a virtualização já está a correr.

---

## Pré-requisitos

| O quê | Como |
| :--- | :--- |
| **Windows** | 10, 11 ou Server 2016+ |
| **PowerShell** | 5.1, que vem no sistema. Não é preciso instalar nada |
| **gpg** *(opcional)* | O Git para Windows traz um. Sem ele fica só a soma |
| **Hyper-V** | Pro ou superior. O programa activa-o, com uma pergunta explícita |
| **VirtualBox** *(alternativa)* | [virtualbox.org](https://www.virtualbox.org/wiki/Downloads) |

A edição Home não tem Hyper-V. Não está desligado: não está lá. Quem tiver Home e quiser virtualizar usa o VirtualBox, e o programa encaminha para lá em vez de mandar procurar uma funcionalidade que a máquina nunca vai ter.

```bat
EXECUTAR.bat -Diagnostico
```

---

## Linha de comandos

```powershell
.\src\LaboratorioVirtual.ps1
.\src\LaboratorioVirtual.ps1 -Diagnostico
.\src\LaboratorioVirtual.ps1 -VerificarCatalogo
.\src\LaboratorioVirtual.ps1 -VerificarFicheiro D:\ISO\Win11.iso -Soma 9ffe...
.\src\LaboratorioVirtual.ps1 -Pasta D:\Laboratorio
```

O `-VerificarFicheiro` sai com código 0 quando a soma confere e 1 quando não confere, o que o torna utilizável num script.

---

## O que a máquina criada leva

- **Rede em NAT**, pelo Comutador Predefinido. Alcança a Internet, não é alcançável a partir da rede local. Um comutador externo poria a máquina de laboratório directamente na rede da empresa, o que raramente é o que se quer e nunca é o que se espera.
- **Memória dinâmica**, com um chão de metade. O convidado devolve ao anfitrião o que não está a usar, e é isso que permite ter duas máquinas de laboratório abertas sem somar a memória das duas.
- **Não arranca sozinha com o Windows.** Quem a quer, abre-a.
- **Arranque Seguro com o modelo certo.** Uma máquina de Geração 2 traz o certificado da Microsoft, e a maioria das distribuições de Linux é assinada por outra autoridade — a `MicrosoftUEFICertificateAuthority`. Sem trocar o modelo, a imagem não arranca e não diz porquê.
- **TPM, nas máquinas de Windows 11.** Pela ordem certa: o protector de chaves antes do `Enable-VMTPM`, porque ao contrário falha.


---

## A VMware que já cá está

Se tiver uma **VMware Workstation** ou uma **Workstation Player** instalada, o
programa reconhece-a e sabe criar máquinas nela. Aparece na lista dos
hipervisores, em primeiro.

Não é cortesia: pôr um segundo hipervisor numa máquina que já tem VMware é a
receita conhecida para os dois ficarem lentos. Quem tem uma quase sempre a tem
por motivo de trabalho, com máquinas lá dentro.

### Como se cria uma máquina na VMware

Não há um `VBoxManage`. Há um ficheiro de texto — o `.vmx` — que descreve a
máquina inteira, e um programa à parte que cria o disco. O `vmrun` liga e
desliga, mas não cria.

Escrever um `.vmx` à mão parece frágil e não é: o formato é estável há mais de
vinte anos, e a alternativa — automatizar a interface gráfica — é que seria
frágil.

**Três campos decidem se a máquina arranca**, e nenhum é óbvio:

- **`guestOS`** não é uma etiqueta: decide o controlador de disco, o relógio e a
  placa de rede. Um Ubuntu criado como `other-64` arranca com metade das
  definições erradas, e a lentidão nunca é associada a este campo
- **o disco tem de existir antes do `.vmx`.** A VMware não o cria a partir dele:
  isso é o `vmware-vdiskmanager`, e a versão gratuita do Player nem sempre o
  traz. Quando falta, o programa diz — em vez de escrever um `.vmx` que aponta
  para um disco que não existe
- **`firmware = "efi"`** faz falta a um Windows 11, ou o instalador recusa-se a
  começar com uma mensagem sobre outra coisa

O caminho do disco vai **relativo**, para a pasta da máquina se poder mover para
outro disco sem partir.

---

## Instalar um hipervisor

Sem hipervisor não há onde criar a máquina. A opção **5** do menu trata disso —
e o menu de criação também a oferece, quando não encontra nenhum.

| | O que acontece |
| :--- | :--- |
| **Hyper-V** | Activa-se a funcionalidade. Não se instala: já cá está, desligada. Precisa de administrador e de reiniciar |
| **VirtualBox** | Descarrega-se da Oracle, verifica-se, e o instalador abre com a interface normal |

### O que a Oracle não faz, e o programa não finge

**A Oracle não assina o `SHA256SUMS` com GPG.** Não há assinatura em claro nem
`.asc` na directoria da versão: o manifesto é um ficheiro simples, no mesmo
servidor de onde vem o instalador. Uma soma obtida pelo mesmo canal do ficheiro
prova que ele chegou inteiro — não prova que veio de quem diz.

```
    [ok]  Domínio da Oracle, verificado a cada salto
    [ok]  HTTPS em todos os saltos
    [--]  Assinatura GPG do manifesto        ← a Oracle não a publica
    [ok]  Soma SHA-256 do ficheiro
    [ok]  Assinatura Authenticode da Oracle  ← esta não vem do mesmo canal
```

**E aqui o Windows tem uma coisa que as outras duas versões não têm.** O
instalador da Oracle está assinado com Authenticode, e essa assinatura verifica-se
contra a cadeia de certificados **do Windows** — que não veio da Oracle. É a
única camada desta cadeia que não depende do servidor que forneceu o ficheiro.

Não basta estar assinado: o nome no certificado tem de ser o da Oracle. Um
instalador validamente assinado por outra empresa é exactamente o que um
atacante com um certificado legítimo produziria. Falha aqui, é apagado.

### O número da versão não está escrito no programa

Sai do `LATEST.TXT` da Oracle, e o nome do ficheiro sai do manifesto — pela
mesma razão que o resto do programa nunca inventa um nome. O número de
compilação (`174877` na 7.2.16) muda a cada versão; fixá-lo aqui era garantir
que isto deixava de funcionar dentro de um mês.

### Durante a instalação a rede cai

Alguns segundos, enquanto o VirtualBox instala a sua placa de rede virtual. Não
é avaria, e o programa avisa antes de começar.

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

### O que o Windows sabe e os outros não

Um ficheiro descarregado traz um fluxo alternativo — a **Marca da Web** — com a
zona de origem e, muitas vezes, com o endereço de onde veio. O programa mostra-o:

```
    Este ficheiro foi descarregado de:
      https://exemplo.qualquer/ubuntu.iso
    Confirme que é o sítio oficial do sistema que quer instalar.
```

É das poucas coisas em que o Windows dá mais informação do que o Linux e o
macOS, e é a mais útil de todas: um endereço à frente dos olhos, na hora de
decidir, é o que faz reparar que não é o sítio oficial.

O fluxo perde-se quando o ficheiro passa por um sistema que não é NTFS — uma pen
em FAT32, por exemplo. **Não encontrar a marca não quer dizer que o ficheiro seja
de confiança; quer dizer que o Windows não sabe.**

### O Hyper-V é o mais estreito dos dois

Só liga `.vhd` e `.vhdx`. Uma `.qcow2` de uma appliance tem de ser convertida
antes, e o programa dá o comando:

```powershell
qemu-img convert -p -O vhdx a-sua-imagem.qcow2 a-sua-imagem.vhdx
```

---

## Onde ficam as coisas

Por omissão, no volume com mais espaço livre — e não no do sistema. Uma máquina virtual de 60 GB no mesmo disco onde o Windows tem 15 GB livres é um problema à espera de acontecer, e quem está a criar a primeira máquina virtual não tem razão nenhuma para saber disso de antemão.

```
<volume>\LaboratorioVirtual\
├── Imagens\      as ISO descarregadas e verificadas
└── Maquinas\     os discos e as definições
```

Nada é escrito dentro da pasta do programa. Para outro sítio, `-Pasta`.

---

<sub>Created by Redfox using Claude</sub>
