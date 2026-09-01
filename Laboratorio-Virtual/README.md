# Laboratório Virtual

**Criação assistida de máquinas virtuais em Windows, Linux e macOS.**
*Assisted virtual machine creation on Windows, Linux and macOS.*

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-informational.svg)](CHANGELOG.md)
[![Sistemas](https://img.shields.io/badge/sistemas-Windows%20%C2%B7%20Linux%20%C2%B7%20macOS-lightgrey.svg)](#instala%C3%A7%C3%A3o--installation)

> **PT** · Escolhe o hipervisor, escolhe o sistema convidado, calcula as especificações a partir do que a máquina tem — e descarrega a imagem do sítio oficial com a verificação toda pelo caminho.
> **EN** · Picks the hypervisor, picks the guest system, works out the specification from what the machine has — and fetches the image from the official site with the whole verification chain along the way.

---

## Índice · Contents

- [As duas coisas que este programa faz melhor](#as-duas-coisas-que-este-programa-faz-melhor)
- [Como a imagem é verificada](#como-a-imagem-é-verificada--how-the-image-is-verified)
- [Trazer uma imagem sua](#trazer-uma-imagem-sua--bringing-your-own-image)
- [Instalação](#instalação--installation)
- [O catálogo](#o-catálogo--the-catalogue)
- [Como as especificações são calculadas](#como-as-especificações-são-calculadas)
- [O que este programa não faz](#o-que-este-programa-não-faz)
- [Estrutura](#estrutura--structure)

---

## As duas coisas que este programa faz melhor

**PT** · Criar uma máquina virtual não é difícil. O que é difícil é criar uma
que não seja um problema daqui a uma semana, a partir de uma imagem que seja
mesmo a que diz ser. É nessas duas coisas que este programa se concentra; no
resto, limita-se a chamar o hipervisor.

| | |
|---|---|
| **Verifica de onde vem a imagem** | Lista fechada de domínios, verificada a cada redireccionamento; assinatura GPG quando o projecto a publica; soma SHA-256 sempre. E diz **quais** das camadas passaram. |
| **Nunca inventa o nome de um ficheiro** | O nome sai do manifesto assinado, e não do catálogo. Um nome fixado ficaria desactualizado à primeira versão menor — e um nome errado é indistinguível de um ataque. |
| **Calcula as especificações e explica a conta** | Não diz "4 GB": diz de onde saíram os 4 GB, quanto ficou para o anfitrião e porquê. Quem sabe a conta sabe quando a mudar. |
| **Protege a máquina anfitriã** | Nunca mais núcleos virtuais do que físicos. Nunca mais memória do que o convidado recomenda. Nunca um disco que deixe o anfitrião sem folga. |
| **Diz o que não pode fazer, e porquê** | O macOS num anfitrião que não é Apple, o VirtualBox num Mac com chip da Apple, o Hyper-V numa edição Home. Recusa e explica, em vez de falhar a meio. |
| **Aceita uma imagem sua** | Uma ISO, um disco já feito ou uma appliance que não estão no catálogo. Sem garantias inventadas: diz o que verificou e o que não. |

---

## Como a imagem é verificada · How the image is verified

**PT** · Esta é a parte que justifica o programa existir, por isso está descrita
por inteiro.

```
  1. O domínio  ──▶  lista fechada, verificada a cada redireccionamento
  2. O TLS      ──▶  HTTPS obrigatório, sem excepções de certificado
  3. A assinatura ▶  GPG do manifesto, com impressão digital fixada quando há
  4. A soma     ──▶  SHA-256, obrigatória, sem opção de a desligar
```

### A ordem importa mais do que as camadas

O manifesto é verificado **antes** de dele se tirar o nome do ficheiro. Se o
nome saísse de um manifesto ainda por verificar, um manifesto adulterado podia
mandar descarregar outra coisa qualquer — e o passo da soma confirmaria
alegremente que essa outra coisa correspondia à soma que o atacante lá pôs.

### A assinatura vale mais do que o nome do servidor

É o que permite usar um espelho sem perder garantias. O Linux Mint não tem
servidor próprio de descarregamento — distribui pela `kernel.org` e por outros
espelhos — e a imagem dele é tão verificável como a do Ubuntu, porque o que
prova a origem é a assinatura do Clement Lefebvre e não o nome da máquina que
serviu o ficheiro.

### O programa nunca afirma mais do que fez

```
  Verificação:
    [ok]  Domínio na lista de confiança
    [ok]  Ligação HTTPS com certificado válido
    [ok]  Assinatura do manifesto
    [--]  Impressão digital fixada
    [ok]  Soma SHA-256 do ficheiro
```

Uma camada que não correu aparece na lista, e não é omitida. Dizer
«verificado» quando só se comparou uma soma obtida pelo mesmo canal do ficheiro
é uma verdade que induz em erro: quem controla o canal controla as duas coisas.

**EN** · Four layers, strongest last, and the order matters more than the
layers: the manifest is verified **before** the filename is read out of it. A
layer that did not run appears in the list rather than being omitted — saying
"verified" when only a same-channel checksum was compared is a misleading truth.

---

## Trazer uma imagem sua · Bringing your own image

**PT** · O catálogo cobre o que é comum. Para o resto — um Proxmox, um TrueNAS,
uma appliance, a ISO que a empresa fornece, ou uma distribuição que já estava no
disco — o programa aceita um ficheiro que já tenha.

**Aqui não há garantias nenhumas, e o programa diz isso em vez de as fingir.**
Uma imagem do catálogo vem de um domínio fixado, com um manifesto assinado.
Uma imagem do seu disco não tem nada disso, e o relatório mostra-o:

```
  Verificação:
    [--]  Domínio na lista de confiança
    [--]  Ligação HTTPS com certificado válido
    [--]  Assinatura do manifesto
    [--]  Impressão digital fixada
    [ok]  Soma SHA-256 do ficheiro
    Esta imagem não veio do catálogo: as quatro primeiras camadas não se
    aplicam a um ficheiro que já estava no disco.
```

O que o programa **pode** fazer, e faz:

| | |
|---|---|
| **Diz de onde o ficheiro veio** | Em Windows lê a Marca da Web e mostra o endereço de onde foi descarregado; em macOS lê a quarentena do Gatekeeper e o `kMDItemWhereFroms`; em Linux o `user.xdg.origin.url`. Um endereço à frente dos olhos, na hora de decidir, é o que faz reparar que não é o sítio oficial. |
| **Verifica a soma, se a tiver** | Cole a que o fornecedor publica. É a única camada que ainda se aplica. |
| **Confirma que o ficheiro é o que parece** | Uma ISO começa por `CD001` no sector 16, um qcow2 por `QFI\xfb`. Não é segurança — quem adultera põe a assinatura certa — mas apanha o engano honesto: o `.zip` por extrair, o descarregamento a meio. |
| **Sabe que uma ISO e um disco não são a mesma coisa** | Ver abaixo. |

### A distinção que decide se a máquina arranca

**Uma ISO é o instalador. Uma imagem de disco é a máquina.**

| Formato | O que o programa faz |
| :--- | :--- |
| `.iso` | Liga como CD e cria um disco vazio ao lado, para o sistema se instalar |
| `.img` `.raw` `.qcow2` `.vdi` `.vmdk` `.vhd` `.vhdx` | **É** o disco. Não cria nada e não liga CD nenhum |
| `.ova` `.ovf` | Não se liga: importa-se. Já traz a máquina toda feita |

Criar um disco vazio ao lado de uma `.qcow2` e arrancar de um CD que não existe
dá exactamente o *no bootable device* que ninguém sabe explicar.

**A imagem é copiada para a pasta da máquina, e não ligada onde está.** Ligar o
original faria a máquina escrever por cima dele: a primeira arrancada estragava
a cópia limpa que descarregou, e a segunda máquina feita a partir da mesma
imagem já nascia com o sistema da primeira lá dentro.

### O que cada hipervisor aceita

| | `.iso` | `.qcow2` | `.vdi` | `.vmdk` | `.vhd/.vhdx` | `.ova` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Hyper-V** | ✓ | — | — | — | ✓ | — |
| **VirtualBox** | ✓ | — | ✓ | ✓ | ✓ (vhd) | ✓ |
| **KVM/QEMU** | ✓ | ✓ | ✓ | ✓ | ✓ | — |

Quando o formato não serve, o programa dá o comando de conversão em vez de dizer
apenas «não é suportado»:

```bash
qemu-img convert -p -O vhdx a-sua-imagem.qcow2 a-sua-imagem.vhdx
```

**EN** · The catalogue covers what is common; for everything else the program
accepts a file you already have. There are no guarantees here and it says so:
the layers report shows four `[--]` and one `[ok]` at best. What it can do is
tell you where the file came from (Mark of the Web on Windows, Gatekeeper
quarantine on macOS, `user.xdg.origin.url` on Linux), verify a checksum you
paste, confirm the content matches the extension, and — crucially — know that
**an ISO is the installer while a disk image is the machine**.

---

## Instalação · Installation

**PT** · Escolha a pasta do seu sistema. Cada uma é um programa completo, com o
seu código, os seus testes e o seu lançador.

| Pasta | Como abrir | Hipervisores |
| :--- | :--- | :--- |
| **[`Windows/`](Windows/LEIA-ME.md)** | Duplo clique em `EXECUTAR.bat` | Hyper-V · VirtualBox |
| **[`Linux/`](Linux/LEIA-ME.md)** | `./executar.sh` | KVM/libvirt · VirtualBox |
| **[`macOS/`](macOS/LEIA-ME.md)** | Duplo clique em `executar.command` | QEMU · VirtualBox (só Intel) |

### O que é preciso ter

| | Windows | Linux | macOS |
| :--- | :--- | :--- | :--- |
| **Obrigatório** | PowerShell 5.1 (vem no sistema) | `bash`, `curl`, `jq`, `coreutils` | `bash` 3.2 (vem no sistema), `jq` |
| **Para verificar assinaturas** | `gpg` — o Git para Windows traz um | `gpg` | `gpg` via Homebrew |
| **Para criar máquinas** | Hyper-V (Pro+) ou VirtualBox | `qemu-kvm` + `libvirt` ou VirtualBox | `qemu` via Homebrew |

Sem `gpg`, o programa corre e verifica a soma — e diz que não verificou a
assinatura. Sem hipervisor, o programa corre e mostra tudo — e diz que não pode
criar máquinas. Nada disto impede o arranque.

```bash
./executar.sh --diagnostico       # Linux
./executar.command --diagnostico  # macOS
EXECUTAR.bat -Diagnostico         # Windows
```

---

## O catálogo · The catalogue

**PT** · O ficheiro `src/catalogo.json` é a fronteira de segurança do programa,
e é o único que se pode editar sem saber programar.

**Dezassete imagens**, filtradas pela arquitectura do anfitrião:

| Família | O que há |
| :--- | :--- |
| **Linux** | Ubuntu 24.04 (Desktop, Server, Server ARM64), Debian (amd64, ARM64), Fedora Workstation, Linux Mint, AlmaLinux 9, Rocky 9, openSUSE Leap, Alpine, Kali |
| **Windows** | Windows 11 Enterprise (avaliação, 90 dias), Windows Server 2025 (avaliação, 180 dias) |
| **macOS** | Instalador da Apple, e só em equipamento Apple |
| **Móveis** | Android x86, e o emulador oficial do Android Studio |

### Duas listas de domínios, e não uma

```json
"dominios_confiaveis": [ 14 domínios ]   ← de onde se descarrega
"dominios_paginas":    [ 13 domínios ]   ← o que se abre no navegador
```

A primeira é curta de propósito, para caber numa auditoria de um minuto. Juntar
as duas triplicaria a lista de descarregamento sem que nenhum dos domínios
acrescentados servisse para descarregar seja o que for — e uma lista que ninguém
consegue rever deixa de proteger.

```bash
./executar.sh --verificar-catalogo
```

Valida o catálogo e imprime cada impressão digital fixada ao lado da página
oficial onde a pode comparar. **Faça-o antes de confiar nelas num ambiente que
interesse:** uma impressão digital fixada é a garantia mais forte que este
programa dá, e vale o que valer a confirmação que lhe fizerem.

---

## Como as especificações são calculadas

**PT** · A regra que orienta tudo: **a máquina anfitriã tem de continuar
utilizável.** Uma máquina virtual que arranca e deixa o portátil a nadar não
resolveu um problema — criou dois.

### Memória

```
reserva     = max(4 GB, 25% do total), até um máximo de metade do total
disponível  = total − reserva
proposta    = o recomendado pelo convidado, nunca mais
```

O tecto existe porque dar 12 GB a um convidado que recomenda 8 não o torna mais
rápido: torna-o num convidado com 4 GB de memória parada que fazem falta ao
anfitrião. Quando há folga, o programa diz quanta — quem souber que precisa de
mais, sabe que a tem.

O limite de metade existe por causa das máquinas pequenas: num anfitrião de
4 GB, uma reserva fixa de 4 GB não deixava nada e o programa recusava-se a criar
até um Alpine, que precisa de 1 GB.

### Processador

```
proposta = min(recomendado pelo convidado, núcleos físicos − 1)
```

**Nunca mais núcleos virtuais do que físicos.** É a confusão mais comum de quem
cria a primeira máquina virtual, e o resultado é o contrário do esperado: com
mais núcleos virtuais do que físicos, o hipervisor tem de esperar que haja
núcleos livres suficientes para agendar a máquina toda de uma vez, e o convidado
fica **mais lento**. Dar quatro núcleos a uma máquina virtual num anfitrião de
quatro núcleos é pior do que dar dois.

E os núcleos físicos não são o que o `nproc` diz: num processador com
*hyper-threading*, o `nproc` conta o dobro.

### Disco

Crescimento dinâmico, e o tamanho é reduzido se a promessa não couber deixando
folga no anfitrião. Um disco dinâmico não ocupa hoje o que promete — mas ocupa
amanhã, e um anfitrião que fica sem espaço com uma máquina virtual a correr
corrompe-a.

---

## O que este programa não faz

**PT** · Vale mais dizer isto à cabeça do que deixar descobrir.

- **Não descarrega Windows nem macOS automaticamente.** A Microsoft exige um
  formulário; a Apple só distribui num Mac. O programa abre a página oficial e,
  quando o ficheiro estiver no disco, verifica-o contra a soma que a página
  publica. Contornar um formulário seria fazer o que um programa não deve.
- **Não virtualiza macOS fora de equipamento Apple.** Não é limitação técnica, é
  a licença. E imagens de macOS oferecidas por terceiros não são legítimas, mesmo
  quando funcionam.
- **Não instala hipervisores sozinho.** Diz o comando — o da distribuição certa —
  e deixa a decisão a quem está a usar. A excepção é o Hyper-V, que se activa
  com uma pergunta explícita, porque não se instala: activa-se.
- **Não cria a máquina de UTM no macOS.** Aponta para ela. Montar um pacote
  `.utm` a partir de um script dá, com facilidade, uma máquina que abre e não
  arranca.
- **Não gere as máquinas depois de criadas.** Não é um painel de administração.
  Cria, e sai da frente.
- **Não converte imagens sozinho.** Quando o formato não serve ao hipervisor,
  dá o comando do `qemu-img` e fica por aí. Converter três gigabytes é uma
  operação que quem a manda fazer deve saber que está a fazer.

---

## Estrutura · Structure

```
├── Windows/              PowerShell · 76 testes
│   ├── EXECUTAR.bat
│   ├── src/              LaboratorioVirtual.ps1 + 6 módulos + catalogo.json
│   └── tests/
├── Linux/                bash · 69 testes
│   ├── executar.sh
│   ├── src/              laboratorio-virtual.sh + lib/ + catalogo.json
│   └── tests/
├── macOS/                bash 3.2 · 69 testes
│   ├── executar.command
│   ├── src/              laboratorio-virtual.sh + lib/ + catalogo.json
│   └── tests/
├── README.md
├── CHANGELOG.md
└── CONTRIBUTING.md
```

E dentro de cada versão, os mesmos seis módulos:

| Módulo | O que faz |
| :--- | :--- |
| `seguranca` | Descarregamento verificado. A fronteira de segurança |
| `catalogo` | Leitura e validação do catálogo |
| `imagem_local` | Imagens que o utilizador traz, e o que se consegue saber sobre elas |
| `hardware` | O que a máquina anfitriã tem |
| `recomendacao` | O cálculo das especificações. Não toca na máquina |
| `hipervisor` | Detecção e criação, por hipervisor |

**PT** · Todo o código está comentado em português europeu e inglês britânico.
Nenhum dos 214 testes toca na rede, cria uma máquina virtual ou instala seja o
que for: as três suites correm em qualquer máquina, e depois cada versão é
verificada no seu runner nativo pela integração contínua. Os poucos grupos que
precisam mesmo do sistema — o `stat` do BSD e o `xattr` num Mac, o `jq` em
Linux — são saltados com uma explicação em vez de falharem, e correm no runner
respectivo.

---

*Created by Redfox using Claude*
