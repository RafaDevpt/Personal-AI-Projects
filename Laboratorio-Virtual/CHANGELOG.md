# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

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
