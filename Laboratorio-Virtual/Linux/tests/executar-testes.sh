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
# shellcheck source=../src/lib/imagem_local.sh
. "${FONTE}/lib/imagem_local.sh"
# shellcheck source=../src/lib/vmware.sh
. "${FONTE}/lib/vmware.sh"
# shellcheck source=../src/lib/instalacao.sh
. "${FONTE}/lib/instalacao.sh"

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
t_libvirt_qcow()    { formato_suportado '.qcow2' 'libvirt' >/dev/null; }
t_libvirt_vmdk()    { formato_suportado '.vmdk' 'libvirt' >/dev/null; }
t_libvirt_sem_ova() { ! formato_suportado '.ova' 'libvirt' >/dev/null; }
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
t_ova_no_libvirt_explica() {
    local s; s="$(formato_suportado '.ova' 'libvirt' || true)"
    afirmar_contem "$s" 'VirtualBox'
}
t_extensao_estranha() {
    local s; s="$(formato_suportado '.zip' 'libvirt' || true)"
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
teste 'o libvirt fala qcow2' t_libvirt_qcow
teste 'o libvirt fala vmdk' t_libvirt_vmdk
teste 'o libvirt não importa appliances' t_libvirt_sem_ova
teste 'o VirtualBox fala vdi' t_vbox_vdi
teste 'o VirtualBox importa appliances' t_vbox_ova
teste 'o VirtualBox não lê qcow2 de forma fiável' t_vbox_sem_qcow
teste 'quando o formato não serve, diz-se como converter' t_diz_como_converter
teste 'uma appliance no libvirt explica para onde ir' t_ova_no_libvirt_explica
teste 'uma extensão que não se conhece dá a lista das que se conhecem' t_extensao_estranha
teste 'há um perfil para cada tipo de convidado' t_perfis_completos
teste 'um perfil que não existe cai no genérico' t_perfil_desconhecido


# ===========================================================================
grupo 'Assinatura do conteúdo de um ficheiro'
# ===========================================================================

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


# ---------------------------------------------------------------------------
# PT-PT: Instalacao de um hipervisor
#
#        Nada aqui instala coisa nenhuma, e nada aqui liga a rede. O que se
#        testa sao as decisoes que se tomam **antes** de instalar: que versao,
#        que ramo do repositorio, com que chave, de que dominio. Sao essas que
#        decidem se o que se instala e o da Oracle ou o de outra pessoa.
#
# EN-UK: Installing a hypervisor. Nothing here installs anything and nothing
#        touches the network. What is tested are the decisions taken **before**
#        installing: which version, which repository branch, with which key,
#        from which domain.
# ---------------------------------------------------------------------------
grupo 'Versão publicada pela Oracle'

t_versao_boa()      { afirmar_igual '7.2.16' "$(versao_valida '7.2.16')"; }
t_versao_com_fim()  { afirmar_igual '7.2.16' "$(versao_valida '7.2.16
')"; }
t_versao_vazia()    { ! versao_valida '' >/dev/null 2>&1; }

# PT-PT: Este e o teste que interessa deste grupo. O texto vem do servidor da
#        Oracle e vai ser colado dentro de um URL; se passasse uma barra ou um
#        `..`, o endereco deixava de apontar para onde o programa julga.
# EN-UK: The test that matters here. The text comes from Oracle's server and
#        goes into a URL; a slash or a `..` would make it point elsewhere.
t_versao_com_barra() {
    ! versao_valida '7.2.16/../../etc' >/dev/null 2>&1 \
        && ! versao_valida '../7.2.16' >/dev/null 2>&1
}
t_versao_palavra()  { ! versao_valida 'latest' >/dev/null 2>&1 && ! versao_valida '7.2' >/dev/null 2>&1; }
t_serie()           { afirmar_igual '7.2' "$(serie_versao '7.2.16')"; }

teste 'aceita um número de versão' t_versao_boa
teste 'ignora o fim de linha que o ficheiro traz' t_versao_com_fim
teste 'recusa um ficheiro vazio' t_versao_vazia
teste 'recusa uma versão com barras — ia ser colada num endereço' t_versao_com_barra
teste 'recusa uma versão que não é um número' t_versao_palavra
teste 'a série sai da versão, e não está escrita no programa' t_serie


grupo 'Comandos que acrescentam o repositório da Oracle'

# PT-PT: O nome do pacote sai da serie, que sai da versao que a Oracle publica.
#        Fixar `virtualbox-7.1` aqui era garantir que isto deixava de funcionar
#        na serie seguinte -- e a propria documentacao da Oracle ainda diz 7.1
#        numa pagina onde ja se descarrega a 7.2.
# EN-UK: The package name comes from the series, which comes from the version
#        Oracle publishes. Pinning `virtualbox-7.1` would break this on the next
#        series -- and Oracle's own documentation still says 7.1 on a page that
#        already ships 7.2.
t_apt_pacote() {
    local s; s="$(passos_virtualbox_apt /tmp/chave.asc noble 7.2)"
    afirmar_contem "$s" 'virtualbox-7.2'
}

t_apt_ramo() {
    local s; s="$(passos_virtualbox_apt /tmp/chave.asc bookworm 7.2)"
    afirmar_contem "$s" 'bookworm contrib'
}

# PT-PT: O `signed-by` e o que impede a chave da Oracle de passar a poder
#        assinar pacotes de **qualquer** repositorio configurado na maquina. E
#        exactamente o problema que o `apt-key` tinha, e a razao por que foi
#        retirado -- e um script que ainda o use reintroduz o problema.
# EN-UK: `signed-by` is what stops Oracle's key from being able to sign packages
#        from **any** repository on the machine. That was `apt-key`'s problem and
#        the reason it was removed; a script still using it reintroduces it.
t_apt_signed_by() {
    local s; s="$(passos_virtualbox_apt /tmp/chave.asc noble 7.2)"
    afirmar_contem "$s" 'signed-by=/usr/share/keyrings/oracle-virtualbox-2016.gpg'
}

t_apt_sem_apt_key() {
    local s; s="$(passos_virtualbox_apt /tmp/chave.asc noble 7.2)"
    [[ "$s" != *'apt-key'* ]] || { printf 'usa o apt-key, que foi retirado por ser inseguro\n'; return 1; }
}

t_apt_https() {
    local s; s="$(passos_virtualbox_apt /tmp/chave.asc noble 7.2)"
    afirmar_contem "$s" 'https://download.virtualbox.org/virtualbox/debian'
}

t_rpm_fedora() {
    local s; s="$(passos_virtualbox_rpm fedora 7.2)"
    afirmar_contem "$s" 'rpm/fedora/virtualbox.repo' && afirmar_contem "$s" 'VirtualBox-7.2'
}

t_rpm_suse() {
    local s; s="$(passos_virtualbox_rpm opensuse 7.2)"
    afirmar_contem "$s" 'zypper'
}

t_rpm_desconhecida() { ! passos_virtualbox_rpm nada 7.2 >/dev/null 2>&1; }

teste 'o nome do pacote sai da série publicada pela Oracle' t_apt_pacote
teste 'usa o ramo da distribuição que está a correr' t_apt_ramo
teste 'a linha do repositório fixa a chave com signed-by' t_apt_signed_by
teste 'não usa o apt-key, que foi retirado por ser inseguro' t_apt_sem_apt_key
teste 'o repositório é HTTPS' t_apt_https
teste 'conhece o repositório RPM da Fedora' t_rpm_fedora
teste 'conhece o repositório do openSUSE' t_rpm_suse
teste 'uma variante que não existe não inventa comandos' t_rpm_desconhecida


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

t_catalogo_sem_virtualbox() {
    ! grep -qi 'virtualbox\.org' "${FONTE}/catalogo.json"
}

teste 'aceita o servidor de descarregamento da Oracle' t_dom_oracle
teste 'recusa HTTP, como em todo o resto do programa' t_dom_http
teste 'não deixa descarregar uma imagem de sistema por esta lista' t_dom_nao_serve_imagens
teste 'a lista da instalação não entrou no catálogo' t_catalogo_sem_virtualbox


grupo 'A chave de assinatura da Oracle'

# PT-PT: A impressao esta fixada no programa, e e uma condicao e nao um aviso.
#        Descarregar uma chave e acrescenta-la ao sistema sem a comparar com
#        nada e uma cerimonia sem conteudo: se o canal estivesse comprometido, a
#        chave que chegava era a do atacante e passava a assinar o que ele
#        quisesse, para sempre.
# EN-UK: The fingerprint is pinned, and is a condition rather than a warning.
#        Downloading a key and adding it to the system without comparing it to
#        anything is an empty ceremony.
t_impressao_forma() {
    [[ "$IMPRESSAO_ORACLE" =~ ^[0-9A-F]{40}$ ]] \
        || { printf 'a impressão fixada não tem a forma de uma impressão digital: %s\n' "$IMPRESSAO_ORACLE"; return 1; }
}

t_chave_inexistente() { ! chave_oracle_confere "${TMP}/nao-existe.asc"; }

t_chave_que_nao_e_chave() {
    printf 'isto não é uma chave\n' > "${TMP}/falsa.asc"
    ! chave_oracle_confere "${TMP}/falsa.asc"
}

teste 'a impressão fixada tem a forma de uma impressão digital' t_impressao_forma
teste 'um ficheiro de chave que não existe não passa' t_chave_inexistente
teste 'um ficheiro que não é uma chave não passa' t_chave_que_nao_e_chave

if command -v gpg >/dev/null 2>&1; then
    # PT-PT: A chave verdadeira nao esta no repositorio de proposito -- seria
    #        uma copia a envelhecer ao lado da original. O que se pode provar
    #        sem rede e que a comparacao **e** feita: uma chave legitima de
    #        outra entidade tem de ser recusada.
    # EN-UK: The real key is deliberately not in the repository -- it would be a
    #        stale copy beside the original. What can be proved offline is that
    #        the comparison **happens**: a legitimate key from somebody else must
    #        be refused.
    t_chave_de_outra_entidade() {
        local anel="${TMP}/anel-teste"
        mkdir -p "$anel"; chmod 700 "$anel"
        gpg --homedir "$anel" --batch --quiet --passphrase '' \
            --quick-generate-key 'Alguem Que Nao E A Oracle <nao@oracle.invalido>' \
            default default never >/dev/null 2>&1 || return 0
        gpg --homedir "$anel" --batch --quiet --armor --export > "${TMP}/outra.asc" 2>/dev/null || return 0
        [[ -s "${TMP}/outra.asc" ]] || return 0
        ! chave_oracle_confere "${TMP}/outra.asc"
    }
    teste 'uma chave válida de outra entidade é recusada' t_chave_de_outra_entidade
else
    saltar 'uma chave válida de outra entidade é recusada' \
           'o gpg não está instalado nesta máquina — corre no runner'
fi


# ---------------------------------------------------------------------------
# PT-PT: A VMware que ja esteja instalada
#
#        Nada aqui precisa da VMware instalada, e isso e deliberado: quem
#        escreveu isto nao a tem, e o runner tambem nao. O que se testa e o
#        `.vmx` -- que e texto, e portanto verificavel sem hipervisor nenhum --
#        e a deteccao, que tem de saber dizer "nao esta ca" sem rebentar.
#
# EN-UK: VMware, when already installed. Nothing here needs it installed,
#        deliberately: neither the author nor the runner has it. What is tested
#        is the `.vmx` -- text, therefore checkable without any hypervisor --
#        and the detection, which must say "not here" without blowing up.
# ---------------------------------------------------------------------------
grupo 'Detecção da VMware'

t_vmware_deteccao() {
    local e=0
    estado_vmware || e=$?
    # PT-PT: Qualquer um dos tres e uma resposta valida. O que nao pode e a
    #        funcao rebentar ou devolver uma coisa que ninguem sabe interpretar.
    # EN-UK: Any of the three is a valid answer. What it must not do is blow up
    #        or return something nobody can interpret.
    case $e in
        0|1|2) return 0 ;;
        *) printf 'estado inesperado: %s\n' "$e"; return 1 ;;
    esac
}

