# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [1.3.0] — 2026-09-04

**PT** · O programa passou a reconhecer o que já está instalado, a instalar
sozinho, e a perguntar só o que é mesmo uma decisão.
**EN** · The program now recognises what is already installed, installs by
itself, and asks only what is genuinely a decision.

### Três coisas que estavam mal, e não eram bugs

**Ignorava metade do que estava na máquina.** Quem tem uma VMware Workstation
paga pela empresa, com as máquinas todas lá dentro, era convidado a instalar um
segundo hipervisor — que é a receita conhecida para os dois ficarem lentos.

**Fazia o utilizador acabar a instalação à mão.** Descarregava, verificava, e
depois abria um assistente para ele clicar em «Seguinte» quatro vezes. Clicar
quatro vezes não é uma decisão.

**Perguntava demais e no sítio errado.** Especificações, nome, «criar?» —
quatro paragens, cada uma sem ver as outras, e a decisão de onde guardar cinco
gigabytes de imagem só aparecia depois de os descarregar.

### Reconhece o que já lá está — e sabe usá-lo · Added

| | Detecta | E sabe criar máquinas |
| :--- | :--- | :--- |
| **Windows** | VMware Workstation e Workstation Player | sim |
| **Linux** | VMware Workstation | sim |
| **macOS** | Parallels Desktop **e** VMware Fusion | sim |

Oferecer «quer usar a que já tem?» e depois não saber usá-la seria uma pergunta
a fingir. Por isso o trabalho aqui não foi detectar: foi aprender a conduzir
cada um deles.

**E conduzem-se de maneiras que não se parecem nada.** A Parallels tem o
`prlctl`, uma ferramenta de linha de comandos a sério. A VMware não tem
equivalente: tem o `vmrun`, que liga e desliga mas não cria, e um ficheiro de
texto — o `.vmx` — que descreve a máquina inteira e se escreve à mão. Não há
aqui uma abstracção a partilhar entre as duas, e inventá-la só tornaria as duas
piores.

Escrever um `.vmx` à mão parece frágil e não é: o formato é estável há mais de
vinte anos, e a alternativa — automatizar a interface gráfica — é que seria
frágil.

**A hipótese de instalar outro aparece sempre**, mesmo quando já há um a
funcionar. Quem tem só a VMware pode preferir o Hyper-V para uma máquina em
concreto.

### A instalação é automática · Changed

Deixou de haver assistente para seguir. Em Windows o instalador corre em
silêncio e o progresso aparece no terminal — tempo decorrido e megabytes
escritos, que é verdade, e não uma barra a encher-se sozinha a fingir que sabe
quanto falta.

**E não se acredita no código de saída.** No fim vai-se procurar o `VBoxManage`
onde ele devia ter ficado, porque um instalador que devolve zero sem ter
instalado nada é uma coisa que acontece.

**A única pergunta é onde.** E só onde isso é mesmo uma escolha:

- **Windows** — pergunta-se, porque o `INSTALLDIR` existe e o disco do sistema
  está cheio em muitas máquinas
- **Linux e macOS** — não se pergunta, e não é por esquecimento: quem decide
  onde um pacote fica é a distribuição ou o Homebrew. Inventar uma pergunta cuja
  resposta não muda nada seria pior do que não a fazer, e o programa diz isso

Há um pormenor do instalador da Oracle que valeu um aviso próprio: o
`--msiparams INSTALLDIR=` **não aceita espaços no caminho**. A pasta por omissão
tem espaços e funciona à mesma — porque nesse caso não se lhe passa `INSTALLDIR`
nenhum. Só quando se muda de sítio é que o problema aparece, e o programa avisa
antes em vez de deixar a instalação ir parar ao sítio errado.

### As perguntas passaram a três, e na altura certa · Changed

1. **Onde guardar a imagem** — perguntado ao escolher a imagem, e não no fim.
   Uma imagem anda pelos três a cinco gigabytes, e dizer isto depois de a
   descarregar seria dizer tarde
2. **As especificações e o nome, num ecrã só** — com os motivos por baixo e três
   opções: criar, alterar, cancelar
3. **Nada.** Depois desse ecrã não há mais perguntas

O ecrã de alterar valida cada campo contra **dois** limites ao mesmo tempo: o
que o convidado precisa e o que o anfitrião tem. Nenhum dos dois sozinho chega —
o primeiro deixa criar uma máquina que não cabe, o segundo deixa criar uma que
cabe e não arranca.

**E a ordem mudou:** o descarregamento passou para depois do ecrã das
especificações. Descarregar cinco gigabytes antes de saber se a máquina cabe na
memória do anfitrião é trabalho deitado fora.

### O que continua a não se fazer

