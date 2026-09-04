#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Testes do Laboratorio Virtual, versao de macOS.
#
#        Nenhum teste toca na rede, cria uma maquina virtual ou instala seja o
#        que for. Nao e limitacao: e o desenho. O que interessa provar aqui e o
#        que decide -- se um dominio passa, se um manifesto e lido como deve, se
#        a recomendacao faz a conta certa -- e nada disso precisa de um
#        hipervisor a responder.
#
#        O que fica de fora, e fica assumidamente, e a criacao da maquina em si.
#        Essa so se testa contra um hipervisor a serio, e um teste que precise
#        de um hipervisor nao corre na integracao continua e por isso nao corre
#        nunca.
#
# EN-UK: Virtual Lab tests, macOS version. No test touches the network, creates
#        a virtual machine or installs anything. What is left out, avowedly, is
#        creating the machine itself: that can only be tested against a real
#        hypervisor, and a test needing one does not run in CI and therefore
#        never runs.
#
# Created by Redfox using Claude
# ===========================================================================

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FONTE="$(cd "${RAIZ}/../src" && pwd)"

# PT-PT: As funcoes de aviso que as bibliotecas usam. Nos testes vao para o
#        nada: uma biblioteca que escreve no stderr durante um teste enche o
#        relatorio de ruido que nao e falha nenhuma.
# EN-UK: The reporting functions the libraries use. In tests they go nowhere.
erro()  { printf '%s\n' "$1" >&2; }
aviso() { printf '%s\n' "$1" >&2; }
nota()  { :; }
ok()    { :; }
passo() { :; }

# shellcheck source=arranque.sh
. "${RAIZ}/arranque.sh"
# shellcheck source=../src/lib/seguranca.sh
. "${FONTE}/lib/seguranca.sh"
# shellcheck source=../src/lib/recomendacao.sh
. "${FONTE}/lib/recomendacao.sh"
# shellcheck source=../src/lib/hardware.sh
. "${FONTE}/lib/hardware.sh"
# shellcheck source=../src/lib/hipervisor.sh
. "${FONTE}/lib/hipervisor.sh"
# shellcheck source=../src/lib/catalogo.sh
. "${FONTE}/lib/catalogo.sh"
# shellcheck source=../src/lib/imagem_local.sh
. "${FONTE}/lib/imagem_local.sh"
# shellcheck source=../src/lib/terceiros.sh
. "${FONTE}/lib/terceiros.sh"
# shellcheck source=../src/lib/instalacao.sh
. "${FONTE}/lib/instalacao.sh"

CATALOGO="${FONTE}/catalogo.json"
SOMA_EXEMPLO='9f2f1cbd3ef1a0d4a49a63b3e9b3d9f0c1a2b3c4d5e6f708192a3b4c5d6e7f80'
DOMINIOS=(releases.ubuntu.com cdimage.debian.org)

printf '\n  Laboratório Virtual · testes da versão de macOS\n'
printf '  bash %s\n' "${BASH_VERSION}"


# ===========================================================================
grupo 'Lista de domínios'
# ===========================================================================

t_aceita_https()      { dominio_confiavel 'https://releases.ubuntu.com/24.04/' "${DOMINIOS[@]}"; }
t_recusa_http()       { ! dominio_confiavel 'http://releases.ubuntu.com/24.04/' "${DOMINIOS[@]}"; }
# PT-PT: O truque classico. Se a comparacao fosse por prefixo, isto passava.
t_recusa_prefixo()    { ! dominio_confiavel 'https://releases.ubuntu.com.exemplo.net/x' "${DOMINIOS[@]}"; }
t_recusa_sufixo()     { ! dominio_confiavel 'https://mau-releases.ubuntu.com.br/x' "${DOMINIOS[@]}"; }
# PT-PT: `https://bom.com@mau.net/` vai para o mau.net, e um leitor humano
#        distraido le o principio da linha e assume o contrario.
t_recusa_userinfo()   { ! dominio_confiavel 'https://releases.ubuntu.com@exemplo.net/x' "${DOMINIOS[@]}"; }
t_recusa_vazio()      { ! dominio_confiavel '' "${DOMINIOS[@]}"; }
t_recusa_lixo()       { ! dominio_confiavel 'nem por sombras' "${DOMINIOS[@]}"; }
t_ignora_porta()      { dominio_confiavel 'https://releases.ubuntu.com:443/24.04/' "${DOMINIOS[@]}"; }
t_ignora_maiusculas() { dominio_confiavel 'https://RELEASES.UBUNTU.COM/24.04/' "${DOMINIOS[@]}"; }

teste 'aceita um endereço HTTPS de um domínio da lista' t_aceita_https
teste 'recusa HTTP mesmo num domínio da lista' t_recusa_http
teste 'recusa um domínio que apenas começa por um da lista' t_recusa_prefixo
teste 'recusa um domínio que apenas termina num da lista' t_recusa_sufixo
teste 'recusa um endereço com o domínio na parte do utilizador' t_recusa_userinfo
teste 'recusa um endereço vazio' t_recusa_vazio
teste 'recusa texto que não é um endereço' t_recusa_lixo
teste 'ignora a porta ao comparar o domínio' t_ignora_porta
teste 'compara o domínio sem distinguir maiúsculas' t_ignora_maiusculas


# ===========================================================================
grupo 'Leitura do manifesto de somas'
# ===========================================================================

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

printf '%s *ubuntu-24.04.3-desktop-amd64.iso\n' "$SOMA_EXEMPLO" > "${TMP}/gnu"
printf 'SHA256 (Fedora-Workstation-Live-41-1.4.x86_64.iso) = %s\n' "$SOMA_EXEMPLO" > "${TMP}/bsd"
cat > "${TMP}/assinado" <<EOF
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

# Fedora-Workstation-Live-41-1.4.x86_64.iso: 2147483648 bytes
SHA256 (Fedora-Workstation-Live-41-1.4.x86_64.iso) = ${SOMA_EXEMPLO}
-----BEGIN PGP SIGNATURE-----
iQIzBAEBCAAdFiEE...
-----END PGP SIGNATURE-----
EOF
{
  printf '%s *ubuntu-24.04.3-live-server-amd64.iso\n' "$SOMA_EXEMPLO"
  printf '1111111111111111111111111111111111111111111111111111111111111111 *ubuntu-24.04.3-desktop-amd64.iso\n'
} > "${TMP}/varias"
printf '%s  ./iso/debian-13.0.0-amd64-netinst.iso\n' "$SOMA_EXEMPLO" > "${TMP}/caminho"
printf 'da39a3ee5e6b4b0d3255bfef95601890afd80709 *ubuntu.iso\n' > "${TMP}/sha1"
: > "${TMP}/vazio"

