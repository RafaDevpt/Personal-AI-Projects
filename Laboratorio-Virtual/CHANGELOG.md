# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [1.1.0] — 2026-09-01

**PT** · O programa passou a aceitar imagens que o utilizador já tem, e não só
as do catálogo.
**EN** · The program now accepts images the user already has, not only the
catalogue's.

### O que faltava

A 1.0.0 sabia verificar uma imagem que o utilizador tivesse — mas depois não
fazia nada com ela. Para construir uma máquina, a imagem tinha de estar no
catálogo. Um Proxmox, um TrueNAS, uma appliance, a ISO que a empresa fornece:
nada disso cabia, e são metade dos casos reais.

### Novo · Added

- **Escolher entre o catálogo e uma imagem própria**, logo a seguir a escolher o
  hipervisor. Nas três versões
- **Formatos reconhecidos**: `.iso`, `.img`, `.raw`, `.qcow2`, `.vdi`, `.vmdk`,
  `.vhd`, `.vhdx`, `.ova` e `.ovf`
- **A distinção que decide se a máquina arranca.** Uma ISO é o instalador e
  precisa de um disco vazio ao lado; uma imagem de disco **é** a máquina e não
  leva CD nenhum; uma appliance não se liga, importa-se. Criar um disco vazio ao
  lado de uma `.qcow2` dá o *no bootable device* que ninguém sabe explicar
- **A imagem é copiada para a pasta da máquina**, e não ligada onde está. Ligar
  o original faria a primeira arrancada escrever por cima da cópia limpa que o
  utilizador descarregou — e a segunda máquina feita a partir da mesma imagem já
  nasceria com o sistema da primeira lá dentro
- **Perfis de convidado** para quando o catálogo não sabe os requisitos: Linux
  leve, Linux servidor, Linux com ambiente gráfico, Windows, ou outro
- **O comando de conversão**, quando o formato não serve ao hipervisor. Uma
  mensagem que só diz «não é suportado» deixa a pessoa no mesmo sítio; uma que
  dá o `qemu-img convert` resolve-lhe o problema
- **Confirmação de que o ficheiro é o que parece**: `CD001` no sector 16 de uma
  ISO, `QFI\xfb` num qcow2, e por aí. Não é segurança — quem adultera põe a
  assinatura certa — mas apanha o `.zip` por extrair e o descarregamento a meio,
  que é o caso comum
- **Importação de appliances** `.ova` no VirtualBox

### De onde veio o ficheiro — e aqui cada sistema sabe uma coisa diferente

Esta é a informação mais útil que se consegue dar sobre uma imagem sem
proveniência, e as três versões vão buscá-la a sítios diferentes:

- **Windows** — a Marca da Web, que muitas vezes traz o **endereço** de onde o
  ficheiro foi descarregado. É das poucas coisas em que o Windows dá mais
  informação do que os outros dois
- **macOS** — a quarentena do Gatekeeper e o `kMDItemWhereFroms`, que é um plist
  binário e tem de passar pelo `plutil` para se conseguir ler
- **Linux** — o `user.xdg.origin.url`, a convenção do freedesktop que os
  navegadores respeitam

Nos três, não encontrar a marca **não** quer dizer que o ficheiro seja de
confiança: quer dizer que o sistema não sabe. É a mesma distinção que o resto do
programa faz entre «não encontrei» e «não consegui olhar».

### O que não mudou, e é o mais importante

**A cadeia de verificação continua a valer só para o catálogo, e o programa
continua a dizer a verdade sobre isso.** Uma imagem trazida pelo utilizador
mostra quatro camadas por aplicar e, quando muito, a soma:

```
    [--]  Domínio na lista de confiança
    [--]  Assinatura do manifesto
    [ok]  Soma SHA-256 do ficheiro
```

Fingir o contrário estragaria a única coisa que o resto do programa constrói.

### Testes

76 · 69 · 69 (Windows · Linux · macOS). Os grupos que precisam mesmo do sistema
— o `stat` do BSD e o `xattr` num Mac — são saltados com uma explicação numa
máquina que não seja um Mac, e correm no runner respectivo.

---

## [1.0.0] — 2026-09-01

**PT** · Primeira versão. Três programas independentes que criam máquinas
virtuais a partir de imagens verificadas.
**EN** · First release. Three independent programs that create virtual machines
from verified images.

### O problema que isto resolve

Criar uma máquina virtual não é difícil. O que é difícil são as duas coisas à
volta: garantir que a imagem é mesmo a que diz ser, e escolher especificações
que não deixem o anfitrião inutilizável. É nessas duas que este programa se
concentra; no resto, chama o hipervisor e sai da frente.