- **Instalar o Homebrew.** Instala-se passando um script da Internet
  directamente a um interpretador. Há um teste que falha se isso entrar aqui
- **Instalar em silêncio sem mostrar.** Os comandos aparecem todos antes de
  correrem. Mostrar não é o mesmo que pedir licença: mostra-se, não se pede
- **Escolher pela pessoa.** Quando há uma VMware instalada e ela escolhe
  instalar outro hipervisor à mesma, o programa diz que os dois vão disputar o
  processador — e depois instala

### Testes

110 · 116 · 116 (Windows · Linux · macOS), **342** ao todo, contra 290 na 1.2.0.

Nenhum dos testes novos precisa da VMware, da Parallels ou da Fusion instaladas,
e isso é deliberado: são produtos pagos que nem quem escreveu isto nem os
runners têm. O que se testa é o `.vmx`, que é texto e portanto verificável sem
hipervisor nenhum, e as traduções de vocabulário — que é onde um erro não
rebenta, apenas cria uma máquina com o controlador de disco errado que arranca
devagar sem ninguém perceber porquê.

Há um teste que existe só para impedir uma boa ideia futura: confirma que o
vocabulário da Fusion e o da Parallels **continuam diferentes**. Se alguém um dia
os «simplificar» para um só, falha.

### Corrigido · Fixed

- O arranque de testes de Windows não tinha `Saltar`; o `Vmware.ps1` nasceu sem
  BOM e o PowerShell 5.1 leu-o como ANSI. Os dois são o mesmo erro repetido, e
  os dois já têm quem os apanhe na integração contínua

---

## [1.2.0] — 2026-09-02

**PT** · O programa deixou de dizer o que falta instalar e passou a instalá-lo.
**EN** · The program stopped saying what to install and started installing it.

### O que faltava

Sem hipervisor nenhum, a 1.1.0 dizia «não instalado», dava um endereço, e
ficava-se por aí. Isso é deixar a pessoa a meio: ela queria uma máquina virtual
e ficou com um separador do navegador aberto.

### Novo · Added

- **Opção 5 do menu: preparar um hipervisor.** E o menu de criação também a
  oferece, quando não encontra nenhum, em vez de mandar ler o que está acima
- **Windows** — activa o Hyper-V, ou descarrega e instala o VirtualBox
- **Linux** — instala o KVM com o libvirt, ou acrescenta o repositório da Oracle
  e instala o VirtualBox por ele
- **macOS** — `brew install qemu`, ou descarrega e instala o `.dmg` da Oracle

### As três fazem coisas diferentes, e nenhuma por gosto

**Em Linux não se descarrega binário nenhum.** A versão de Windows tem de ir
buscar um `.exe` à Oracle porque não há alternativa; aqui há, e é melhor sob
todos os pontos de vista. Um ficheiro descarregado à mão verifica-se uma vez, no
dia em que se instala; um pacote de um repositório assinado verifica-se **em
todas as actualizações**, para sempre, pelo gestor de pacotes.

**Num Mac, o QEMU vem do Homebrew** e não há nada a verificar à mão — o Homebrew
já confirma as somas das suas fórmulas. Reescrever isso aqui era substituir uma
coisa que funciona por uma pior.

### A Oracle não assina o manifesto, e o programa não finge que assina

Esta é a parte que interessa. **O `SHA256SUMS` do VirtualBox não é assinado com
GPG** — não há assinatura em claro nem `.asc` na directoria da versão. É um
ficheiro simples, no mesmo servidor de onde vem o instalador. Uma soma obtida
pelo mesmo canal do ficheiro prova que ele chegou inteiro; não prova que veio de
quem diz.

Fingir quatro camadas aqui seria a única mentira deste programa, e no sítio onde
ela custaria mais caro:

```
    [ok]  Domínio da Oracle, verificado a cada salto
    [ok]  HTTPS em todos os saltos
    [--]  Assinatura GPG do manifesto        ← a Oracle não a publica
    [ok]  Soma SHA-256 do ficheiro
    [ok]  Assinatura Authenticode da Oracle  ← esta não vem do mesmo canal
```

**O que salva o caso é diferente em cada sistema, e nenhum dos três podia copiar
o outro:**

- **Windows** — a assinatura **Authenticode** do `.exe`, contra a cadeia de
  certificados do Windows. Não basta estar assinado: o nome no certificado tem
  de ser o da Oracle, porque um instalador validamente assinado por outra
  empresa é exactamente o que um atacante com um certificado legítimo produziria
- **macOS** — a **notarização da Apple** no `.dmg` e o **Developer ID** no
  `.pkg`, contra a cadeia de certificados da Apple
- **Linux** — nem é preciso: a **chave da Oracle é fixada** pela impressão
  digital antes de entrar no sistema, e daí em diante é o gestor de pacotes que
  verifica cada pacote