t_gnu() {
    afirmar_igual "${SOMA_EXEMPLO} ubuntu-24.04.3-desktop-amd64.iso" \
        "$(ler_manifesto "${TMP}/gnu" 'ubuntu-[0-9.]+-desktop-amd64\.iso$')"
}
t_bsd() {
    afirmar_igual "${SOMA_EXEMPLO} Fedora-Workstation-Live-41-1.4.x86_64.iso" \
        "$(ler_manifesto "${TMP}/bsd" 'Fedora-Workstation-Live-.*x86_64.*\.iso$')"
}
# PT-PT: A Fedora assina o manifesto por dentro. As marcas do PGP nao sao linhas
#        de soma, e um leitor que rebentasse nelas nao servia.
t_assinado() {
    afirmar_contem "$(ler_manifesto "${TMP}/assinado" 'Fedora-Workstation-Live-.*\.iso$')" "$SOMA_EXEMPLO"
}
t_varias() {
    afirmar_igual '1111111111111111111111111111111111111111111111111111111111111111 ubuntu-24.04.3-desktop-amd64.iso' \
        "$(ler_manifesto "${TMP}/varias" 'ubuntu-[0-9.]+-desktop-amd64\.iso$')"
}
t_caminho() {
    afirmar_contem "$(ler_manifesto "${TMP}/caminho" 'debian-.*-netinst\.iso$')" 'debian-13.0.0-amd64-netinst.iso'
}
t_sem_correspondencia() { ! ler_manifesto "${TMP}/gnu" 'coisa-nenhuma\.iso$' >/dev/null; }
# PT-PT: Um manifesto de SHA-1 nao deve passar por um de SHA-256.
t_sha1_recusado()       { ! ler_manifesto "${TMP}/sha1" 'ubuntu\.iso$' >/dev/null; }
t_vazio()               { ! ler_manifesto "${TMP}/vazio" '.*' >/dev/null; }

teste 'lê o formato do sha256sum do GNU' t_gnu
teste 'lê o formato BSD, que a Fedora e a Rocky usam' t_bsd
teste 'atravessa um manifesto assinado em claro' t_assinado
teste 'escolhe a linha certa entre várias' t_varias
teste 'fica só com o nome quando o manifesto traz o caminho' t_caminho
teste 'não devolve nada quando o padrão não corresponde' t_sem_correspondencia
teste 'ignora uma soma que não tem 64 dígitos' t_sha1_recusado
teste 'aguenta um manifesto vazio' t_vazio


# ===========================================================================
grupo 'Soma de um ficheiro'
# ===========================================================================

printf 'laboratorio virtual' > "${TMP}/ficheiro"
# PT-PT: `shasum -a 256`, e nao `sha256sum`: num Mac o segundo nao existe.
# EN-UK: `shasum -a 256`, not `sha256sum`: a Mac does not have the latter.
SOMA_REAL="$(shasum -a 256 "${TMP}/ficheiro" | cut -d' ' -f1)"

t_soma_certa()      { soma_confere "${TMP}/ficheiro" "$SOMA_REAL"; }
t_soma_maiusculas() { soma_confere "${TMP}/ficheiro" "$(printf '%s' "$SOMA_REAL" | tr '[:lower:]' '[:upper:]')"; }
t_soma_errada()     { ! soma_confere "${TMP}/ficheiro" "$SOMA_EXEMPLO"; }
# PT-PT: O caso que uma comparacao distraida deixava passar.
t_soma_vazia()      { ! soma_confere "${TMP}/ficheiro" ''; }
t_sem_ficheiro()    { ! soma_confere "${TMP}/nao-existe" "$SOMA_REAL"; }

teste 'confirma uma soma correcta' t_soma_certa
teste 'ignora maiúsculas e minúsculas na soma' t_soma_maiusculas
teste 'recusa uma soma errada' t_soma_errada
teste 'recusa uma soma vazia' t_soma_vazia
teste 'recusa um ficheiro que não existe' t_sem_ficheiro


# ===========================================================================
grupo 'Recomendação de especificações'
# ===========================================================================

# PT-PT: Ubuntu Desktop: min 2/4096/25600, rec 2/8192/40960.
UBUNTU_MIN=(2 4096 25600); UBUNTU_REC=(2 8192 40960)
ALPINE_MIN=(1 1024 2048);  ALPINE_REC=(1 2048 8192)

rec_ubuntu() { recomendar "$1" "$2" "$3" "${UBUNTU_MIN[@]}" "${UBUNTU_REC[@]}"; }
rec_alpine() { recomendar "$1" "$2" "$3" "${ALPINE_MIN[@]}" "${ALPINE_REC[@]}"; }

