#!/usr/bin/env python3
"""
PT-PT: Testes do modo de texto.

       O que se testa aqui é o contrato com quem automatiza: **o código de
       saída** e **as chaves do JSON**. As duas coisas que, se mudarem sem
       aviso, partem o script de alguém em silêncio.

       Testa-se também que o modo de texto não oferece operações de escrita.
       Não é uma limitação a documentar: é uma decisão, e uma decisão vale um
       teste que falhe se alguém a inverter por conveniência.

EN-UK: Text-mode tests.

       What is tested here is the contract with whoever automates: **the exit
       code** and **the JSON keys**. The two things that, changed without
       warning, break somebody's script silently.

       It is also tested that text mode offers no write operations. That is not
       a limitation to document: it is a decision, and a decision is worth a
       test that fails if somebody reverses it for convenience.

Created by Redfox using Claude
"""

from __future__ import annotations

import json

from vfc import cli, health
from vfc.models import Finding, Severity


class TestCodigoDeSaida:
    """PT-PT: O que a automação lê. / EN-UK: What automation reads."""

    def test_sem_achados(self) -> None:
        assert cli.exit_code_for([]) == cli.EXIT_OK

    def test_so_informacao(self) -> None:
        achados = [Finding(Severity.INFO, "x", "y")]
        assert cli.exit_code_for(achados) == cli.EXIT_OK

    def test_com_avisos(self) -> None:
        achados = [Finding(Severity.INFO, "x", "y"), Finding(Severity.WARNING, "x", "y")]
        assert cli.exit_code_for(achados) == cli.EXIT_WARNING

    def test_o_pior_manda(self) -> None:
        achados = [
            Finding(Severity.WARNING, "x", "y"),
            Finding(Severity.CRITICAL, "x", "y"),
            Finding(Severity.INFO, "x", "y"),
        ]
        assert cli.exit_code_for(achados) == cli.EXIT_CRITICAL

    def test_inacessivel_e_um_codigo_distinto(self) -> None:
        # PT-PT: Não conseguir ligar não é a mesma coisa que estar tudo mal. É a
        #        distinção que evita acordar alguém por causa de um cabo.
        # EN-UK: Failing to connect is not the same as everything being wrong.
        #        It is the distinction that avoids waking somebody over a cable.
        assert cli.EXIT_UNREACHABLE not in (cli.EXIT_OK, cli.EXIT_WARNING, cli.EXIT_CRITICAL)


class TestRelatorioEmTexto:
    def test_o_resumo_diz_a_hora_da_recolha(self, parque) -> None:
        # PT-PT: Um relatório sem hora é comparado com a realidade de agora sem
        #        se saber que é de há uma hora.
        # EN-UK: A report with no timestamp gets compared against now without
        #        anybody knowing it is an hour old.
        texto = cli.render_summary(parque, [])
        assert "Recolhido em" in texto

    def test_o_resumo_mostra_o_aviso_de_licenca(self, parque) -> None:
        parque.read_only_reason = "Licença gratuita: a API é só de leitura."
        assert "só de leitura" in cli.render_summary(parque, [])

    def test_sem_achados_diz_que_nao_ha(self) -> None:
        # PT-PT: Uma secção vazia parece uma ferramenta que falhou a correr.
        # EN-UK: An empty section reads like a tool that failed to run.
        texto = cli.render_findings([])
        assert "Nada a apontar" in texto

    def test_os_achados_levam_o_conselho(self) -> None:
        achados = [Finding(Severity.CRITICAL, "DS", "cheio", remedy="apague snapshots")]
        assert "apague snapshots" in cli.render_findings(achados)

    def test_as_tabelas_saem_todas(self, parque, agora) -> None:
        achados = health.evaluate(parque, now=agora)
        relatorio = cli.render_report(parque, achados)
        for esperado in ("ANFITRIÃO", "DATASTORE", "MÁQUINA", "esx01.lab.local", "SRV-APP01"):
            assert esperado in relatorio

    def test_datastores_ordenados_pelo_mais_apertado(self, parque) -> None:
        # PT-PT: O que se procura numa lista de datastores está sempre no fundo
        #        da lista ordenada por nome.
        # EN-UK: What you look for is always at the bottom of a list sorted by
        #        name.
        linhas = cli.render_datastores(parque).splitlines()
        assert "DS-LENTO" in linhas[2]

    def test_snapshots_do_mais_velho_para_o_mais_novo(self, parque) -> None:
        texto = cli.render_snapshots(parque)
        assert "SRV-DC01" in texto

    def test_inventario_vazio_nao_rebenta(self) -> None:
        from vfc.models import Fleet

        vazio = Fleet()
        assert "Nenhum anfitrião" in cli.render_hosts(vazio)
        assert "Nenhum datastore" in cli.render_datastores(vazio)
        assert "Nenhuma máquina" in cli.render_vms(vazio)
        assert "Nenhum snapshot" in cli.render_snapshots(vazio)