teste 'a detecção corre nesta máquina sem rebentar' t_vmware_deteccao


grupo 'Tipo de convidado da VMware'

t_tipo_ubuntu() { afirmar_igual 'ubuntu-64'   "$(tipo_vmware 'ubuntu-24-04-desktop' 'linux')"; }
t_tipo_debian() { afirmar_igual 'debian12-64' "$(tipo_vmware 'debian-12' 'linux')"; }
t_tipo_alma()   { afirmar_igual 'rhel9-64'    "$(tipo_vmware 'almalinux-9' 'linux')"; }
t_tipo_mint()   { afirmar_igual 'ubuntu-64'   "$(tipo_vmware 'linuxmint-22' 'linux')"; }
t_tipo_kali()   { afirmar_igual 'debian12-64' "$(tipo_vmware 'kali-2024' 'linux')"; }

# PT-PT: Este campo decide o controlador de disco e o relogio. Cair em
#        `other-64` quando se sabe que e Linux seria criar uma maquina com
#        metade das definicoes erradas -- e a lentidao que daqui resulta nunca e
#        associada a este campo.
# EN-UK: This field decides the disk controller and the clock. Falling to
#        `other-64` when Linux is known would create a machine with half its
#        settings wrong.
t_tipo_desconhecida() {
    afirmar_igual 'otherlinux-64' "$(tipo_vmware 'nunca-visto' 'linux')" \
        && afirmar_igual 'windows11-64' "$(tipo_vmware 'nunca-visto' 'windows')" \
        && afirmar_igual 'other-64' "$(tipo_vmware '' '')"
}