t_nunca_mais_nucleos() {
    local s; s="$(recomendar 2 16384 204800 1 2048 10240 8 4096 20480)"
    local cpu; cpu="$(valor_de cpu "$s")"
    (( cpu <= 2 )) || { printf 'deu %s núcleos num anfitrião de 2\n' "$cpu"; return 1; }
}
t_deixa_um_nucleo() {
    local s; s="$(recomendar 4 16384 204800 1 2048 10240 8 4096 20480)"
    afirmar_igual '3' "$(valor_de cpu "$s")"
}
# PT-PT: 64 GB no anfitriao nao fazem um Ubuntu correr melhor com 24.
t_tecto_memoria() {
    local s; s="$(rec_ubuntu 16 65536 921600)"
    afirmar_igual '8192' "$(valor_de ram_mb "$s")"
}
t_reserva_anfitriao() {
    local s; s="$(rec_ubuntu 8 16384 307200)"
    local ram; ram="$(valor_de ram_mb "$s")"
    (( ram <= 12288 )) || { printf 'deixou menos de 4 GB para o anfitrião\n'; return 1; }
}
t_baixa_e_avisa() {
    local s; s="$(rec_ubuntu 4 8192 204800)"
    [[ "$(valor_de viavel "$s")" == 'sim' ]] || { printf 'recusou\n'; return 1; }
    local ram; ram="$(valor_de ram_mb "$s")"
    (( ram < 8192 )) || { printf 'não baixou: %s\n' "$ram"; return 1; }
    printf '%s\n' "$s" | grep -q '^aviso=' || { printf 'baixou sem avisar\n'; return 1; }
}
# PT-PT: O caso que a reserva fixa de 4 GB estragava: um anfitriao de 4 GB
#        ficava sem nada e o programa recusava ate um Alpine de 1 GB.
t_maquina_pequena() {
    local s; s="$(rec_alpine 2 4096 61440)"
    [[ "$(valor_de viavel "$s")" == 'sim' ]] || { printf 'recusou um Alpine num anfitrião de 4 GB\n'; return 1; }
    afirmar_igual '2048' "$(valor_de ram_mb "$s")"
}
t_sem_memoria() {
    local s; s="$(rec_ubuntu 2 2048 204800)"
    afirmar_igual 'nao' "$(valor_de viavel "$s")"
}
t_sem_disco() {
    local s; s="$(rec_ubuntu 8 32768 10240)"
    afirmar_igual 'nao' "$(valor_de viavel "$s")"
}
t_encolhe_disco() {
    local s; s="$(rec_ubuntu 8 32768 51200)"
    [[ "$(valor_de viavel "$s")" == 'sim' ]] || { printf 'recusou\n'; return 1; }
    local disco; disco="$(valor_de disco_mb "$s")"
    (( disco < 40960 )) || { printf 'manteve %s MB com só 50 GB livres\n' "$disco"; return 1; }
}
# PT-PT: Um numero sem explicacao nao ensina ninguem a mexer nele depois.
t_explica() {
    local s; s="$(rec_ubuntu 8 16384 307200)"
    local quantos; quantos="$(printf '%s\n' "$s" | grep -c '^motivo=')"
    (( quantos >= 3 )) || { printf 'só explicou %s passos\n' "$quantos"; return 1; }
}
t_ram_multiplo() {
    # PT-PT: Um valor redondo e mais facil de reconhecer um mes depois.
    local s; s="$(rec_ubuntu 4 8192 204800)"
    local ram; ram="$(valor_de ram_mb "$s")"
    (( ram % 256 == 0 )) || { printf 'ram=%s não é múltiplo de 256\n' "$ram"; return 1; }
}

teste 'nunca dá mais núcleos virtuais do que físicos' t_nunca_mais_nucleos
teste 'deixa um núcleo para o anfitrião' t_deixa_um_nucleo
teste 'não dá mais memória do que o recomendado, por muita que haja' t_tecto_memoria
teste 'reserva memória para o anfitrião' t_reserva_anfitriao
teste 'baixa do recomendado quando não há, e avisa' t_baixa_e_avisa
teste 'uma máquina pequena ainda corre um convidado pequeno' t_maquina_pequena
teste 'recusa quando não há memória para o mínimo' t_sem_memoria
teste 'recusa quando não há disco para o mínimo' t_sem_disco
teste 'encolhe o disco para deixar folga no anfitrião' t_encolhe_disco
teste 'explica sempre como chegou aos números' t_explica
teste 'arredonda a memória a um múltiplo de 256 MB' t_ram_multiplo


# ===========================================================================
grupo 'QEMU e arquitectura'
# ===========================================================================

t_binario_arm()   { afirmar_igual 'qemu-system-aarch64' "$(binario_qemu 'arm64')"; }
t_binario_intel() { afirmar_igual 'qemu-system-x86_64' "$(binario_qemu 'x86_64')"; }
# PT-PT: Sao dois programas diferentes e nao duas opcoes do mesmo. Chamar o
#        errado da um erro que nao diz qual foi o erro.
t_binario_novo()  { afirmar_igual 'qemu-system-x86_64' "$(binario_qemu 'coisa')"; }

# PT-PT: Num Apple Silicon, o QEMU acelerado so corre convidados ARM. Uma imagem
#        de x86_64 corre por emulacao pura -- dez a vinte vezes mais devagar.
#        Este e o calculo que decide se o utilizador e avisado antes de
#        descarregar tres gigabytes.
t_acelera_igual()    { acelera 'arm64' 'arm64'; }
t_acelera_intel()    { acelera 'x86_64' 'x86_64'; }
t_emula_cruzado()    { ! acelera 'arm64' 'x86_64'; }
t_emula_ao_contrario() { ! acelera 'x86_64' 'arm64'; }

t_aviso_emulacao() {
    local a; a="$(aviso_emulacao 'arm64' 'x86_64')"
    afirmar_contem "$a" 'devagar'
}

t_vbox_ubuntu()   { afirmar_igual 'Ubuntu_64' "$(tipo_virtualbox 'ubuntu-24.04-desktop' 'linux')"; }
t_vbox_mint()     { afirmar_igual 'Ubuntu_64' "$(tipo_virtualbox 'linuxmint-cinnamon' 'linux')"; }
t_vbox_rocky()    { afirmar_igual 'RedHat_64' "$(tipo_virtualbox 'rocky-9' 'linux')"; }
t_vbox_novo()     { afirmar_igual 'Linux_64' "$(tipo_virtualbox 'coisa-nova' 'linux')"; }

teste 'o binário do QEMU muda com a arquitectura do convidado' t_binario_arm
teste 'e o de Intel é outro programa' t_binario_intel
teste 'uma arquitectura desconhecida cai no de Intel' t_binario_novo
teste 'acelera quando anfitrião e convidado são da mesma arquitectura' t_acelera_igual
teste 'acelera também em Intel' t_acelera_intel
teste 'não acelera um convidado x86_64 num Mac ARM' t_emula_cruzado
teste 'nem um convidado ARM num Mac Intel' t_emula_ao_contrario
teste 'o aviso da emulação diz que vai ficar lento' t_aviso_emulacao
teste 'reconhece as distribuições no VirtualBox' t_vbox_ubuntu
teste 'o Mint é um Ubuntu para o VirtualBox' t_vbox_mint
teste 'o Rocky é um RedHat para o VirtualBox' t_vbox_rocky
teste 'uma distribuição desconhecida ainda dá um tipo utilizável' t_vbox_novo


# ===========================================================================
grupo 'Validação do catálogo'
# ===========================================================================

if ! command -v jq >/dev/null 2>&1; then
    saltar 'validação do catálogo' 'o jq não está instalado nesta máquina; na integração contínua está'