### Novo · Added

**A cadeia de verificação**, que é a razão de o projecto existir.

- Lista fechada de domínios de descarregamento, verificada **a cada
  redireccionamento**. Os saltos são seguidos à mão, com `--max-redirs 0` e
  `-MaximumRedirection 0`, porque o comportamento normal do `curl -L` e do
  `Invoke-WebRequest` anula a lista por completo
- HTTPS obrigatório, com `--proto '=https'` para que nem um redireccionamento
  possa descer a HTTP
- Assinatura GPG do manifesto, verificada **antes** de dele se tirar o nome do
  ficheiro. A ordem não é arbitrária: se o nome saísse de um manifesto por
  verificar, um manifesto adulterado podia mandar descarregar outra coisa
  qualquer — e a soma no fim confirmaria alegremente que essa outra coisa
  correspondia ao que o atacante lá pôs
- Impressão digital fixada quando existe, e é uma **condição** e não um aviso:
  uma assinatura válida de uma chave errada é exactamente o que um atacante com
  um catálogo adulterado produziria
- Soma SHA-256 obrigatória, sem opção de a desligar. Um ficheiro que não passe é
  apagado, porque deixá-lo lá é deixar uma armadilha para quem o encontrar
- **O programa diz sempre que camadas correram.** As que não correram aparecem
  na lista com `[--]`. Dizer «verificado» quando só se comparou uma soma obtida
  pelo mesmo canal do ficheiro é uma verdade que induz em erro

**O nome do ficheiro nunca é inventado.** Sai do manifesto assinado. Um nome
fixado no catálogo ficaria desactualizado à primeira versão menor — e um nome
errado é indistinguível de um ataque.

**O catálogo**, com dezassete imagens: onze distribuições de Linux (incluindo
ARM64 para Ubuntu Server e Debian), duas avaliações da Microsoft, o instalador
do macOS e duas entradas de Android. Duas listas de domínios em vez de uma — a
de descarregamento é curta de propósito, para caber numa auditoria de um minuto.

**A recomendação de especificações**, que explica a conta em vez de só dar o
número:

- Nunca mais núcleos virtuais do que físicos. É a confusão mais comum de quem
  cria a primeira máquina virtual, e o resultado é o contrário do esperado
- Nunca mais memória do que o convidado recomenda. Dar 12 GB a quem recomenda 8
  não o torna mais rápido, torna-o num convidado com 4 GB de memória parada
- Reserva para o anfitrião, com um limite de metade do total — sem esse limite,
  um anfitrião de 4 GB ficava sem nada e o programa recusava até um Alpine
- Disco dinâmico, encolhido se a promessa não couber deixando folga

**Três versões independentes:**

- `Windows/` — PowerShell 5.1, Hyper-V e VirtualBox. 56 testes
- `Linux/` — bash, KVM/libvirt e VirtualBox. 53 testes
- `macOS/` — bash **3.2**, QEMU e VirtualBox (só Intel). 53 testes

### O que cada versão sabe que as outras não sabem

- **Windows** — que o WMI reporta as extensões do processador como desligadas
  numa máquina onde o Hyper-V está ligado, porque o Windows já é ele próprio um
  convidado. E que o WSL 2, o Docker Desktop e a Integridade de Memória activam
  o hipervisor sem o dizer, o que torna o VirtualBox lento sem explicação
- **Linux** — que o `nproc` conta fios e não núcleos, e que entrar nos grupos
  `kvm` e `libvirt` não tem efeito na sessão que já está aberta
- **macOS** — que o bash do sistema é o 3.2 e não tem `mapfile`, que não há
  `sha256sum`, e que num Apple Silicon uma imagem x86_64 não corre devagar:
  corre por emulação, dez a vinte vezes mais devagar

### O que este programa recusa fazer

- Descarregar Windows ou macOS contornando o formulário do fabricante. Abre a
  página e verifica o ficheiro depois
- Virtualizar macOS fora de equipamento Apple. Não é limitação técnica, é a
  licença — e imagens de macOS de terceiros não são legítimas, mesmo quando
  funcionam
- Oferecer o VirtualBox num Mac com chip da Apple
- Instalar hipervisores sozinho. Diz o comando, da distribuição certa

### Integração contínua

Matriz de três runners nativos. Uma versão de Linux testada num runner de
Windows não prova nada sobre o que ela faz em Linux — e a de macOS, escrita para
o bash 3.2, só num Mac é que se confirma que o é mesmo.

---

<sub>Created by Redfox using Claude</sub>