class TestJson:
    """PT-PT: O contrato com os scripts. / EN-UK: The contract with scripts."""

    def test_e_json_valido(self, parque, agora) -> None:
        achados = health.evaluate(parque, now=agora)
        dados = json.loads(cli.render_json(parque, achados))
        assert isinstance(dados, dict)

    def test_as_chaves_de_topo(self, parque) -> None:
        # PT-PT: Acrescentar chaves é seguro. Mudar estas parte o script de
        #        alguém sem aviso, e este teste é o que obriga a pensar nisso.
        # EN-UK: Adding keys is safe. Changing these breaks somebody's script
        #        silently, and this test is what forces the thought.
        dados = json.loads(cli.render_json(parque, []))
        assert {
            "endpoint",
            "is_vcenter",
            "collected_at",
            "totals",
            "findings",
            "hosts",
            "datastores",
            "vms",
        } <= set(dados)

    def test_a_gravidade_vem_em_texto(self, parque, agora) -> None:
        achados = health.evaluate(parque, now=agora)
        dados = json.loads(cli.render_json(parque, achados))
        gravidades = {a["severity"] for a in dados["findings"]}
        assert gravidades <= {"info", "warning", "critical"}

    def test_o_json_nao_leva_senhas(self, parque) -> None:
        texto = cli.render_json(parque, []).lower()
        for palavra in ("password", "senha", "pwd"):
            assert palavra not in texto


class TestSemEscritaEmModoDeTexto:
    """
    PT-PT: O modo de texto não escreve no vSphere.

           Uma operação destrutiva sem confirmação escrita fica a um `Ctrl-R` de
           distância da próxima vez que alguém a repetir sem pensar. Se um dia
           alguém acrescentar `--desligar`, este teste falha e pergunta porquê.

    EN-UK: Text mode does not write to vSphere. A destructive operation with no
           written confirmation sits one `Ctrl-R` away from the next time
           somebody repeats it without thinking. If somebody adds `--power-off`,
           this test fails and asks why.
    """

    def test_a_linha_de_comandos_nao_tem_operacoes(self) -> None:
        from vfc.__main__ import build_parser

        opcoes = {accao.dest for accao in build_parser()._actions}
        proibidas = {
            "desligar",
            "ligar",
            "reiniciar",
            "encerrar",
            "snapshot",
            "manutencao",
            "power_off",
            "reboot",
        }
        assert not opcoes & proibidas

    def test_nao_ha_opcao_de_senha_na_linha_de_comandos(self) -> None:
        # PT-PT: Um argumento fica visível no `ps` para qualquer utilizador da
        #        máquina e escrito no histórico da shell.
        # EN-UK: An argument is visible in `ps` to every user on the machine and
        #        written to the shell history.
        from vfc.__main__ import build_parser

        opcoes = {accao.dest for accao in build_parser()._actions}
        assert not opcoes & {"senha", "password", "pwd"}