else
    t_catalogo_valido()   { afirmar_vazio "$(validar_catalogo "$CATALOGO")"; }
    t_catalogo_imagens()  { local n; n="$(jq '.imagens | length' "$CATALOGO")"; (( n > 0 )); }

    t_iso_verificavel() {
        # PT-PT: Sem manifesto nao ha verificacao, e este programa nao descarrega
        #        o que nao consegue verificar. O teste existe para essa regra nao
        #        se perder na proxima entrada que alguem acrescentar com pressa.
        local em_falta
        em_falta="$(jq -r '.imagens[] | select(.tipo == "iso") | select((.manifesto // "") == "" or (.padrao_ficheiro // "") == "") | .id' "$CATALOGO")"
        afirmar_vazio "$em_falta"
    }

    t_dominios_curtos() {
        local fora
        fora="$(jq -r '. as $c | .imagens[] | select((.directorio // "") != "") |
                       select(($c.dominios_confiaveis | index(.directorio | sub("^https://"; "") | sub("/.*$"; ""))) | not) | .id' "$CATALOGO")"
        afirmar_vazio "$fora"
    }

    # PT-PT: O ataque que esta validacao existe para travar: alguem edita o
    #        catalogo e troca um endereco por outro parecido.
    t_recusa_dominio_fora() {
        local falso="${TMP}/falso.json"
        cat > "$falso" <<'JSON'
{ "versao_esquema": 1, "dominios_confiaveis": ["releases.ubuntu.com"], "dominios_paginas": ["ubuntu.com"],
  "imagens": [ { "id": "falso", "nome": "Falso", "familia": "linux", "arquitectura": "x86_64", "tipo": "iso",
    "pagina_oficial": "https://ubuntu.com/x", "directorio": "https://releases-ubuntu.com.mau.net/",
    "manifesto": "SHA256SUMS", "padrao_ficheiro": "x\\.iso$",
    "minimo": {"cpu":1,"ram_gb":1,"disco_gb":1}, "recomendado": {"cpu":1,"ram_gb":1,"disco_gb":1} } ] }
JSON
        afirmar_diferente '' "$(validar_catalogo "$falso")"
    }

    t_recusa_http() {
        local falso="${TMP}/http.json"
        cat > "$falso" <<'JSON'
{ "versao_esquema": 1, "dominios_confiaveis": ["releases.ubuntu.com"], "dominios_paginas": ["ubuntu.com"],
  "imagens": [ { "id": "falso", "nome": "Falso", "familia": "linux", "arquitectura": "x86_64", "tipo": "iso",
    "pagina_oficial": "https://ubuntu.com/x", "directorio": "http://releases.ubuntu.com/",
    "manifesto": "SHA256SUMS", "padrao_ficheiro": "x\\.iso$",
    "minimo": {"cpu":1,"ram_gb":1,"disco_gb":1}, "recomendado": {"cpu":1,"ram_gb":1,"disco_gb":1} } ] }
JSON
        afirmar_diferente '' "$(validar_catalogo "$falso")"
    }

    t_recusa_impressao_falsa() {
        local falso="${TMP}/chave.json"
        cat > "$falso" <<'JSON'
{ "versao_esquema": 1, "dominios_confiaveis": ["releases.ubuntu.com"], "dominios_paginas": ["ubuntu.com"],
  "imagens": [ { "id": "falso", "nome": "Falso", "familia": "linux", "arquitectura": "x86_64", "tipo": "iso",
    "pagina_oficial": "https://ubuntu.com/x", "directorio": "https://releases.ubuntu.com/",
    "manifesto": "SHA256SUMS", "padrao_ficheiro": "x\\.iso$", "chave_gpg": "a-minha-chave",
    "minimo": {"cpu":1,"ram_gb":1,"disco_gb":1}, "recomendado": {"cpu":1,"ram_gb":1,"disco_gb":1} } ] }
JSON
        afirmar_diferente '' "$(validar_catalogo "$falso")"
    }

    # PT-PT: Uma imagem de x86_64 num anfitriao ARM nao arranca devagar: nao
    #        arranca. Mostra-la seria oferecer um ecra preto.
    t_filtra_arquitectura() {
        local erradas
        erradas="$(imagens_compativeis "$CATALOGO" 'arm64' | cut -f1 | while IFS= read -r id; do
            local a; a="$(campo_imagem "$CATALOGO" "$id" '.arquitectura')"
            [[ "$a" != 'arm64' && "$a" != 'qualquer' ]] && printf '%s ' "$id"
        done)"
        afirmar_vazio "$erradas"
    }

    teste 'o catálogo que vem no projecto passa na validação' t_catalogo_valido
    teste 'o catálogo tem imagens' t_catalogo_imagens
    teste 'todas as imagens descarregáveis têm manifesto e padrão' t_iso_verificavel
    teste 'todos os directórios de descarregamento estão na lista curta' t_dominios_curtos
    teste 'recusa um catálogo com um endereço fora da lista' t_recusa_dominio_fora
    teste 'recusa um catálogo com um endereço em HTTP' t_recusa_http
    teste 'recusa uma impressão digital que não é uma impressão digital' t_recusa_impressao_falsa
    teste 'filtra as imagens pela arquitectura do anfitrião' t_filtra_arquitectura
fi


# ===========================================================================
grupo 'Imagens que o utilizador já tem'
# ===========================================================================

t_iso_instalador()  { afirmar_igual 'instalador' "$(tipo_de_imagem 'ubuntu.iso')"; }
# PT-PT: E a distincao que decide entre uma maquina que arranca e um ecra a
#        dizer que nao ha nada para arrancar. Uma .qcow2 **e** a maquina.
t_disco_nao_e_iso() {
    local f
    for f in a.qcow2 a.vdi a.vmdk a.vhd a.vhdx a.img a.raw; do
        afirmar_igual 'disco' "$(tipo_de_imagem "$f")" "$f" || return 1
    done
}
t_apliancia()       { afirmar_igual 'apliancia' "$(tipo_de_imagem 'a.ova')"; }
t_maiusculas()      { afirmar_igual 'instalador' "$(tipo_de_imagem 'UBUNTU.ISO')"; }
t_desconhecido()    {
    afirmar_igual 'desconhecido' "$(tipo_de_imagem 'a.zip')" || return 1
    afirmar_igual 'desconhecido' "$(tipo_de_imagem 'sem-extensao')"
}
t_extensao()        {
    afirmar_igual '.iso' "$(extensao_de 'X.ISO')" || return 1
    afirmar_vazio "$(extensao_de 'sem-ponto')"
}