teste 'reconhece o Ubuntu' t_tipo_ubuntu
teste 'reconhece o Debian' t_tipo_debian
teste 'reconhece a AlmaLinux como RHEL' t_tipo_alma
teste 'o Mint é um Ubuntu para efeitos da VMware' t_tipo_mint
teste 'o Kali é um Debian para efeitos da VMware' t_tipo_kali
teste 'uma distribuição desconhecida ainda dá um tipo utilizável' t_tipo_desconhecida


grupo 'O ficheiro .vmx'

t_vmx_numeros() {
    local v; v="$(conteudo_vmx lab ubuntu-64 4 8 lab.vmdk '' nao)"
    afirmar_contem "$v" 'numvcpus = "4"' \
        && afirmar_contem "$v" 'guestOS = "ubuntu-64"' \
        && afirmar_contem "$v" 'displayName = "lab"'
}

# PT-PT: O campo chama-se `memsize` e e em megabytes. Passar-lhe os GB
#        directamente dava a maquina oito megabytes de memoria, e o erro so
#        aparece quando ela nao arranca.
# EN-UK: The field is `memsize`, in megabytes. Passing GB straight in would give
#        the machine eight megabytes, and the mistake only shows when it will
#        not boot.
t_vmx_memoria_mb() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 8 lab.vmdk '' nao)"
    afirmar_contem "$v" 'memsize = "8192"'
}