Nos três, é a mesma ideia: a camada que conta é a que **não** depende do servidor
que forneceu o ficheiro. E nos três é uma condição, não um aviso — o que não
passa é apagado.

### A chave é fixada, e não apenas descarregada

`B9F8D658297AF3EFC18D5CDFA2F683C52980AECF`, publicada pela Oracle na página
`virtualbox.org/wiki/Linux_Downloads`. Acrescentar ao sistema uma chave que se
acabou de ir buscar é uma cerimónia sem conteúdo: se o canal estivesse
comprometido, a chave que chegava era a do atacante e passava a assinar tudo o
que ele quisesse, para sempre.

A linha do repositório leva `signed-by`, para que essa chave só assine os
pacotes desse repositório — sem isso, que é o que o antigo `apt-key` fazia e a
razão por que foi retirado, a chave da Oracle podia assinar pacotes de qualquer
repositório da máquina.

### Nada é fixado que possa envelhecer

A versão sai do `LATEST.TXT` da Oracle; o nome do ficheiro sai do manifesto; o
nome do pacote (`virtualbox-7.2`) sai da série da versão. O número de compilação
— `174877` na 7.2.16 — muda a cada versão, e fixá-lo era garantir que isto
deixava de funcionar dentro de um mês. A própria documentação da Oracle ainda diz
`virtualbox-7.1` numa página onde já se descarrega a 7.2, o que é a demonstração
do problema.

### Duas listas de domínios, outra vez

A lista de onde vem o VirtualBox é **separada** da do catálogo. Juntá-las
alargaria a lista por onde vêm imagens de sistemas operativos para incluir um
sítio que não serve nenhuma — e a do catálogo é curta precisamente para caber
numa auditoria de um minuto. Há um teste, nas três versões, que falha se as duas
se tocarem.

### O que se recusa a fazer

- **Instalar o Homebrew.** Instala-se passando um script da Internet
  directamente a um interpretador, que é o padrão que este programa existe para
  evitar. Há um teste que falha se algum dia entrar aqui um `curl | sh`
- **Instalar em silêncio.** Os comandos aparecem todos **antes** da pergunta;
  perguntar «posso?» e só depois revelar o que se ia fazer não é uma pergunta.
  E o instalador do Windows abre com a interface normal, em vez do modo
  silencioso, porque é ele que avisa que a rede vai abaixo
- **Oferecer o VirtualBox num Mac com chip da Apple.** A Oracle passou a publicar
  uma versão ARM, mas num anfitrião ARM só há aceleração para convidados ARM — e
  quem quer o VirtualBox quer quase sempre um convidado x86, que seria emulado

### Alterado · Changed

- `versao_valida` deixou de escrever mensagens: valida e devolve. Quem chama é
  que sabe falar com o utilizador — e assim testa-se sem arrastar o ponto de
  entrada inteiro para dentro da suite
- O arranque de testes de Windows ganhou o `Saltar` que o de Linux e o de macOS
  já tinham. O cabeçalho do ficheiro prometia que os três arranques tinham «a
  mesma forma», e não tinham

### Corrigido · Fixed

- O README dizia **«não instala hipervisores sozinho»**, que deixou de ser
  verdade com esta versão. Uma linha dessas num ficheiro que ninguém relê é
  como um comentário desactualizado: pior do que não estar lá

### Testes

94 · 99 · 97 (Windows · Linux · macOS), 290 ao todo, contra 230 na 1.1.0.

Nenhum deles instala nada nem liga à rede. O que testam são as decisões tomadas
**antes** de instalar — que versão, que ficheiro, de que domínio, com que
assinatura — que são as que decidem se o que se instala é o da Oracle ou o de
outra pessoa. Há um teste que gera uma chave GPG legítima de outra entidade só
para confirmar que ela é recusada.

Um deles é saltado de propósito e para sempre: «um `.dmg` notarizado pela Apple
em nome da Oracle é aceite». Não se consegue fabricar um para o teste — que é,
precisamente, a razão de essa camada valer alguma coisa.

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

76 · 77 · 77 (Windows · Linux · macOS), 230 ao todo. Os grupos que precisam
mesmo do sistema — o `jq` em Linux, o `stat` do BSD e o `xattr` num Mac — são
saltados com uma explicação numa máquina que não os tenha, e correm no runner
respectivo. Numa máquina de desenvolvimento sem `jq` a contagem baixa para
69 e 62; é por isso que os números aqui são os do runner, e não os do portátil
de quem escreveu isto.

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

- `Windows/` — PowerShell 5.1, Hyper-V e VirtualBox
- `Linux/` — bash, KVM/libvirt e VirtualBox
- `macOS/` — bash **3.2**, QEMU e VirtualBox (só Intel)

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