# PT-PT: O QEMU e o mais largo dos dois: fala praticamente todos os formatos de
#        disco que existem, porque foi ele que inventou metade deles.
t_qemu_qcow()       { formato_suportado '.qcow2' 'qemu' >/dev/null; }
t_qemu_vmdk()       { formato_suportado '.vmdk' 'qemu' >/dev/null; }
t_qemu_sem_ova()    { ! formato_suportado '.ova' 'qemu' >/dev/null; }
t_vbox_vdi()        { formato_suportado '.vdi' 'virtualbox' >/dev/null; }
t_vbox_ova()        { formato_suportado '.ova' 'virtualbox' >/dev/null; }
t_vbox_sem_qcow()   { ! formato_suportado '.qcow2' 'virtualbox' >/dev/null; }

# PT-PT: Uma mensagem que so diz "nao e suportado" deixa a pessoa no mesmo
#        sitio. Uma que diz o comando resolve-lhe o problema.
t_diz_como_converter() {
    local s; s="$(formato_suportado '.qcow2' 'virtualbox' || true)"
    afirmar_contem "$s" 'qemu-img convert' || return 1
    afirmar_contem "$s" 'vdi'
}
t_ova_no_qemu_explica() {
    local s; s="$(formato_suportado '.ova' 'qemu' || true)"
    afirmar_contem "$s" 'VirtualBox'
}
t_extensao_estranha() {
    local s; s="$(formato_suportado '.zip' 'qemu' || true)"
    afirmar_contem "$s" '.iso'
}

t_perfis_completos() {
    local c cpu ram disco rcpu rram rdisco
    while IFS= read -r c; do
        [[ -z "$c" ]] && continue
        read -r cpu ram disco rcpu rram rdisco <<< "$(perfil_generico "$c")"
        (( ram > 0 )) || { printf '%s sem memória\n' "$c"; return 1; }
        (( rram >= ram )) || { printf '%s recomenda menos do que o mínimo\n' "$c"; return 1; }
        [[ -n "$(nome_perfil "$c")" ]] || { printf '%s sem nome\n' "$c"; return 1; }
    done < <(chaves_perfil)
}
t_perfil_desconhecido() { afirmar_igual "$(perfil_generico 'outro')" "$(perfil_generico 'inventado')"; }

teste 'uma ISO é um instalador' t_iso_instalador
teste 'um disco já feito não é um instalador' t_disco_nao_e_iso
teste 'uma appliance importa-se, não se cria' t_apliancia
teste 'a extensão é comparada sem distinguir maiúsculas' t_maiusculas
teste 'um formato desconhecido é desconhecido' t_desconhecido
teste 'a extensão sai com o ponto e em minúsculas' t_extensao
teste 'o QEMU fala qcow2' t_qemu_qcow
teste 'o QEMU fala vmdk' t_qemu_vmdk
teste 'o QEMU não importa appliances' t_qemu_sem_ova
teste 'o VirtualBox fala vdi' t_vbox_vdi
teste 'o VirtualBox importa appliances' t_vbox_ova
teste 'o VirtualBox não lê qcow2 de forma fiável' t_vbox_sem_qcow
teste 'quando o formato não serve, diz-se como converter' t_diz_como_converter
teste 'uma appliance no QEMU explica para onde ir' t_ova_no_qemu_explica
teste 'uma extensão que não se conhece dá a lista das que se conhecem' t_extensao_estranha
teste 'há um perfil para cada tipo de convidado' t_perfis_completos
teste 'um perfil que não existe cai no genérico' t_perfil_desconhecido


# ===========================================================================
grupo 'Assinatura do conteúdo de um ficheiro'
# ===========================================================================

# PT-PT: Este grupo precisa do `stat` do BSD e do `xattr`, que so existem num
#        Mac. Numa maquina de desenvolvimento que nao seja um Mac, salta-se e
#        diz-se porque -- um teste saltado em silencio e pior do que nenhum,
#        porque da a impressao de cobertura que nao houve. Na integracao
#        continua corre num Mac a serio, que e onde interessa.
# EN-UK: This group needs BSD `stat` and `xattr`, which only exist on a Mac. On
#        a non-Mac development machine it is skipped, and said so. In CI it runs
#        on a real Mac, which is where it matters.
if ! stat -f '%z' "$0" >/dev/null 2>&1 || ! command -v xattr >/dev/null 2>&1; then
    saltar 'assinatura e origem dos ficheiros'         'precisa do stat do BSD e do xattr, que só existem num Mac; na integração contínua corre'
else

# PT-PT: Uma ISO de mentira, com o CD001 no sitio certo — o sector 16.
# EN-UK: A fake ISO with CD001 in the right place — sector 16.
ISO_BOA="${TMP}/boa.iso"
dd if=/dev/zero of="$ISO_BOA" bs=1 count=33024 2>/dev/null
printf 'CD001' | dd of="$ISO_BOA" bs=1 seek=32769 conv=notrunc 2>/dev/null

# PT-PT: E um .zip com nome de ISO, que e o engano honesto mais comum.
# EN-UK: And a .zip named as an ISO, the commonest honest mistake.
ISO_MA="${TMP}/ma.iso"
dd if=/dev/zero of="$ISO_MA" bs=1 count=33024 2>/dev/null
printf 'PK\003\004' | dd of="$ISO_MA" bs=1 conv=notrunc 2>/dev/null

ISO_CURTA="${TMP}/curta.iso"
dd if=/dev/zero of="$ISO_CURTA" bs=1 count=512 2>/dev/null

QCOW="${TMP}/boa.qcow2"
printf 'QFI\373' > "$QCOW"

IMG="${TMP}/qualquer.img"
dd if=/dev/zero of="$IMG" bs=1 count=1024 2>/dev/null