t_vmx_memoria_fraccao() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 1.5 lab.vmdk '' nao)"
    afirmar_contem "$v" 'memsize = "1536"'
}

# PT-PT: O caminho do disco vai relativo para a pasta da maquina se poder mover
#        para outro disco sem partir.
# EN-UK: The disk path goes in relative so the machine folder can be moved.
t_vmx_disco_relativo() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk '' nao)"
    afirmar_contem "$v" 'nvme0:0.fileName = "lab.vmdk"' \
        && ! printf '%s' "$v" | grep -q 'nvme0:0.fileName = "/'
}

# PT-PT: E a distincao que decide se a maquina arranca ou fica num ecra a dizer
#        que nao ha nada para arrancar.
# EN-UK: The distinction that decides whether the machine boots.
t_vmx_com_cd() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk /imagens/ubuntu.iso nao)"
    afirmar_contem "$v" 'cdrom-image' && afirmar_contem "$v" 'ubuntu.iso'
}

t_vmx_sem_cd() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk '' nao)"
    ! printf '%s' "$v" | grep -q 'cdrom-image'
}

t_vmx_nat() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk '' nao)"
    afirmar_contem "$v" 'ethernet0.connectionType = "nat"'
}

# PT-PT: Sem `firmware = "efi"`, o instalador do Windows 11 recusa-se a comecar
#        por causa do modo de arranque -- e a mensagem que da fala de outra coisa.
# EN-UK: Without `firmware = "efi"`, the Windows 11 installer refuses to start
#        over boot mode, with a message about something else.
t_vmx_efi() {
    local v; v="$(conteudo_vmx lab windows11-64 2 4 lab.vmdk '' sim)"
    afirmar_contem "$v" 'firmware = "efi"'
}

t_vmx_sem_efi() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk '' nao)"
    ! printf '%s' "$v" | grep -q 'firmware'
}

# PT-PT: Uma maquina acabada de criar por um script nao foi movida nem copiada,
#        e a pergunta da VMware na primeira arrancada so confunde quem a abre.
# EN-UK: A machine a script just created was neither moved nor copied.
t_vmx_sem_pergunta() {
    local v; v="$(conteudo_vmx lab ubuntu-64 2 4 lab.vmdk '' nao)"
    afirmar_contem "$v" 'uuid.action = "create"'
}

teste 'leva os números que se lhe deram' t_vmx_numeros
teste 'a memória vai em megabytes, e não em gigabytes' t_vmx_memoria_mb
teste 'meio gigabyte também dá o número certo' t_vmx_memoria_fraccao
teste 'o caminho do disco vai relativo, para a pasta se poder mover' t_vmx_disco_relativo
teste 'um instalador leva CD' t_vmx_com_cd
teste 'uma imagem de disco não leva CD' t_vmx_sem_cd
teste 'a rede fica em NAT' t_vmx_nat
teste 'um convidado de Windows leva EFI' t_vmx_efi
teste 'um convidado de Linux não leva EFI' t_vmx_sem_efi
teste 'não pergunta se a máquina foi movida na primeira arrancada' t_vmx_sem_pergunta


resumo
