"""
PT-PT: Testes da analise do diario, da geracao de relatorios e da configuracao.

       Nenhum destes testes corre um comando, le o diario de uma maquina real ou
       precisa de Linux. Os registos sao construidos a mao, no formato que o
       `journalctl -o json` produz, e e por isso que esta suite corre em
       qualquer sitio — incluindo numa maquina de desenvolvimento que nao seja
       Linux, e num runner de integracao continua.

EN-UK: Tests for journal analysis, report generation and configuration.

       None of these tests runs a command, reads a real machine's journal or
       needs Linux. The records are hand-built in the shape `journalctl -o json`
       produces, which is why this suite runs anywhere.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
from pathlib import Path

from ittoolkit import disks, events, network, reports, services
from ittoolkit.config import AppConfig
from ittoolkit.models import Achado, Gravidade


def registo(mensagem, unidade="cron.service", prioridade=3, instante=1_756_000_000_000_000):
    """
    PT-PT: Constroi um registo como o `journalctl -o json` o devolve.

           O `__REALTIME_TIMESTAMP` vem em microssegundos e **como texto** — e
           assim que o journalctl o escreve, e um teste que passasse um inteiro
           nao estaria a testar o que a maquina entrega.

    EN-UK: Builds a record as `journalctl -o json` returns it.

           `__REALTIME_TIMESTAMP` arrives in microseconds and **as a string** —
           that is how journalctl writes it, and a test passing an integer would
           not be testing what the machine delivers.
    """
    return {
        "MESSAGE": mensagem,
        "_SYSTEMD_UNIT": unidade,
        "PRIORITY": str(prioridade),
        "__REALTIME_TIMESTAMP": str(instante),
    }


class TestAssinatura:
    """
    PT-PT: A assinatura e o centro do modulo: e o que decide o que conta como
           «a mesma mensagem». Cada teste aqui corresponde a uma forma de o
           diario escrever um valor diferente na mesma mensagem.
    EN-UK: The signature is the module's centre: it decides what counts as "the
           same message".
    """

    def test_pid_diferente_da_a_mesma_assinatura(self):
        a = events.assinatura("systemd[1234]: falhou")
        b = events.assinatura("systemd[9876]: falhou")
        assert a == b

    def test_endereco_de_memoria_diferente_da_a_mesma_assinatura(self):
        a = events.assinatura("segfault at 0x7f3a2b ip 0x7f3a2c")
        b = events.assinatura("segfault at 0x1122ff ip 0x112300")
        assert a == b

    def test_ip_diferente_da_a_mesma_assinatura(self):
        """
        PT-PT: Cinquenta tentativas de sessao falhadas de cinquenta enderecos
               sao um ataque, e um ataque e um problema — nao cinquenta.
        EN-UK: Fifty failed logins from fifty addresses are one attack.
        """
        a = events.assinatura("Failed password for root from 192.0.2.10 port 51234 ssh2")
        b = events.assinatura("Failed password for root from 198.51.100.7 port 33012 ssh2")
        assert a == b

    def test_mensagens_realmente_diferentes_nao_se_juntam(self):
        a = events.assinatura("Out of memory: killed process")
        b = events.assinatura("I/O error on device sda")
        assert a != b

    def test_assinatura_e_limitada_em_comprimento(self):
        assert len(events.assinatura("palavra " * 200)) <= events.MAX_MENSAGEM


class TestAnalise:
    def test_agrupa_ocorrencias_iguais(self):
        registos = [registo("systemd[100]: erro"), registo("systemd[200]: erro")]
        analise = events.analisar(registos, 24, 3000)
        assert len(analise.problemas) + len(analise.outros) == 1
        grupo = (analise.problemas + analise.outros)[0]
        assert grupo.contagem == 2

    def test_separa_a_mesma_mensagem_de_unidades_diferentes(self):
        """
        PT-PT: O mesmo texto vindo de duas unidades sao dois problemas. Um
               «connection refused» do Postfix e um do Nginx nao se resolvem no
               mesmo sitio.
        EN-UK: The same text from two units is two problems.
        """
        registos = [
            registo("connection refused", unidade="postfix.service"),
            registo("connection refused", unidade="nginx.service"),
        ]
        analise = events.analisar(registos, 24, 3000)
        assert len(analise.problemas) + len(analise.outros) == 2

    def test_ordena_por_gravidade(self):
        registos = [
            registo("aviso qualquer", unidade="a.service", prioridade=4),
            registo("Out of memory: Killed process 1 (x)", unidade="kernel", prioridade=2),
        ]
        analise = events.analisar(registos, 24, 3000)
        todos = analise.problemas + analise.outros
        assert todos[0].gravidade.value <= todos[-1].gravidade.value

    def test_o_grupo_fica_com_a_prioridade_mais_grave(self):
        """
        PT-PT: Um servico que avisa noventa vezes e falha uma e um problema, nao
               um aviso. Ordenar pelo aviso enterrava-o no fim da lista.
        EN-UK: A service warning ninety times and failing once is a problem.
        """
        registos = [
            registo("systemd[1]: coisa", prioridade=4),
            registo("systemd[2]: coisa", prioridade=2),
            registo("systemd[3]: coisa", prioridade=4),
        ]
        analise = events.analisar(registos, 24, 3000)
        grupo = (analise.problemas + analise.outros)[0]
        assert grupo.nivel == 2
        assert grupo.contagem == 3

    def test_mensagem_conhecida_vai_para_problemas(self):
        registos = [registo("Out of memory: Killed process 4242 (java)", unidade="kernel")]
        analise = events.analisar(registos, 24, 3000)
        assert len(analise.problemas) == 1
        assert analise.problemas[0].regra is not None

    def test_mensagem_desconhecida_fica_nos_outros(self):
        analise = events.analisar([registo("uma coisa qualquer sem regra")], 24, 3000)
        assert analise.outros
        assert not analise.problemas

    def test_primeiro_e_ultimo_por_comparacao_de_datas(self):
        cedo = 1_756_000_000_000_000
        tarde = cedo + 3_600_000_000
        registos = [
            registo("systemd[1]: x", instante=tarde),
            registo("systemd[2]: x", instante=cedo),
        ]
        analise = events.analisar(registos, 24, 3000)
        grupo = (analise.problemas + analise.outros)[0]
        assert grupo.primeiro < grupo.ultimo

    def test_prioridade_invalida_nao_rebenta(self):
        mau = registo("x")
        mau["PRIORITY"] = "não-é-número"
        analise = events.analisar([mau], 24, 3000)
        assert analise.total == 1

    def test_registo_sem_mensagem_e_ignorado(self):
        assert events.analisar([{"_SYSTEMD_UNIT": "a.service"}], 24, 3000).total == 0

    def test_truncagem_e_declarada(self):
        registos = [registo(f"mensagem {i}") for i in range(10)]
        assert events.analisar(registos, 24, 10).truncado is True

    def test_sem_truncagem_nao_ha_aviso(self):
        assert events.analisar([registo("x")], 24, 3000).truncado is False

    def test_mensagem_longa_e_cortada(self):
        analise = events.analisar([registo("a" * 900)], 24, 3000)
        grupo = (analise.problemas + analise.outros)[0]
        assert len(grupo.exemplo) <= events.MAX_MENSAGEM + 10

    def test_mensagem_multilinha_fica_numa_linha(self):
        analise = events.analisar([registo("linha um\nlinha dois\tterceira")], 24, 3000)
        grupo = (analise.problemas + analise.outros)[0]
        assert "\n" not in grupo.exemplo
        assert "\t" not in grupo.exemplo

    def test_veredicto_sem_registos(self):
        assert "Sem eventos" in events.analisar([], 24, 3000).veredicto


class TestUnidadeDe:
    def test_prefere_a_unidade_do_systemd(self):
        assert events.unidade_de({"_SYSTEMD_UNIT": "a.service", "SYSLOG_IDENTIFIER": "b"}) == "a.service"

    def test_usa_o_identificador_quando_nao_ha_unidade(self):
        """
        PT-PT: As mensagens do kernel nao vêm de unidade nenhuma, e sem este
               recurso ficavam todas agrupadas em «desconhecido».
        EN-UK: Kernel messages come from no unit at all.
        """
        assert events.unidade_de({"SYSLOG_IDENTIFIER": "kernel"}) == "kernel"

    def test_ultimo_recurso_e_o_executavel(self):
        assert events.unidade_de({"_COMM": "sshd"}) == "sshd"

    def test_sem_nada_nao_rebenta(self):
        assert events.unidade_de({}) == "desconhecido"


class TestComandoLeitura:
    def test_pede_json_e_desliga_o_paginador(self):
        """
        PT-PT: Sem `--no-pager` o journalctl abre o `less` e o processo fica a
               espera de uma tecla que nunca chega.
        EN-UK: Without `--no-pager` journalctl opens `less` and waits forever.
        """
        comando = events.comando_leitura(24, True, 3000)
        assert "--no-pager" in comando
        assert "json" in comando

    def test_avisos_alargam_a_prioridade(self):
        com = events.comando_leitura(24, True, 100)
        sem = events.comando_leitura(24, False, 100)
        assert f"0..{events.PRIORIDADE_AVISO}" in com
        assert f"0..{events.PRIORIDADE_ERRO}" in sem

    def test_leva_o_tecto_e_a_janela(self):
        comando = events.comando_leitura(48, True, 500)
        assert "-48h" in comando
        assert "500" in comando

    def test_ambito_de_utilizador_acrescenta_a_opcao(self):
        assert "--user" in events.comando_leitura(24, True, 10, ambito="utilizador")
        assert "--user" not in events.comando_leitura(24, True, 10)

    def test_apenas_este_arranque(self):
        assert "-b" in events.comando_leitura(24, True, 10, apenas_este_arranque=True)


class TestRelatorios:
    def _identificacao(self):
        return {"Máquina": "pc-teste", "Utilizador": "rafael"}

    def test_html_escapa_o_conteudo_do_sistema(self):
        """
        PT-PT: O teste que importa mais deste ficheiro. Mensagens do kernel e do
               udev com sinais de menor e maior sao vulgares, e inseri-las em
               bruto partia o relatorio ou, no pior caso, executava-as.
        EN-UK: The most important test here.
        """
        registos = [registo("<script>alert('x')</script> e <b>negrito</b>")]
        html = reports.relatorio_eventos(
            events.analisar(registos, 24, 3000), self._identificacao()
        )
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_html_escapa_a_identificacao(self):
        html = reports.relatorio_eventos(
            events.analisar([], 24, 3000), {"Máquina": "pc<>teste"}
        )
        assert "pc<>teste" not in html
        assert "pc&lt;&gt;teste" in html

    def test_html_e_um_documento_completo(self):
        html = reports.relatorio_eventos(events.analisar([], 24, 3000), self._identificacao())
        assert html.startswith("<!DOCTYPE html>")
        assert html.rstrip().endswith("</html>")
        assert 'charset="utf-8"' in html

    def test_relatorio_de_saude_ordena_por_gravidade(self):
        achados = [
            Achado("Rede", "Aviso menor", "d", Gravidade.BAIXA),
            Achado("Discos", "Disco a falhar", "d", Gravidade.CRITICA),
        ]
        html = reports.relatorio_saude(achados, self._identificacao())
        assert html.index("Disco a falhar") < html.index("Aviso menor")

    def test_relatorio_de_saude_sem_achados(self):
        assert "Nenhum problema identificado" in reports.relatorio_saude([], self._identificacao())

    def test_inventario_escapa_nomes_de_pacotes(self):
        html = reports.relatorio_inventario(
            {"Modelo": "X"}, {}, [{"nome": "app <beta>"}], [], self._identificacao()
        )
        assert "app <beta>" not in html
        assert "app &lt;beta&gt;" in html

    def test_inventario_mostra_as_actualizacoes(self):
        html = reports.relatorio_inventario(
            {}, {}, [],
            [{"pacote": "openssl", "versao": "3.0.2", "accao": "actualização", "quando": "2026-08-30"}],
            self._identificacao(),
        )
        assert "openssl" in html
        assert "2026-08-30" in html

    def test_nome_seguro_remove_caracteres_proibidos(self):
        assert reports._nome_seguro('sa:ude/re*lat?rio') == "sauderelatrio"
        for proibido in '<>:"/\\|?*':
            assert proibido not in reports._nome_seguro(f"a{proibido}b")

    def test_nome_seguro_troca_espacos_por_underscore(self):
        assert reports._nome_seguro("com espaços") == "com_espaços"

    def test_nome_seguro_limita_o_comprimento(self):
        assert len(reports._nome_seguro("x" * 200)) <= 60

    def test_nome_seguro_nunca_devolve_vazio(self):
        assert reports._nome_seguro("///") == "relatorio"
        assert reports._nome_seguro("") == "relatorio"

    def test_gravar_nunca_sobrepoe(self, tmp_path: Path):
        primeiro = reports.gravar("<html></html>", tmp_path, "saude")
        segundo = reports.gravar("<html></html>", tmp_path, "saude")
        assert primeiro.exists()
        assert segundo.exists()
        assert len(list(tmp_path.glob("*.html"))) == 2

    def test_gravar_cria_a_pasta(self, tmp_path: Path):
        assert reports.gravar("<html></html>", tmp_path / "nova" / "sub", "teste").is_file()

    def test_listar_pasta_inexistente_devolve_vazio(self, tmp_path: Path):
        assert reports.listar_relatorios(tmp_path / "nao-existe") == []

    def test_listar_ordena_do_mais_recente(self, tmp_path: Path):
        import os
        import time

        antigo = tmp_path / "antigo.html"
        antigo.write_text("<html></html>", encoding="utf-8")
        os.utime(antigo, (time.time() - 3600, time.time() - 3600))
        (tmp_path / "recente.html").write_text("<html></html>", encoding="utf-8")

        assert reports.listar_relatorios(tmp_path)[0].name == "recente.html"


class TestConfig:
    def test_valores_por_omissao_sao_validos(self):
        config = AppConfig()
        assert config.periodo_horas == 24
        assert config.tema == "system"

    def test_limites_absurdos_sao_corrigidos(self):
        config = AppConfig(disco_percent_min=900, ram_percent_max=1, max_eventos=10**9)
        assert config.disco_percent_min <= 50
        assert config.ram_percent_max >= 50
        assert config.max_eventos <= 50_000

    def test_periodo_invalido_volta_a_24(self):
        assert AppConfig(periodo_horas=13).periodo_horas == 24

    def test_tema_invalido_volta_a_system(self):
        assert AppConfig(tema="néon").tema == "system"

    def test_ficheiro_corrompido_nao_impede_o_arranque(self, tmp_path: Path):
        mau = tmp_path / "config.json"
        mau.write_text("{isto não é json", encoding="utf-8")
        assert AppConfig.load(mau).periodo_horas == 24

    def test_json_que_nao_e_objecto(self, tmp_path: Path):
        mau = tmp_path / "config.json"
        mau.write_text("[1, 2, 3]", encoding="utf-8")
        assert AppConfig.load(mau).periodo_horas == 24

    def test_tipo_errado_num_campo_nao_rebenta(self, tmp_path: Path):
        mau = tmp_path / "config.json"
        mau.write_text(json.dumps({"max_eventos": "muitos"}), encoding="utf-8")
        assert AppConfig.load(mau).max_eventos > 0

    def test_chaves_desconhecidas_sao_ignoradas(self, tmp_path: Path):
        ficheiro = tmp_path / "config.json"
        ficheiro.write_text(json.dumps({"inventada": 1, "periodo_horas": 48}), encoding="utf-8")
        assert AppConfig.load(ficheiro).periodo_horas == 48

    def test_gravar_e_voltar_a_ler(self, tmp_path: Path):
        ficheiro = tmp_path / "config.json"
        original = AppConfig(periodo_horas=168, incluir_utilizador=True)
        assert original.save(ficheiro) is True
        lido = AppConfig.load(ficheiro)
        assert lido.periodo_horas == 168
        assert lido.incluir_utilizador is True

    def test_diarios_escolhidos_respeita_as_opcoes(self):
        assert AppConfig(incluir_sistema=True, incluir_utilizador=False).diarios_escolhidos == ["sistema"]
        assert AppConfig(incluir_sistema=False, incluir_utilizador=True).diarios_escolhidos == ["utilizador"]
        assert AppConfig(incluir_sistema=False, incluir_utilizador=False).diarios_escolhidos == []

    def test_config_nao_escreve_dentro_do_repositorio(self):
        """
        PT-PT: A configuracao vai para o `~/.config`, nunca para a pasta do
               codigo — um `git status` sujo depois de abrir a aplicacao e um
               convite a cometer o ficheiro por engano.
        EN-UK: Configuration goes to `~/.config`, never the code folder.
        """
        caminho = AppConfig.config_path()
        raiz = Path(__file__).resolve().parent.parent
        assert raiz not in caminho.parents


class TestParticao:
    def test_percentagens(self):
        parte = disks.Particao("/", "ext4", total_gb=100.0, livre_gb=25.0)
        assert parte.usado_gb == 75.0
        assert parte.percent_livre == 25.0
        assert parte.percent_usado == 75.0

    def test_disco_de_tamanho_zero_nao_divide_por_zero(self):
        assert disks.Particao("/x", "ext4", 0.0, 0.0).percent_livre == 0.0

    def test_volume_so_de_leitura_nao_gera_alerta(self):
        """
        PT-PT: Uma imagem so de leitura esta sempre a 0% livre e nunca e um
               problema. Alertar sobre ela ensina o operador a ignorar a seccao.
        EN-UK: A read-only image always sits at 0% free and is never a problem.
        """
        parte = disks.Particao("/mnt/iso", "iso9660", 4.0, 0.0, so_leitura=True)
        assert parte.percent_livre == 0.0
        assert parte.so_leitura is True


class TestMontagensRelevantes:
    """
    PT-PT: A funcao que decide o que entra no relatorio de espaco. Cada caso
           aqui apareceu como falso alarme antes de existir esta filtragem.
    EN-UK: The function deciding what enters the space report.
    """

    def test_um_disco_normal_conta(self):
        assert disks.relevante("ext4", "/") is True
        assert disks.relevante("xfs", "/home") is True
        assert disks.relevante("btrfs", "/dados") is True

    def test_snap_nao_conta(self):
        """
        PT-PT: Cada snap e um squashfs a 100% de ocupacao por definicao. Numa
               Ubuntu com quinze snaps, isto dava quinze avisos criticos.
        EN-UK: Every snap is a squashfs at 100% used by definition.
        """
        assert disks.relevante("squashfs", "/snap/firefox/1234") is False

    def test_tmpfs_nao_conta(self):
        assert disks.relevante("tmpfs", "/run/user/1000") is False
        assert disks.relevante("devtmpfs", "/dev") is False

    def test_overlay_de_contentor_nao_conta(self):
        assert disks.relevante("overlay", "/var/lib/docker/overlay2/abc") is False


class TestRedeAuxiliares:
    def test_deteccao_de_link_local(self):
        assert network._e_apipa("169.254.10.5") is True
        assert network._e_apipa("192.0.2.10") is False
        assert network._e_apipa("") is False
        assert network._e_apipa("não é um endereço") is False

    def test_interfaces_virtuais_sao_ignoradas(self):
        """
        PT-PT: Uma ponte do Docker nao ter gateway e o normal. Alertar sobre
               isso numa maquina de programador enchia o relatorio de ruido.
        EN-UK: A Docker bridge having no gateway is normal.
        """
        assert network.ignorar_interface("docker0") is True
        assert network.ignorar_interface("br-1a2b3c") is True
        assert network.ignorar_interface("virbr0") is True
        assert network.ignorar_interface("lo") is True
        assert network.ignorar_interface("enp0s3") is False
        assert network.ignorar_interface("wlan0") is False


class TestServicos:
    def test_ruido_conhecido_esta_na_lista(self):
        assert "systemd-tmpfiles-setup.service" in services.ARRANQUE_TARDIO
        assert "man-db.service" in services.ARRANQUE_TARDIO

    def test_nome_de_unidade_valido(self):
        assert services._nome_valido("nginx.service") is True
        assert services._nome_valido("getty@tty1.service") is True

    def test_nome_de_unidade_com_caracteres_estranhos_e_recusado(self):
        assert services._nome_valido("nginx; rm -rf /") is False
        assert services._nome_valido("") is False

    def test_leitura_da_tabela_mantem_a_descricao_com_espacos(self):
        """
        PT-PT: A descricao de uma unidade tem espacos; o nome nunca tem. Dividir
               pela esquerda com um numero fixo de campos e o que impede a
               descricao de ser cortada ao meio.
        EN-UK: A unit's description has spaces; its name never does.
        """
        saida = "nginx.service loaded active running A high performance web server\n"
        linhas = services._ler_tabela(saida, 5)
        assert linhas[0][0] == "nginx.service"
        assert linhas[0][4] == "A high performance web server"

    def test_leitura_da_tabela_tira_o_marcador_de_estado(self):
        linhas = services._ler_tabela("● a.service loaded failed failed Coisa\n", 5)
        assert linhas[0][0] == "a.service"

    def test_leitura_da_tabela_tolera_linhas_curtas(self):
        linhas = services._ler_tabela("a.service loaded\n", 5)
        assert len(linhas[0]) == 5
