"""
PT-PT: Testes da analise do diario, da geracao de relatorios e da configuracao.

       Nenhum destes testes corre um comando, le o diario de uma maquina real ou
       precisa de um Mac. Os registos sao construidos a mao, no formato que o
       `log show --style ndjson` produz, e e por isso que esta suite corre em
       qualquer sitio — incluindo numa maquina de desenvolvimento que nao seja
       um Mac, e num runner de integracao continua.

EN-UK: Tests for log analysis, report generation and configuration.

       None of these tests runs a command, reads a real machine's log or needs a
       Mac. The records are hand-built in the shape `log show --style ndjson`
       produces, which is why this suite runs anywhere.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
from pathlib import Path

from ittoolkit import disks, events, network, reports, services
from ittoolkit.config import AppConfig
from ittoolkit.models import Achado, Gravidade


def registo(mensagem, processo="/usr/libexec/exemplod", tipo="Error",
            instante="2026-08-30 11:02:31.123456+0100"):
    """
    PT-PT: Constroi um registo como o `log show --style ndjson` o devolve.

           O `processImagePath` e um caminho completo, e nao um nome — e assim
           que o macOS o escreve, e um teste que passasse so o nome nao estaria
           a testar o que a maquina entrega.

    EN-UK: Builds a record as `log show --style ndjson` returns it.

           `processImagePath` is a full path, not a name — that is how macOS
           writes it, and a test passing only the name would not be testing what
           the machine delivers.
    """
    return {
        "eventMessage": mensagem,
        "processImagePath": processo,
        "messageType": tipo,
        "timestamp": instante,
        "subsystem": "",
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
        a = events.assinatura("exemplod[1234]: falhou")
        b = events.assinatura("exemplod[9876]: falhou")
        assert a == b

    def test_uuid_diferente_da_a_mesma_assinatura(self):
        """
        PT-PT: O macOS mete UUID em quase tudo. Sem os normalizar, cada
               ocorrencia de um problema conta como um problema novo.
        EN-UK: macOS puts UUIDs in nearly everything.
        """
        a = events.assinatura("session 3F2504E0-4F89-11D3-9A0C-0305E82C3301 failed")
        b = events.assinatura("session 7B1A93C2-11AA-4D6E-8B22-9F0E71C4A5D9 failed")
        assert a == b

    def test_endereco_de_memoria_diferente_da_a_mesma_assinatura(self):
        a = events.assinatura("EXC_BAD_ACCESS at 0x7f3a2b")
        b = events.assinatura("EXC_BAD_ACCESS at 0x1122ff")
        assert a == b

    def test_pasta_pessoal_e_normalizada(self):
        """
        PT-PT: O mesmo erro em dois Macs so difere no nome do utilizador. Num
               relatorio de parque, contam como um.
        EN-UK: The same error on two Macs differs only in the user's name.
        """
        a = events.assinatura("cannot open /Users/rafael/Documents/x")
        b = events.assinatura("cannot open /Users/maria/Documents/x")
        assert a == b

    def test_mensagens_realmente_diferentes_nao_se_juntam(self):
        a = events.assinatura("Sandbox: deny file-read")
        b = events.assinatura("I/O error on disk0s2")
        assert a != b

    def test_assinatura_e_limitada_em_comprimento(self):
        assert len(events.assinatura("palavra " * 200)) <= events.MAX_MENSAGEM


class TestAnalise:
    def test_agrupa_ocorrencias_iguais(self):
        registos = [registo("exemplod[100]: erro"), registo("exemplod[200]: erro")]
        analise = events.analisar(registos, 24, 3000)
        assert len(analise.problemas) + len(analise.outros) == 1
        assert (analise.problemas + analise.outros)[0].contagem == 2

    def test_separa_a_mesma_mensagem_de_processos_diferentes(self):
        """
        PT-PT: O mesmo texto vindo de dois processos sao dois problemas. Um
               «connection refused» do Mail e um do Safari nao se resolvem no
               mesmo sitio.
        EN-UK: The same text from two processes is two problems.
        """
        registos = [
            registo("connection refused", processo="/Applications/Mail.app/Contents/MacOS/Mail"),
            registo("connection refused", processo="/usr/libexec/trustd"),
        ]
        analise = events.analisar(registos, 24, 3000)
        assert len(analise.problemas) + len(analise.outros) == 2

    def test_o_grupo_fica_com_o_tipo_mais_grave(self):
        """
        PT-PT: Um processo que regista noventa vezes e falha uma e um problema,
               nao um registo. Ordenar pelo registo enterrava-o no fim da lista.
        EN-UK: A process logging ninety times and faulting once is a problem.
        """
        registos = [
            registo("exemplod[1]: coisa", tipo="Default"),
            registo("exemplod[2]: coisa", tipo="Fault"),
            registo("exemplod[3]: coisa", tipo="Default"),
        ]
        grupo = (lambda a: (a.problemas + a.outros)[0])(events.analisar(registos, 24, 3000))
        assert grupo.tipo == "Fault"
        assert grupo.contagem == 3
        assert grupo.gravidade is Gravidade.CRITICA

    def test_mensagem_conhecida_vai_para_problemas(self):
        registos = [registo("panic(cpu 0 caller 0xfff): watchdog", processo="/kernel")]
        analise = events.analisar(registos, 24, 3000)
        assert len(analise.problemas) == 1
        assert analise.problemas[0].regra is not None

    def test_mensagem_desconhecida_fica_nos_outros(self):
        analise = events.analisar([registo("uma coisa qualquer sem regra")], 24, 3000)
        assert analise.outros
        assert not analise.problemas

    def test_ruido_conhecido_nao_conta_para_o_veredicto(self):
        """
        PT-PT: As negacoes de sandbox sao centenas por dia num Mac saudavel.
               Conta-las como problemas tornaria o veredicto inutil.
        EN-UK: Sandbox denials number in the hundreds a day on a healthy Mac.
        """
        registos = [
            registo("Sandbox: mdworker(123) deny(1) file-read-data", processo="/usr/libexec/sandboxd")
            for _ in range(30)
        ]
        analise = events.analisar(registos, 24, 3000)
        assert analise.acionaveis == []
        assert "Nenhum problema conhecido" in analise.veredicto

    def test_primeiro_e_ultimo_por_comparacao_de_datas(self):
        registos = [
            registo("exemplod[1]: x", instante="2026-08-30 18:00:00.000000+0100"),
            registo("exemplod[2]: x", instante="2026-08-30 09:00:00.000000+0100"),
        ]
        grupo = (lambda a: (a.problemas + a.outros)[0])(events.analisar(registos, 24, 3000))
        assert grupo.primeiro < grupo.ultimo

    def test_registo_sem_mensagem_e_ignorado(self):
        assert events.analisar([{"processImagePath": "/x"}], 24, 3000).total == 0

    def test_tipo_desconhecido_nao_rebenta(self):
        mau = registo("x")
        mau["messageType"] = "Inventado"
        analise = events.analisar([mau], 24, 3000)
        assert analise.total == 1
        assert (analise.problemas + analise.outros)[0].nivel_texto == "?"

    def test_truncagem_e_declarada(self):
        registos = [registo(f"mensagem {i}") for i in range(10)]
        assert events.analisar(registos, 24, 10).truncado is True

    def test_mensagem_longa_e_cortada(self):
        analise = events.analisar([registo("a" * 900)], 24, 3000)
        assert len((analise.problemas + analise.outros)[0].exemplo) <= events.MAX_MENSAGEM + 10

    def test_mensagem_multilinha_fica_numa_linha(self):
        analise = events.analisar([registo("linha um\nlinha dois\tterceira")], 24, 3000)
        exemplo = (analise.problemas + analise.outros)[0].exemplo
        assert "\n" not in exemplo
        assert "\t" not in exemplo

    def test_veredicto_sem_registos(self):
        assert "Sem eventos" in events.analisar([], 24, 3000).veredicto


class TestProcessoDe:
    def test_tira_o_caminho_e_deixa_o_nome(self):
        """
        PT-PT: O `/usr/libexec/nehelper` interessa como `nehelper`. Guardar o
               caminho inteiro faz a mesma coisa parecer diferente conforme a
               versao do macOS a tenha movido de sitio.
        EN-UK: `/usr/libexec/nehelper` matters as `nehelper`.
        """
        assert events.processo_de({"processImagePath": "/usr/libexec/nehelper"}) == "nehelper"

    def test_usa_o_emissor_quando_nao_ha_processo(self):
        assert events.processo_de({"senderImagePath": "/kernel"}) == "kernel"

    def test_sem_nada_nao_rebenta(self):
        assert events.processo_de({}) == "desconhecido"


class TestComandoLeitura:
    def test_pede_ndjson_e_limita_a_janela(self):
        """
        PT-PT: Sem `--last`, o `log show` percorre o arquivo inteiro e demora
               minutos antes de escrever a primeira linha.
        EN-UK: Without `--last`, `log show` walks the whole archive.
        """
        comando = events.comando_leitura(24, False, 3000)
        assert "ndjson" in comando
        assert "24h" in comando

    def test_predicado_restringe_do_lado_do_sistema(self):
        """
        PT-PT: Filtrar depois de receber e receber tudo — e num Mac isso sao
               dezenas de milhares de linhas por hora.
        EN-UK: Filtering after receiving means receiving everything.
        """
        comando = events.comando_leitura(24, False, 3000)
        assert events.PREDICADO in comando

    def test_avisos_alargam_o_predicado(self):
        com = events.comando_leitura(24, True, 100)
        assert events.PREDICADO_COM_AVISOS in com
        assert "Default" in events.PREDICADO_COM_AVISOS


class TestRelatoriosDeParagem:
    """
    PT-PT: Os relatorios de paragem sao ficheiros e nao linhas de diario, e e
           por isso que sobrevivem ao reinicio que levou o diario. Estes testes
           usam uma pasta temporaria, e nao a do sistema.
    EN-UK: Crash reports are files rather than log lines, which is why they
           survive the reboot that took the log with it.
    """

    def test_encontra_os_recentes(self, tmp_path: Path):
        (tmp_path / "Safari_2026-08-30-110231_Mac.ips").write_text("{}", encoding="utf-8")
        (tmp_path / "Kernel_2026-08-30-110231_Mac.panic").write_text("{}", encoding="utf-8")
        encontrados = events.relatorios_de_paragem(dias=7, pastas=(tmp_path,))
        assert len(encontrados) == 2
        assert {e["nome"] for e in encontrados} == {"Safari", "Kernel"}

    def test_ignora_ficheiros_que_nao_sao_relatorios(self, tmp_path: Path):
        (tmp_path / "leia-me.txt").write_text("x", encoding="utf-8")
        assert events.relatorios_de_paragem(dias=7, pastas=(tmp_path,)) == []

    def test_ignora_os_antigos(self, tmp_path: Path):
        import os
        import time

        antigo = tmp_path / "Safari_2020.ips"
        antigo.write_text("{}", encoding="utf-8")
        ha_muito = time.time() - 60 * 86400
        os.utime(antigo, (ha_muito, ha_muito))
        assert events.relatorios_de_paragem(dias=7, pastas=(tmp_path,)) == []

    def test_pasta_inexistente_nao_rebenta(self, tmp_path: Path):
        assert events.relatorios_de_paragem(dias=7, pastas=(tmp_path / "nao-existe",)) == []


class TestRelatorios:
    def _identificacao(self):
        return {"Máquina": "mac-teste", "Utilizador": "rafael"}

    def test_html_escapa_o_conteudo_do_sistema(self):
        """
        PT-PT: O teste que importa mais deste ficheiro. As negacoes de sandbox
               trazem descritores entre parenteses angulares, e inseri-los em
               bruto partia o relatorio ou, no pior caso, executava-os.
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
            events.analisar([], 24, 3000), {"Máquina": "mac<>teste"}
        )
        assert "mac<>teste" not in html
        assert "mac&lt;&gt;teste" in html

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

    def test_inventario_escapa_nomes_de_aplicacoes(self):
        html = reports.relatorio_inventario(
            {"Modelo": "X"}, {}, [{"nome": "app <beta>"}], [], self._identificacao()
        )
        assert "app <beta>" not in html
        assert "app &lt;beta&gt;" in html

    def test_nome_seguro_remove_os_dois_pontos(self):
        """
        PT-PT: O Finder mostra os dois-pontos como barras. Um relatório chamado
               `saude:2026` aparece como `saude/2026` e ninguém o encontra.
        EN-UK: Finder shows colons as slashes.
        """
        assert ":" not in reports._nome_seguro("saude:2026")

    def test_nome_seguro_remove_caracteres_proibidos(self):
        assert reports._nome_seguro('sa:ude/re*lat?rio') == "sauderelatrio"

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
        original = AppConfig(periodo_horas=168, incluir_relatorios_paragem=False)
        assert original.save(ficheiro) is True
        lido = AppConfig.load(ficheiro)
        assert lido.periodo_horas == 168
        assert lido.incluir_relatorios_paragem is False

    def test_fontes_escolhidas_respeita_as_opcoes(self):
        assert "relatórios de paragem" in AppConfig(incluir_relatorios_paragem=True).fontes_escolhidas
        assert "relatórios de paragem" not in AppConfig(
            incluir_relatorios_paragem=False
        ).fontes_escolhidas

    def test_o_diario_esta_sempre_na_lista(self):
        """
        PT-PT: Num Mac ha um diario unico e nao ha nada para escolher dentro
               dele. Desligar tudo deixaria a analise sem fonte nenhuma.
        EN-UK: On a Mac there is a single log and nothing to choose inside it.
        """
        assert "diário" in AppConfig(incluir_relatorios_paragem=False).fontes_escolhidas

    def test_config_nao_escreve_dentro_do_repositorio(self):
        caminho = AppConfig.config_path()
        raiz = Path(__file__).resolve().parent.parent
        assert raiz not in caminho.parents