t_iso_verdadeira()  { assinatura_ficheiro "$ISO_BOA" >/dev/null; }
t_zip_apanhado()    {
    local s; s="$(assinatura_ficheiro "$ISO_MA" || true)"
    afirmar_contem "$s" 'zip'
}
t_truncado()        {
    local s; s="$(assinatura_ficheiro "$ISO_CURTA" || true)"
    afirmar_contem "$s" 'pequeno'
}
t_qcow_verdadeiro() { assinatura_ficheiro "$QCOW" >/dev/null; }
# PT-PT: Sao bytes em bruto. Nao ha nada para verificar, e recusar por isso
#        seria recusar um formato legitimo.
t_img_sem_assinatura() {
    local s; s="$(assinatura_ficheiro "$IMG")"
    afirmar_contem "$s" 'não tem assinatura'
}
t_sem_ficheiro_assinatura() { ! assinatura_ficheiro "${TMP}/nada.iso" >/dev/null; }

# PT-PT: Nao encontrar a marca de origem nao quer dizer que o ficheiro seja de
#        confianca; quer dizer que o sistema nao sabe. E a mesma diferenca que o
#        resto do programa faz entre "nao encontrei" e "nao consegui olhar".
t_origem_desconhecida() {
    local s; s="$(origem_ficheiro "$ISO_BOA" || true)"
    afirmar_contem "$s" 'não sabe'
}

teste 'reconhece uma ISO verdadeira pelo CD001' t_iso_verdadeira
teste 'apanha um .zip com nome de ISO' t_zip_apanhado
teste 'apanha um descarregamento que ficou a meio' t_truncado
teste 'reconhece um qcow2 pelo QFI' t_qcow_verdadeiro
teste 'um .img não tem assinatura, e isso não é uma falha' t_img_sem_assinatura
teste 'um ficheiro que não existe não rebenta' t_sem_ficheiro_assinatura
teste 'sem marca de origem, diz que não se sabe' t_origem_desconhecida

fi


# ---------------------------------------------------------------------------
# PT-PT: Instalacao de um hipervisor
#
#        Nada aqui instala coisa nenhuma, e nada aqui liga a rede. O que se
#        testa sao as decisoes tomadas **antes** de instalar: que versao, que
#        ficheiro dos que a Oracle publica, de que dominio, e o que se faz
#        quando a assinatura nao confere.
#
# EN-UK: Installing a hypervisor. Nothing here installs anything and nothing
#        touches the network. What is tested are the decisions taken **before**
#        installing.
# ---------------------------------------------------------------------------
grupo 'Versão publicada pela Oracle'

