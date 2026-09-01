#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Testes do Laboratorio Virtual, versao de Linux.
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
# EN-UK: Virtual Lab tests, Linux version. No test touches the network, creates
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

CATALOGO="${FONTE}/catalogo.json"
SOMA_EXEMPLO='9f2f1cbd3ef1a0d4a49a63b3e9b3d9f0c1a2b3c4d5e6f708192a3b4c5d6e7f80'
DOMINIOS=(releases.ubuntu.com cdimage.debian.org)

printf '\n  Laboratório Virtual · testes da versão de Linux\n'


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
SOMA_REAL="$(sha256sum "${TMP}/ficheiro" | cut -d' ' -f1)"

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
grupo 'Grupos e identificadores'
# ===========================================================================

t_grupos_faltam()   { afirmar_igual 'kvm libvirt' "$(grupos_em_falta 'users audio video' | tr '\n' ' ' | sed 's/ $//')"; }
t_grupos_um()       { afirmar_igual 'libvirt' "$(grupos_em_falta 'users kvm')"; }
t_grupos_nenhum()   { afirmar_vazio "$(grupos_em_falta 'users kvm libvirt')"; }

t_osinfo_ubuntu()   { afirmar_igual 'ubuntu24.04' "$(variante_osinfo 'ubuntu-24.04-desktop' 'linux')"; }
t_osinfo_debian()   { afirmar_igual 'debian12' "$(variante_osinfo 'debian-13-netinst' 'linux')"; }
t_osinfo_kali()     { afirmar_igual 'debian12' "$(variante_osinfo 'kali-linux' 'linux')"; }
t_osinfo_novo()     { afirmar_igual 'linux2022' "$(variante_osinfo 'coisa-nova' 'linux')"; }
t_osinfo_windows()  { afirmar_igual 'win11' "$(variante_osinfo 'coisa-nova' 'windows')"; }

t_vbox_ubuntu()     { afirmar_igual 'Ubuntu_64' "$(tipo_virtualbox 'ubuntu-24.04-desktop' 'linux')"; }
t_vbox_mint()       { afirmar_igual 'Ubuntu_64' "$(tipo_virtualbox 'linuxmint-cinnamon' 'linux')"; }
t_vbox_rocky()      { afirmar_igual 'RedHat_64' "$(tipo_virtualbox 'rocky-9' 'linux')"; }
t_vbox_novo()       { afirmar_igual 'Linux_64' "$(tipo_virtualbox 'coisa-nova' 'linux')"; }

teste 'diz os dois grupos em falta' t_grupos_faltam
teste 'diz só o que falta quando já se pertence a um' t_grupos_um
teste 'não diz nada quando já se pertence aos dois' t_grupos_nenhum
teste 'reconhece as distribuições no osinfo' t_osinfo_ubuntu
teste 'o Debian tem a sua variante' t_osinfo_debian
teste 'o Kali é um Debian para o osinfo' t_osinfo_kali
teste 'uma distribuição desconhecida ainda dá uma variante utilizável' t_osinfo_novo
teste 'o Windows tem a sua variante' t_osinfo_windows
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


resumo