class TestParticao:
    def test_percentagens(self):
        parte = disks.Particao("/", "apfs", total_gb=100.0, livre_gb=25.0)
        assert parte.usado_gb == 75.0
        assert parte.percent_livre == 25.0
        assert parte.percent_usado == 75.0

    def test_disco_de_tamanho_zero_nao_divide_por_zero(self):
        assert disks.Particao("/x", "apfs", 0.0, 0.0).percent_livre == 0.0

    def test_volume_selado_de_sistema_e_so_de_leitura(self):
        """
        PT-PT: O volume de sistema de um macOS moderno está sempre a 0% livre e
               nunca é um problema: é uma imagem selada e assinada.
        EN-UK: A modern macOS's system volume always sits at 0% free.
        """
        parte = disks.Particao("/", "apfs", 20.0, 0.0, so_leitura=True)
        assert parte.percent_livre == 0.0
        assert parte.so_leitura is True


class TestVolumesRelevantes:
    """
    PT-PT: A funcao que decide o que entra no relatorio de espaco. Cada caso
           aqui apareceu como falso alarme antes de existir esta filtragem.
    EN-UK: The function deciding what enters the space report.
    """

    def test_um_volume_normal_conta(self):
        assert disks.relevante("apfs", "/") is True
        assert disks.relevante("apfs", "/System/Volumes/Data") is True
        assert disks.relevante("hfs", "/Volumes/Externo") is True

    def test_volumes_internos_do_apfs_nao_contam(self):
        """
        PT-PT: O Preboot, o VM e o Recovery sao geridos pelo sistema e o
               utilizador nao pode fazer nada sobre eles.
        EN-UK: Preboot, VM and Recovery are system-managed.
        """
        assert disks.relevante("apfs", "/System/Volumes/Preboot") is False
        assert disks.relevante("apfs", "/System/Volumes/VM") is False

    def test_devfs_nao_conta(self):
        assert disks.relevante("devfs", "/dev") is False
        assert disks.relevante("autofs", "/net") is False


