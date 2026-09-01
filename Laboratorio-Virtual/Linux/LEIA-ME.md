# Linux

**Laboratório Virtual — arranque em Linux**

Esta pasta é uma versão completa e independente, escrita em `bash`. Não partilha código com as pastas `Windows/` e `macOS/`: fala com o KVM pelo `virt-install` e com o VirtualBox pelo `VBoxManage`.

---

## Como abrir

```bash
./executar.sh
```

Se o ficheiro não estiver executável — acontece quando o repositório foi copiado por uma máquina Windows:

```bash
chmod +x executar.sh src/laboratorio-virtual.sh
```

**O lançador não instala nada e não pede sudo.** Verifica o que falta, diz o comando de instalação **da distribuição onde está a correr**, e arranca na mesma: o programa corre sem hipervisor nenhum, só não cria máquinas — e ver a lista de imagens e as especificações recomendadas continua a valer a pena antes de instalar seja o que for.

Sobre o sudo: não se pede, e é de propósito. Só a criação da máquina precisa de permissões, e essas resolvem-se com os grupos — que é a forma certa — e não correndo o programa todo como root.

---

## Os dois hipervisores

| | KVM/libvirt | VirtualBox |
| :--- | :--- | :--- |
| **Onde está** | O KVM faz parte do kernel. Instala-se o que está à volta: QEMU e libvirt | Instala-se como um programa |
| **Velocidade** | Muito mais rápido | Mais lento |
| **Facilidade** | Linha de comandos e `virt-manager` | Interface própria, mais simples |

O KVM não se activa nem se instala: ou o processador tem as extensões e o módulo está carregado, ou não. O que se instala é o QEMU, que emula o resto da máquina, e o libvirt, que gere as máquinas e as redes.

---

## As duas permissões, e a que ninguém se lembra

Ter o KVM disponível **não chega**. O `/dev/kvm` pertence ao grupo `kvm`, e o socket do libvirt ao grupo `libvirt`. Um utilizador que não pertença a eles vê o `virt-install` falhar com um erro de permissão a meio — depois de já ter descarregado a imagem toda.

```bash
sudo usermod -aG kvm,libvirt $USER
```

**E depois volte a iniciar sessão.** Entrar num grupo não tem efeito na sessão que já está aberta: a pessoa corre o `usermod`, vê o comando terminar bem, tenta outra vez e falha igual. É a segunda chamada ao helpdesk mais comum deste tipo de coisa, e é evitável — por isso o programa diz as duas coisas na mesma linha.

O programa pergunta por isto antes de descarregar seja o que for.

---

## Pré-requisitos

| O quê | Debian/Ubuntu | Fedora/RHEL | Arch |
| :--- | :--- | :--- | :--- |
| **jq** | `sudo apt install jq` | `sudo dnf install jq` | `sudo pacman -S jq` |
| **gpg** *(opcional)* | `sudo apt install gnupg` | `sudo dnf install gnupg2` | `sudo pacman -S gnupg` |
| **KVM** | `sudo apt install qemu-kvm libvirt-daemon-system virtinst` | `sudo dnf install qemu-kvm libvirt virt-install` | `sudo pacman -S qemu-full libvirt virt-install` |
| **VirtualBox** | `sudo apt install virtualbox` | `sudo dnf install VirtualBox` | `sudo pacman -S virtualbox` |

O `curl` e o `sha256sum` já estão em qualquer distribuição.

```bash
./executar.sh --diagnostico
```

Diz o que está instalado, que permissões faltam, e o comando de instalação da sua distribuição — lido do `/etc/os-release`, `ID_LIKE` incluído, que é o que faz isto funcionar num Linux Mint ou num Pop!_OS sem eles estarem em lista nenhuma.

---

## Linha de comandos

```bash
./executar.sh
./executar.sh --diagnostico
./executar.sh --verificar-catalogo
./executar.sh --verificar ~/Transferencias/x.iso --soma 9ffe...
./executar.sh --pasta /dados/laboratorio
```

O `--verificar` sai com 0 quando a soma confere e 1 quando não confere.

---

## O que a máquina criada leva

- **Rede em NAT**, pela rede `default` do libvirt. Alcança a Internet, não é alcançável da rede local. Para um laboratório é o que se quer: uma máquina de testes com um serviço mal configurado não deve estar exposta ao resto do escritório.
- **Disco `qcow2`**, de crescimento dinâmico e com instantâneos. A diferença de desempenho para o `raw` num laboratório não se nota.
- **`--cpu host-passthrough`**, que passa as capacidades do processador real ao convidado.
- **Sem consola agarrada.** O `virt-install` corre com `--noautoconsole`: sem isso, ficava agarrado até a instalação acabar e o programa parecia bloqueado. Para ver:

```bash
virt-viewer --connect qemu:///system NOME
```

---

## Núcleos físicos não são o que o `nproc` diz

O `nproc` conta fios de execução, e num processador com *hyper-threading* isso é o dobro dos núcleos. Dar oito núcleos virtuais a partir de oito fios de quatro núcleos físicos é dar o dobro do que há, e o convidado fica mais lento — que é exactamente o contrário do que quem escreveu o número queria.

O programa usa o `lscpu -p`, que dá a resposta certa, e só recorre ao `nproc` quando ele não existe.

---

## Onde ficam as coisas

```
~/LaboratorioVirtual/
├── Imagens/      as ISO descarregadas e verificadas
└── Maquinas/     os discos qcow2
```

Nada é escrito dentro da pasta do programa. Para outro sítio, `--pasta`.

---

<sub>Created by Redfox using Claude</sub>