t_versao_boa()      { afirmar_igual '7.2.16' "$(versao_valida '7.2.16')"; }
t_versao_com_fim()  { afirmar_igual '7.2.16' "$(versao_valida '7.2.16
')"; }
t_versao_vazia()    { ! versao_valida '' >/dev/null 2>&1; }

# PT-PT: O texto vem do servidor da Oracle e vai ser colado dentro de um URL; se
#        passasse uma barra ou um `..`, o endereco deixava de apontar para onde
#        o programa julga que aponta.
# EN-UK: The text comes from Oracle's server and goes into a URL; a slash or a
#        `..` would make it point elsewhere.
t_versao_com_barra() {
    ! versao_valida '7.2.16/../../etc' >/dev/null 2>&1 \
        && ! versao_valida '../7.2.16' >/dev/null 2>&1
}
t_versao_palavra() { ! versao_valida 'latest' >/dev/null 2>&1 && ! versao_valida '7.2' >/dev/null 2>&1; }

teste 'aceita um número de versão' t_versao_boa
teste 'ignora o fim de linha que o ficheiro traz' t_versao_com_fim
teste 'recusa um ficheiro vazio' t_versao_vazia
teste 'recusa uma versão com barras — ia ser colada num endereço' t_versao_com_barra
teste 'recusa uma versão que não é um número' t_versao_palavra


grupo 'Escolha do instalador no manifesto'

MANIFESTO_ORACLE="${TMP}/SHA256SUMS-oracle"
cat > "$MANIFESTO_ORACLE" <<'FIM'
8237c1c8ef0c837c47394b82959d7ea42626ad3140e452f4f59561021b428eed *VirtualBox-7.2.16-174877-OSX.dmg
43984f01e4dedd82a22d3c38d432a22f6df9bc2f5e5333a722b734c5bf8b6636 *VirtualBox-7.2.16-174877-macOSArm64.dmg
9383a42bffa5c0ac4bc5f1c7d820478d84380d3a17b65aa9b43e6778cbdb615a *VirtualBox-7.2.16-174877-Win.exe
FIM

t_escolhe_intel() {
    local r; r="$(ler_manifesto "$MANIFESTO_ORACLE" "$(padrao_instalador 7.2.16 x86_64)")"
    afirmar_contem "$r" 'VirtualBox-7.2.16-174877-OSX.dmg'
}

# PT-PT: O ficheiro de Intel e o de Apple Silicon estao os dois no mesmo
#        manifesto e so diferem no sufixo. Escolher o errado dava um instalador
#        que abre e depois nao instala, sem dizer porque.
# EN-UK: The Intel and Apple Silicon files sit in the same manifest and differ
#        only in the suffix. Picking the wrong one gives an installer that opens
#        and then refuses, without saying why.
t_escolhe_arm() {
    local r; r="$(ler_manifesto "$MANIFESTO_ORACLE" "$(padrao_instalador 7.2.16 arm64)")"
    afirmar_contem "$r" 'VirtualBox-7.2.16-174877-macOSArm64.dmg'
}

t_nao_apanha_windows() {
    local r; r="$(ler_manifesto "$MANIFESTO_ORACLE" "$(padrao_instalador 7.2.16 x86_64)")"
    [[ "$r" != *'Win.exe'* ]] || { printf 'escolheu o instalador de Windows\n'; return 1; }
}

# PT-PT: O numero de compilacao nao esta fixado no programa: se estivesse, isto
#        deixava de funcionar na versao seguinte.
# EN-UK: The build number is not pinned: were it, this would break on the next
#        release.
t_compilacao_livre() {
    local p; p="$(padrao_instalador 7.2.16 x86_64)"
    [[ 'VirtualBox-7.2.16-999999-OSX.dmg' =~ $p ]]
}

t_nao_aceita_sufixo() {
    local p; p="$(padrao_instalador 7.2.16 x86_64)"
    ! [[ 'VirtualBox-7.2.16-174877-OSX.dmg.zip' =~ $p ]]
}

t_nao_aceita_outra_versao() {
    local p; p="$(padrao_instalador 7.2.16 x86_64)"
    ! [[ 'VirtualBox-7.1.4-165100-OSX.dmg' =~ $p ]]
}

teste 'escolhe o ficheiro de um Mac Intel' t_escolhe_intel
teste 'escolhe o ficheiro de um Mac com chip da Apple' t_escolhe_arm
teste 'não escolhe o instalador de Windows' t_nao_apanha_windows
teste 'o número de compilação não está fixado no programa' t_compilacao_livre
teste 'não aceita um nome com qualquer coisa colada ao fim' t_nao_aceita_sufixo
teste 'não aceita o instalador de outra versão' t_nao_aceita_outra_versao


grupo 'A lista de domínios da instalação é separada da do catálogo'

t_dom_oracle() {
    local -a d=(); local x
    while IFS= read -r x; do d+=("$x"); done < <(dominios_virtualbox)
    dominio_confiavel 'https://download.virtualbox.org/virtualbox/LATEST.TXT' "${d[@]}"
}

t_dom_http() {
    local -a d=(); local x
    while IFS= read -r x; do d+=("$x"); done < <(dominios_virtualbox)
    ! dominio_confiavel 'http://download.virtualbox.org/virtualbox/LATEST.TXT' "${d[@]}"
}

# PT-PT: As duas listas sao separadas de proposito. Se fossem uma so, um
#        catalogo adulterado podia mandar buscar uma "imagem" ao servidor da
#        Oracle, e este ficheiro podia ir buscar um "instalador" ao servidor da
#        Ubuntu. Nenhuma das duas coisas faz sentido.
# EN-UK: The two lists are separate on purpose. Merged, a tampered catalogue
#        could fetch an "image" from Oracle's server, and this file could fetch
#        an "installer" from Ubuntu's.
t_dom_nao_serve_imagens() {
    local -a d=(); local x
    while IFS= read -r x; do d+=("$x"); done < <(dominios_virtualbox)
    ! dominio_confiavel 'https://releases.ubuntu.com/24.04/SHA256SUMS' "${d[@]}"
}

t_catalogo_sem_virtualbox() { ! grep -qi 'virtualbox\.org' "${FONTE}/catalogo.json"; }

teste 'aceita o servidor de descarregamento da Oracle' t_dom_oracle
teste 'recusa HTTP, como em todo o resto do programa' t_dom_http
teste 'não deixa descarregar uma imagem de sistema por esta lista' t_dom_nao_serve_imagens
teste 'a lista da instalação não entrou no catálogo' t_catalogo_sem_virtualbox


grupo 'Assinatura da Apple'

if command -v spctl >/dev/null 2>&1; then

    t_assinatura_sem_ficheiro() {
        local e=0; assinatura_apple_confere "${TMP}/nao-existe.dmg" Oracle || e=$?
        afirmar_igual '1' "$e"
    }

    # PT-PT: Um ficheiro que ninguem assinou tem de ser recusado. Nao se pode
    #        provar aqui o caso contrario -- fabricar um `.dmg` notarizado pela
    #        Apple em nome da Oracle e, felizmente, exactamente o que nao se
    #        consegue fazer.
    # EN-UK: A file nobody signed must be refused. The converse cannot be proved
    #        here: fabricating an Apple-notarised `.dmg` in Oracle's name is,
    #        happily, precisely what cannot be done.
    t_assinatura_ficheiro_qualquer() {
        printf 'isto não é um instalador\n' > "${TMP}/qualquer.dmg"
        ! assinatura_apple_confere "${TMP}/qualquer.dmg" Oracle
    }

    t_pacote_ficheiro_qualquer() {
        printf 'isto não é um pacote\n' > "${TMP}/qualquer.pkg"
        ! assinatura_pacote_confere "${TMP}/qualquer.pkg" Oracle
    }

    teste 'um ficheiro que não existe dá o código de ausente' t_assinatura_sem_ficheiro
    teste 'um ficheiro que ninguém assinou é recusado' t_assinatura_ficheiro_qualquer
    teste 'um pacote que ninguém assinou é recusado' t_pacote_ficheiro_qualquer

    saltar 'um .dmg notarizado pela Apple em nome da Oracle é aceite' \
           'não se consegue fabricar um para o teste — que é a razão de a camada valer'
else
    saltar 'assinatura da Apple no ficheiro descarregado' \
           'o spctl só existe num Mac — este grupo corre no runner de macOS'
fi


grupo 'Homebrew'

# PT-PT: Este programa recusa-se a instalar o Homebrew, e a razao e a mesma que
#        o levou a existir: instala-se passando um script da Internet
#        directamente a um interpretador. Nao seria coerente recusar esse padrao
#        com imagens e aceita-lo com o resto.
# EN-UK: This program refuses to install Homebrew, for the same reason it
#        exists: it is installed by piping a script from the Internet straight
#        into an interpreter.
t_nao_instala_homebrew() {
    ! grep -qE 'curl[^|]*\|[[:space:]]*(ba)?sh|install\.sh\)"' "${FONTE}/lib/instalacao.sh"
}

t_deteccao_homebrew() {
    if command -v brew >/dev/null 2>&1; then tem_homebrew; else ! tem_homebrew; fi
}

teste 'não instala o Homebrew passando um script a um interpretador' t_nao_instala_homebrew
teste 'a detecção do Homebrew corresponde à realidade desta máquina' t_deteccao_homebrew


# ---------------------------------------------------------------------------
# PT-PT: Os hipervisores de terceiros deste Mac
#
#        Nada aqui precisa da Parallels nem da Fusion instaladas, e isso e
#        deliberado: sao produtos pagos, e nem quem escreveu isto nem o runner
#        os tem. O que se testa e o `.vmx` -- que e texto, e portanto
#        verificavel sem hipervisor nenhum -- as duas traducoes de vocabulario,
#        e a deteccao, que tem de saber dizer "nao esta ca" sem rebentar.
#
# EN-UK: This Mac's third-party hypervisors. Nothing here needs Parallels or
#        Fusion installed, deliberately: they are paid products, and neither the
#        author nor the runner has them.
# ---------------------------------------------------------------------------
grupo 'Detecção dos hipervisores de terceiros'

t_fusion_deteccao() {
    local e=0
    estado_fusion || e=$?
    case $e in
        0|1|2) return 0 ;;
        *) printf 'estado inesperado: %s\n' "$e"; return 1 ;;
    esac
}