class TestRedeAuxiliares:
    def test_deteccao_de_endereco_self_assigned(self):
        assert network._e_apipa("169.254.10.5") is True
        assert network._e_apipa("192.0.2.10") is False
        assert network._e_apipa("") is False
        assert network._e_apipa("não é um endereço") is False

    def test_interfaces_de_servico_sao_ignoradas(self):
        """
        PT-PT: O `awdl0` e o AirDrop, o `utun` e uma VPN, o `llw0` e o Low
               Latency WLAN. Nenhum tem gateway, e todos existem em todos os
               Macs — alertar sobre eles seria alertar sempre.
        EN-UK: `awdl0` is AirDrop, `utun` a VPN, `llw0` Low Latency WLAN.
        """
        assert network.ignorar_interface("awdl0") is True
        assert network.ignorar_interface("utun3") is True
        assert network.ignorar_interface("llw0") is True
        assert network.ignorar_interface("bridge0") is True
        assert network.ignorar_interface("lo0") is True
        assert network.ignorar_interface("en0") is False
        assert network.ignorar_interface("en1") is False


class TestServicos:
    def test_ruido_conhecido_esta_na_lista(self):
        assert "com.apple.mbsystemadministration" in services.RUIDO_CONHECIDO

    def test_etiqueta_valida(self):
        assert services._etiqueta_valida("com.apple.mDNSResponder") is True
        assert services._etiqueta_valida("org.cups.cupsd") is True

    def test_etiqueta_com_caracteres_estranhos_e_recusada(self):
        assert services._etiqueta_valida("com.exemplo; rm -rf /") is False
        assert services._etiqueta_valida("") is False

    def test_leitura_da_listagem_salta_o_cabecalho(self):
        saida = "PID\tStatus\tLabel\n123\t0\tcom.apple.exemplo\n"
        linhas = services._ler_listagem(saida)
        assert len(linhas) == 1
        assert linhas[0]["etiqueta"] == "com.apple.exemplo"

    def test_traco_no_codigo_nao_e_zero(self):
        """
        PT-PT: O traco significa «nao ha codigo», e nao «codigo zero». Um
               servico a correr tem traco na coluna do codigo, e trata-lo como
               zero e dizer que terminou bem quando nem sequer terminou.
        EN-UK: The dash means "no code", not "code zero".
        """
        assert services._numero("-") is None
        assert services._numero("0") == 0
        assert services._numero("78") == 78

    def test_a_coluna_do_codigo_e_a_que_identifica_a_falha(self):
        """
        PT-PT: E a unica forma de o launchd dizer que um servico falhou. Ler mal
               esta coluna e nao ver falha nenhuma numa maquina cheia delas.
        EN-UK: It is launchd's only way of saying a service failed.
        """
        saida = (
            "PID\tStatus\tLabel\n"
            "123\t-\tcom.apple.a.correr\n"
            "-\t0\tcom.apple.saiu.bem\n"
            "-\t78\tcom.apple.falhou\n"
        )
        entradas = services._ler_listagem(saida)
        falhadas = [e for e in entradas if services._numero(e["codigo"]) not in (None, 0)]
        assert len(falhadas) == 1
        assert falhadas[0]["etiqueta"] == "com.apple.falhou"
