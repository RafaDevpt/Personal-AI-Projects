#!/usr/bin/env python3
"""
PT-PT: Testes das definições.

       Dois grupos. O primeiro verifica que **nenhuma senha é escrita em disco**
       e que nenhuma é lida de disco — testa-se a ausência, de propósito, porque
       a ausência é a funcionalidade.

       O segundo verifica que um ficheiro estragado não impede a aplicação de
       arrancar. Um ficheiro meio escrito porque a máquina desligou é normal, e
       recusar arrancar por causa de uma preferência de tema seria
       desproporcionado.

EN-UK: Settings tests.

       Two groups. The first checks that **no password is written to disk** and
       none is read from it — the absence is tested on purpose, because the
       absence is the feature.

       The second checks that a damaged file does not stop the application
       starting. A half-written file because the machine went down is normal,
       and refusing to start over a theme preference would be out of proportion.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
from pathlib import Path

from vfc.config import Server, Settings, load_settings, save_settings


class TestSenhasNuncaEmDisco:
    """PT-PT: A funcionalidade é a ausência. / EN-UK: The feature is the absence."""

    def test_o_servidor_nao_tem_campo_de_senha(self) -> None:
        campos = set(Server.__dataclass_fields__)
        assert not campos & {"password", "senha", "pwd", "secret", "token"}

    def test_as_definicoes_nao_tem_campo_de_senha(self) -> None:
        campos = set(Settings.__dataclass_fields__)
        assert not campos & {"password", "senha", "pwd", "secret", "save_password"}

    def test_o_ficheiro_gravado_nao_contem_senhas(self, tmp_path: Path) -> None:
        definicoes = Settings(
            servers=[Server(label="Lab", host="vc.lab.local", username="admin@vsphere.local")]
        )
        destino = tmp_path / "definicoes.json"
        assert save_settings(definicoes, destino)

        texto = destino.read_text(encoding="utf-8").lower()
        for palavra in ("password", "senha", "pwd", "secret"):
            assert palavra not in texto

    def test_uma_senha_posta_a_mao_no_ficheiro_e_ignorada(self, tmp_path: Path) -> None:
        # PT-PT: Alguém vai tentar. O que se garante é que não há caminho
        #        nenhum no programa que leia uma senha de um ficheiro — ela é
        #        ignorada na leitura e não sobrevive à gravação seguinte.
        # EN-UK: Somebody will try it. What is guaranteed is that no path in the
        #        program reads a password from a file: it is ignored on read and
        #        does not survive the next write.
        destino = tmp_path / "definicoes.json"
        destino.write_text(
            json.dumps(
                {
                    "servers": [
                        {"host": "vc.lab.local", "username": "admin", "password": "Passw0rd!"}
                    ]
                }
            ),
            encoding="utf-8",
        )
        definicoes = load_settings(destino)
        assert definicoes.servers[0].host == "vc.lab.local"
        assert not hasattr(definicoes.servers[0], "password")

        save_settings(definicoes, destino)
        assert "Passw0rd!" not in destino.read_text(encoding="utf-8")


class TestServidoresGuardados:
    def test_gravar_e_ler(self, tmp_path: Path) -> None:
        destino = tmp_path / "definicoes.json"
        original = Settings(
            servers=[
                Server(
                    label="Laboratório",
                    host="vc.lab.local",
                    username="admin@vsphere.local",
                    port=443,
                    fingerprint="AA:BB",
                )
            ],
            refresh_seconds=120,
        )
        save_settings(original, destino)
        lido = load_settings(destino)
        assert lido.servers[0].host == "vc.lab.local"
        assert lido.servers[0].fingerprint == "AA:BB"
        assert lido.refresh_seconds == 120

    def test_procura_ignora_maiusculas(self) -> None:
        definicoes = Settings(servers=[Server(host="VC.Lab.Local")])
        assert definicoes.server_for("vc.lab.local") is not None

    def test_lembrar_actualiza_em_vez_de_duplicar(self) -> None:
        definicoes = Settings(servers=[Server(host="vc.lab.local", username="antigo")])
        definicoes.remember(Server(host="vc.lab.local", username="novo", fingerprint="CC:DD"))
        assert len(definicoes.servers) == 1
        assert definicoes.servers[0].username == "novo"
        assert definicoes.servers[0].fingerprint == "CC:DD"

    def test_lembrar_sem_impressao_nao_apaga_a_que_ha(self) -> None:
        # PT-PT: Guardar o utilizador não pode deitar fora a impressão digital
        #        aceite — isso obrigaria a aceitar o certificado outra vez, e
        #        aceitar certificados com frequência é como se deixa de os ler.
        # EN-UK: Storing the username must not throw away the accepted
        #        fingerprint: that would force accepting the certificate again,
        #        and accepting certificates often is how people stop reading them.
        definicoes = Settings(servers=[Server(host="vc.lab.local", fingerprint="AA:BB")])
        definicoes.remember(Server(host="vc.lab.local", username="novo"))
        assert definicoes.servers[0].fingerprint == "AA:BB"

    def test_esquecer(self) -> None:
        definicoes = Settings(servers=[Server(host="vc.lab.local")])
        assert definicoes.forget("VC.LAB.LOCAL")
        assert definicoes.servers == []
        assert not definicoes.forget("nao.existe")

    def test_rotulo_na_lista(self) -> None:
        assert Server(label="Lab", host="vc.lab.local").display == "Lab (vc.lab.local)"
        assert Server(host="vc.lab.local").display == "vc.lab.local"


class TestFicheiroEstragado:
    """PT-PT: Nada disto pode impedir o arranque. / EN-UK: None of this may block startup."""

    def test_ficheiro_que_nao_existe(self, tmp_path: Path) -> None:
        definicoes = load_settings(tmp_path / "nao-existe.json")
        assert definicoes.servers == []
        assert definicoes.refresh_seconds == 60

    def test_json_invalido(self, tmp_path: Path) -> None:
        destino = tmp_path / "definicoes.json"
        destino.write_text("{ isto não é json", encoding="utf-8")
        assert load_settings(destino).servers == []

    def test_json_que_e_uma_lista(self, tmp_path: Path) -> None:
        destino = tmp_path / "definicoes.json"
        destino.write_text("[1, 2, 3]", encoding="utf-8")
        assert load_settings(destino).servers == []

    def test_valores_com_o_tipo_errado(self, tmp_path: Path) -> None:
        destino = tmp_path / "definicoes.json"
        destino.write_text(
            json.dumps({"refresh_seconds": "cada bocadinho", "servers": []}), encoding="utf-8"
        )
        assert load_settings(destino).refresh_seconds == 60

    def test_servidor_sem_endereco_e_descartado(self, tmp_path: Path) -> None:
        destino = tmp_path / "definicoes.json"
        destino.write_text(
            json.dumps({"servers": [{"username": "admin"}, {"host": "vc.lab.local"}]}),
            encoding="utf-8",
        )
        definicoes = load_settings(destino)
        assert len(definicoes.servers) == 1

    def test_gravar_num_sitio_impossivel_nao_rebenta(self, tmp_path: Path) -> None:
        # PT-PT: Perder a memória entre sessões é um incómodo. Interromper quem
        #        está a trabalhar por causa disso não é proporcionado.
        # EN-UK: Losing memory between sessions is an inconvenience.
        #        Interrupting somebody mid-task over it is not proportionate.
        impossivel = tmp_path / "ficheiro" / "que" / "e" / "um" / "ficheiro.json"
        impossivel.parent.parent.parent.parent.mkdir(parents=True)
        impossivel.parent.parent.parent.write_text("sou um ficheiro", encoding="utf-8")
        assert save_settings(Settings(), impossivel) is False


class TestLimiares:
    def test_passam_para_a_avaliacao(self) -> None:
        definicoes = Settings(datastore_free_critical_pct=5.0, snapshot_age_warning_days=7)
        limiares = definicoes.thresholds()
        assert limiares.datastore_free_critical_pct == 5.0
        assert limiares.snapshot_age_warning_days == 7

    def test_um_limiar_alterado_muda_o_resultado(self, tmp_path: Path) -> None:
        from vfc import health
        from vfc.models import DatastoreInfo

        datastore = DatastoreInfo(
            moid="ds", name="DS", capacity_bytes=1000 * 1024**3, free_bytes=150 * 1024**3
        )
        assert health.check_datastore(datastore, Settings().thresholds()) != []

        tolerante = Settings(datastore_free_warning_pct=5.0, datastore_free_critical_pct=2.0)
        assert health.check_datastore(datastore, tolerante.thresholds()) == []