t_parallels_deteccao() {
    # PT-PT: A pergunta e pelo `prlctl` e nao pela aplicacao: a aplicacao pode
    #        estar instalada com as ferramentas de linha de comandos por
    #        instalar, e nesse caso este programa nao lhe consegue tocar -- que
    #        e a mesma coisa, do ponto de vista de quem esta a decidir.
    # EN-UK: The question is about `prlctl`, not the application: the
    #        application can be installed with its command-line tools missing.
    if command -v prlctl >/dev/null 2>&1; then estado_parallels; else ! estado_parallels; fi
}

teste 'a detecção da Fusion corre sem rebentar' t_fusion_deteccao
teste 'a detecção da Parallels corresponde à realidade desta máquina' t_parallels_deteccao


grupo 'Vocabulário da Fusion e da Parallels'

# PT-PT: Os dois produtos nao coincidem em nada, e nem sequer sao do mesmo
#        genero: a Parallels quer o nome da distribuicao, a Fusion quer um
#        identificador com a arquitectura la dentro. Traduzir mal nao rebenta --
#        cria uma maquina com o controlador de disco errado, que arranca devagar
#        sem ninguem perceber porque.
# EN-UK: The two share no vocabulary and are not even of the same kind:
#        Parallels wants the distribution's name, Fusion an identifier with the
#        architecture inside. Translating wrong does not crash -- it creates a
#        machine with the wrong disk controller.
t_fusion_ubuntu() { afirmar_igual 'ubuntu-64'   "$(tipo_fusion 'ubuntu-24-04' 'linux')"; }
t_fusion_alma()   { afirmar_igual 'rhel9-64'    "$(tipo_fusion 'almalinux-9' 'linux')"; }
t_fusion_mint()   { afirmar_igual 'ubuntu-64'   "$(tipo_fusion 'linuxmint-22' 'linux')"; }
t_fusion_outra()  {
    afirmar_igual 'otherlinux-64' "$(tipo_fusion 'nunca-visto' 'linux')" \
        && afirmar_igual 'windows11-64' "$(tipo_fusion 'nunca-visto' 'windows')"
}

t_prl_ubuntu()  { afirmar_igual 'ubuntu'      "$(distribuicao_parallels 'ubuntu-24-04' 'linux')"; }
t_prl_fedora()  { afirmar_igual 'fedora-core' "$(distribuicao_parallels 'fedora-40' 'linux')"; }
t_prl_windows() { afirmar_igual 'win-11'      "$(distribuicao_parallels 'windows-11' 'windows')"; }
t_prl_outra()   { afirmar_igual 'linux'       "$(distribuicao_parallels 'nunca-visto' 'linux')"; }

# PT-PT: Os dois vocabularios tem mesmo de ser diferentes. Se algum dia alguem
#        os "simplificar" para um so, este teste falha -- que e o que se quer.
# EN-UK: The two vocabularies must differ. Should anybody ever "simplify" them
#        into one, this test fails -- which is the point.
t_vocabularios_diferentes() {
    local f p
    f="$(tipo_fusion 'ubuntu-24-04' 'linux')"
    p="$(distribuicao_parallels 'ubuntu-24-04' 'linux')"
    afirmar_diferente "$f" "$p"
}

teste 'a Fusion reconhece o Ubuntu' t_fusion_ubuntu
teste 'a Fusion reconhece a AlmaLinux como RHEL' t_fusion_alma
teste 'para a Fusion, o Mint é um Ubuntu' t_fusion_mint
teste 'uma distribuição desconhecida ainda dá um tipo utilizável' t_fusion_outra
teste 'a Parallels reconhece o Ubuntu' t_prl_ubuntu
teste 'a Parallels chama fedora-core à Fedora' t_prl_fedora
teste 'a Parallels reconhece o Windows' t_prl_windows
teste 'uma distribuição desconhecida ainda dá uma distribuição utilizável' t_prl_outra
teste 'os dois vocabulários não são o mesmo, e não se devem juntar' t_vocabularios_diferentes


grupo 'O ficheiro .vmx da Fusion'

t_vmx_numeros() {
    local v; v="$(conteudo_vmx lab ubuntu-64 4 8 lab.vmdk '' nao)"
    afirmar_contem "$v" 'numvcpus = "4"' \
        && afirmar_contem "$v" 'guestOS = "ubuntu-64"' \
        && afirmar_contem "$v" 'displayName = "lab"'
}

# PT-PT: O campo chama-se `memsize` e e em megabytes. Passar-lhe os GB
#        directamente dava a maquina oito megabytes de memoria, e o erro so
#        aparece quando ela nao arranca.
# EN-UK: The field is `memsize`, in megabytes.
t_vmx_memoria() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 8 lab.vmdk '' nao)"
    afirmar_contem "$v" 'memsize = "8192"'
}

t_vmx_disco_relativo() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk '' nao)"
    afirmar_contem "$v" 'nvme0:0.fileName = "lab.vmdk"' \
        && ! printf '%s' "$v" | grep -q 'nvme0:0.fileName = "/'
}

t_vmx_com_cd() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk /Users/x/ubuntu.iso nao)"
    afirmar_contem "$v" 'cdrom-image'
}

t_vmx_sem_cd() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk '' nao)"
    ! printf '%s' "$v" | grep -q 'cdrom-image'
}

t_vmx_nat() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk '' nao)"
    afirmar_contem "$v" 'ethernet0.connectionType = "nat"'
}

t_vmx_efi() {
    local v; v="$(conteudo_vmx lab windows11-64 2 4 lab.vmdk '' sim)"
    afirmar_contem "$v" 'firmware = "efi"'
}

t_vmx_sem_pergunta() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk '' nao)"
    afirmar_contem "$v" 'uuid.action = "create"'
}

teste 'leva os números que se lhe deram' t_vmx_numeros
teste 'a memória vai em megabytes, e não em gigabytes' t_vmx_memoria
teste 'o caminho do disco vai relativo, para o pacote se poder mover' t_vmx_disco_relativo
teste 'um instalador leva CD' t_vmx_com_cd
teste 'uma imagem de disco não leva CD' t_vmx_sem_cd
teste 'a rede fica em NAT' t_vmx_nat
teste 'um convidado de Windows leva EFI' t_vmx_efi
teste 'não pergunta se a máquina foi movida na primeira arrancada' t_vmx_sem_pergunta


resumo
