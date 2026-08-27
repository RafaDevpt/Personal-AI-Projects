# -*- coding: utf-8 -*-
"""
PT-PT: Testes da analise de eventos, da geracao de relatorios e da configuracao.
       Nenhum destes testes toca no Windows nem le event logs reais.
EN-UK: Tests for event analysis, report generation and configuration. None of
       these tests touch Windows or read real event logs.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ittoolkit import events, reports
from ittoolkit.config import AppConfig
from ittoolkit.models import Achado, Gravidade
from ittoolkit.shell import normalizar_json


def registo(event_id, provider, nivel=2, quando="2026-08-27 10:00:00", mensagem="ok"):
    """PT-PT: Constroi um registo como o PowerShell o devolve.
    EN-UK: Builds a record as PowerShell returns it."""
    return {
        "Id": event_id,
        "ProviderName": provider,
        "Level": nivel,
        "Quando": quando,
        "Mensagem": mensagem,
    }


class TestAnalise:
    def test_agrupa_ocorrencias_iguais(self):
        """PT-PT: Cinquenta linhas iguais sao um problema, nao cinquenta.
        EN-UK: Fifty identical lines are one problem, not fifty."""
        registos = [registo(41, "Kernel-Power", nivel=1) for _ in range(50)]
        analise = events.analisar({"System": registos}, 24, 3000)

        assert analise.total == 50
        assert len(analise.problemas) == 1
        assert analise.problemas[0].contagem == 50

    def test_separa_o_mesmo_id_de_providers_diferentes(self):
        registos = [registo(1000, "Application Error"), registo(1000, "MSSQLSERVER")]
        analise = events.analisar({"Application": registos}, 24, 3000)
        todos = analise.problemas + analise.outros
        assert len(todos) == 2

    def test_ordena_por_gravidade(self):
        registos = [
            registo(10016, "DistributedCOM"),
            registo(41, "Kernel-Power", nivel=1),
            registo(7000, "Service Control Manager"),
        ]
        analise = events.analisar({"System": registos}, 24, 3000)
        assert analise.problemas[0].event_id == 41

    def test_evento_desconhecido_e_recorrente_sobe_a_problemas(self):
        """
        PT-PT: Nao ter entrada na base nao torna um evento inofensivo.
        EN-UK: Having no knowledge-base entry does not make an event harmless.
        """
        registos = [registo(9999, "Fornecedor Qualquer", nivel=2) for _ in range(8)]
        analise = events.analisar({"Application": registos}, 24, 3000)
        assert len(analise.problemas) == 1
        assert analise.problemas[0].event_id == 9999
        assert analise.problemas[0].regra is None

    def test_evento_desconhecido_isolado_fica_nos_outros(self):
        analise = events.analisar({"Application": [registo(9999, "X")]}, 24, 3000)
        assert analise.problemas == []
        assert len(analise.outros) == 1

    def test_primeiro_e_ultimo_por_comparacao_de_datas(self):
        """
        PT-PT: A ordem em que os registos chegam nao pode determinar as colunas.
        EN-UK: The order records arrive in must not determine the columns.
        """
        registos = [
            registo(41, "Kernel-Power", nivel=1, quando="2026-08-27 18:00:00"),
            registo(41, "Kernel-Power", nivel=1, quando="2026-08-27 06:00:00"),
            registo(41, "Kernel-Power", nivel=1, quando="2026-08-27 12:00:00"),
        ]
        grupo = events.analisar({"System": registos}, 24, 3000).problemas[0]
        assert grupo.primeiro == "2026-08-27 06:00:00"
        assert grupo.ultimo == "2026-08-27 18:00:00"

    def test_id_invalido_e_ignorado_sem_rebentar(self):
        """
        PT-PT: A v1.0 morria com TypeError a meio da analise.
        EN-UK: v1.0 died with a TypeError halfway through.
        """
        registos = [registo(41, "Kernel-Power", nivel=1), {"Id": None}, {"Id": "abc"}]
        analise = events.analisar({"System": registos}, 24, 3000)
        assert analise.total == 1

    def test_id_em_texto_e_aceite(self):
        analise = events.analisar({"System": [registo("41", "Kernel-Power", nivel=1)]}, 24, 3000)
        assert analise.problemas[0].event_id == 41

    def test_truncagem_e_declarada(self):
        """
        PT-PT: Um relatorio incompleto tem de o dizer.
        EN-UK: An incomplete report has to say so.
        """
        registos = [registo(7000, "Service Control Manager") for _ in range(10)]
        analise = events.analisar({"System": registos}, 24, 10)
        assert analise.truncado is True
        assert any("limite" in aviso for aviso in analise.avisos)

    def test_sem_truncagem_nao_ha_aviso(self):
        registos = [registo(7000, "Service Control Manager") for _ in range(3)]
        analise = events.analisar({"System": registos}, 24, 3000)
        assert analise.truncado is False
        assert analise.avisos == []

    def test_mensagem_longa_e_cortada(self):
        longa = "x" * 5000
        registos = [registo(41, "Kernel-Power", nivel=1, mensagem=longa)]
        grupo = events.analisar({"System": registos}, 24, 3000).problemas[0]
        assert len(grupo.exemplo) < events.MAX_MENSAGEM + 20

    def test_mensagem_multilinha_fica_numa_linha(self):
        registos = [registo(41, "Kernel-Power", nivel=1, mensagem="linha um\n\n  linha dois")]
        grupo = events.analisar({"System": registos}, 24, 3000).problemas[0]
        assert grupo.exemplo == "linha um linha dois"


class TestComandoLeitura:
    def test_pede_filtro_do_lado_do_servico(self):
        comando = events._comando_leitura("System", 24, [1, 2, 3], 3000)
        assert "FilterHashtable" in comando
        assert "Get-EventLog" not in comando

    def test_silencia_o_erro_de_log_vazio(self):
        """
        PT-PT: Sem isto, «sem erros nas ultimas 24h» aparecia como falha.
        EN-UK: Without this, "no errors in 24h" looked like a failure.
        """
        assert "-ErrorAction SilentlyContinue" in events._comando_leitura("System", 24, [2], 100)

    def test_leva_o_tecto_de_eventos(self):
        assert "-MaxEvents 500" in events._comando_leitura("System", 24, [2], 500)


class TestRelatorios:
    def _identificacao(self):
        return {"Máquina": "PC-TESTE", "Utilizador": "rafael"}

    def test_html_escapa_o_conteudo_do_windows(self):
        """
        PT-PT: O teste que importa mais deste ficheiro. Mensagens de eventos com
               sinais de menor e maior sao vulgares, e insere-las em bruto
               partia o relatorio ou, no pior caso, executava-as.
        EN-UK: The most important test here. Event messages containing angle
               brackets are commonplace; inserting them raw broke the report or,
               at worst, executed them.
        """
        registos = [
            registo(
                41, "Kernel-Power", nivel=1,
                mensagem="<script>alert('x')</script> e <b>negrito</b>",
            )
        ]
        analise = events.analisar({"System": registos}, 24, 3000)
        html = reports.relatorio_eventos(analise, self._identificacao())

        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_html_escapa_a_identificacao(self):
        html = reports.relatorio_eventos(
            events.analisar({}, 24, 3000), {"Máquina": "PC<>TESTE"}
        )
        assert "PC<>TESTE" not in html
        assert "PC&lt;&gt;TESTE" in html

    def test_html_e_um_documento_completo(self):
        html = reports.relatorio_eventos(events.analisar({}, 24, 3000), self._identificacao())
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
        html = reports.relatorio_saude([], self._identificacao())
        assert "Nenhum problema identificado" in html

    def test_inventario_escapa_nomes_de_software(self):
        html = reports.relatorio_inventario(
            {"Modelo": "X"}, {}, [{"DisplayName": "App <beta>"}], [], self._identificacao()
        )
        assert "App <beta>" not in html
        assert "App &lt;beta&gt;" in html

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
        """
        PT-PT: Duas analises seguidas nao podem perder a primeira.
        EN-UK: Two analyses in a row must not lose the first.
        """
        primeiro = reports.gravar("<html></html>", tmp_path, "saude")
        segundo = reports.gravar("<html></html>", tmp_path, "saude")
        assert primeiro.exists()
        assert segundo.exists()
        assert len(list(tmp_path.glob("*.html"))) == 2

    def test_gravar_cria_a_pasta(self, tmp_path: Path):
        destino = tmp_path / "nova" / "sub"
        ficheiro = reports.gravar("<html></html>", destino, "teste")
        assert ficheiro.is_file()

    def test_listar_pasta_inexistente_devolve_vazio(self, tmp_path: Path):
        assert reports.listar_relatorios(tmp_path / "nao-existe") == []

    def test_listar_ordena_do_mais_recente(self, tmp_path: Path):
        import os
        import time

        antigo = tmp_path / "antigo.html"
        antigo.write_text("<html></html>", encoding="utf-8")
        os.utime(antigo, (time.time() - 3600, time.time() - 3600))
        recente = tmp_path / "recente.html"
        recente.write_text("<html></html>", encoding="utf-8")

        assert reports.listar_relatorios(tmp_path)[0].name == "recente.html"


class TestNormalizarJson:
    """PT-PT: Os tres formatos que o ConvertTo-Json produz.
    EN-UK: The three shapes ConvertTo-Json produces."""

    def test_lista_fica_como_esta(self):
        assert normalizar_json([{"a": 1}, {"a": 2}]) == [{"a": 1}, {"a": 2}]

    def test_objecto_unico_e_embrulhado(self):
        assert normalizar_json({"a": 1}) == [{"a": 1}]

    def test_escalar_vira_dicionario(self):
        """PT-PT: O caso que faltava na v1.0 — um único servidor DNS.
        EN-UK: The case v1.0 missed — a single DNS server."""
        assert normalizar_json("10.0.0.1") == [{"valor": "10.0.0.1"}]

    def test_lista_de_escalares(self):
        assert normalizar_json(["a", "b"]) == [{"valor": "a"}, {"valor": "b"}]

    def test_none_devolve_lista_vazia(self):
        assert normalizar_json(None) == []


class TestConfig:
    def test_valores_por_omissao_sao_validos(self):
        config = AppConfig()
        assert config.periodo_horas == 24
        assert config.logs_escolhidos == ["System", "Application"]

    def test_limites_absurdos_sao_corrigidos(self):
        config = AppConfig(disco_percent_min=900, uptime_dias_max=0, ram_percent_max=5)
        assert config.disco_percent_min == 50
        assert config.uptime_dias_max == 1
        assert config.ram_percent_max == 50

    def test_periodo_invalido_volta_a_24(self):
        assert AppConfig(periodo_horas=13).periodo_horas == 24

    def test_tema_invalido_volta_a_system(self):
        assert AppConfig(tema="arco-íris").tema == "system"

    def test_ficheiro_corrompido_nao_impede_o_arranque(self, tmp_path: Path):
        caminho = tmp_path / "config.json"
        caminho.write_text("{isto não é json", encoding="utf-8")
        assert AppConfig.load(caminho).periodo_horas == 24

    def test_json_que_nao_e_objecto(self, tmp_path: Path):
        caminho = tmp_path / "config.json"
        caminho.write_text("[1, 2, 3]", encoding="utf-8")
        assert AppConfig.load(caminho).tema == "system"

    def test_tipo_errado_num_campo_nao_rebenta(self, tmp_path: Path):
        caminho = tmp_path / "config.json"
        caminho.write_text(json.dumps({"max_eventos": "muitos"}), encoding="utf-8")
        assert AppConfig.load(caminho).max_eventos == 3000

    def test_chaves_desconhecidas_sao_ignoradas(self, tmp_path: Path):
        caminho = tmp_path / "config.json"
        caminho.write_text(json.dumps({"opcao_de_outra_versao": True}), encoding="utf-8")
        assert AppConfig.load(caminho).periodo_horas == 24

    def test_gravar_e_voltar_a_ler(self, tmp_path: Path):
        caminho = tmp_path / "config.json"
        original = AppConfig(periodo_horas=168, disco_gb_min=30, tema="dark")
        assert original.save(caminho)

        lida = AppConfig.load(caminho)
        assert lida.periodo_horas == 168
        assert lida.disco_gb_min == 30
        assert lida.tema == "dark"

    def test_logs_escolhidos_respeita_as_opcoes(self):
        config = AppConfig(incluir_application=False, incluir_security=True)
        assert config.logs_escolhidos == ["System", "Security"]

    def test_config_nao_escreve_dentro_do_repositorio(self):
        """
        PT-PT: Os relatorios contem nome da maquina, utilizador e numero de
               serie. Se a pasta ficasse dentro do repositorio, um `git add .`
               levava-os para o GitHub.
        EN-UK: Reports carry machine name, user and serial. If the folder sat
               inside the repository, a `git add .` would push them to GitHub.
        """
        config = AppConfig()
        raiz = Path(__file__).resolve().parent.parent
        assert raiz not in config.reports_dir.resolve().parents
        assert raiz not in AppConfig.config_path().resolve().parents


class TestParticao:
    def test_percentagens(self):
        from ittoolkit.disks import Particao

        parte = Particao(montagem="C:\\", sistema="NTFS", total_gb=100.0, livre_gb=25.0)
        assert parte.percent_livre == pytest.approx(25.0)
        assert parte.percent_usado == pytest.approx(75.0)
        assert parte.usado_gb == pytest.approx(75.0)

    def test_disco_de_tamanho_zero_nao_divide_por_zero(self):
        from ittoolkit.disks import Particao

        parte = Particao(montagem="X:\\", sistema="?", total_gb=0.0, livre_gb=0.0)
        assert parte.percent_livre == 0.0

    def test_volume_so_de_leitura_nao_gera_alerta(self, monkeypatch=None):
        """
        PT-PT: Uma ISO montada esta sempre a 0% livre e nunca e um problema.
               Sem esta excepcao, o relatorio abria com alertas críticos falsos
               e o operador aprendia a ignorar a secção dos discos.
        EN-UK: A mounted ISO always sits at 0% free and is never a problem.
        """
        from ittoolkit import disks
        from ittoolkit.disks import Particao

        original = disks.particoes
        disks.particoes = lambda: [
            Particao("D:\\", "UDF", 4.7, 0.0, so_leitura=True),
            Particao("C:\\", "NTFS", 120.0, 3.0),
        ]
        try:
            achados = disks.achados(percent_min=10, gb_min=15)
        finally:
            disks.particoes = original

        montagens = [a.titulo for a in achados]
        assert not any("D:" in t for t in montagens)
        assert any("C:" in t for t in montagens)


class TestRedeAuxiliares:
    def test_deteccao_de_apipa(self):
        from ittoolkit.network import _e_apipa

        assert _e_apipa("169.254.10.5") is True
        assert _e_apipa("10.162.84.20") is False
        assert _e_apipa("não é um ip") is False


class TestServicos:
    def test_ruido_conhecido_esta_na_lista(self):
        from ittoolkit.services import ARRANQUE_TARDIO

        assert "sppsvc" in ARRANQUE_TARDIO
        assert "wuauserv" in ARRANQUE_TARDIO

    def test_nome_de_servico_com_caracteres_estranhos_e_recusado(self):
        """
        PT-PT: O nome entra numa string de comando. Sem validacao, um nome com
               ponto e virgula executava outra coisa qualquer.
        EN-UK: The name goes into a command string. Without validation, a name
               with a semicolon would run something else entirely.
        """
        from ittoolkit.services import arrancar

        resultado = arrancar("Spooler; Remove-Item C:\\ -Recurse")
        assert not resultado.ok
        assert "inválido" in resultado.erro
