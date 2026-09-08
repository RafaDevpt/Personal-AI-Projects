#!/usr/bin/env python3
"""
PT-PT: Testes da decisão sobre o certificado.

       Esta é a segunda suite que interessa, e testa a coisa que quase todas as
       ferramentas de vSphere fazem mal: aceitar qualquer certificado.

       O caso que mais importa é o da **impressão digital que mudou**. É o
       momento em que uma ferramenta ou avisa ou não avisa, e a diferença entre
       as duas é a diferença entre notar uma substituição de certificado e
       entregar a senha de administrador a quem a provocou.

       Nenhum destes testes abre uma ligação de rede: a parte que fala com o
       socket está isolada em `fetch_certificate` e `_chain_validates`, e é
       substituída. O que se testa é a decisão, que é onde estão as escolhas.

EN-UK: Certificate decision tests.

       This is the second suite that matters, and it tests the thing nearly
       every vSphere tool gets wrong: accepting any certificate.

       The case that matters most is the **changed fingerprint** — the moment a
       tool either warns or does not, and the difference between noticing a
       certificate substitution and handing an administrator password to
       whoever caused it.

       None of these tests opens a network connection: the socket-facing part is
       isolated in `fetch_certificate` and `_chain_validates` and is substituted.
       What is tested is the decision, which is where the choices live.

Created by Redfox using Claude
"""

from __future__ import annotations

import pytest

from vfc import connection
from vfc.connection import CertificateInfo, TrustDecision, fingerprint_of

IMPRESSAO_A = "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99"
IMPRESSAO_B = "11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00"


@pytest.fixture
def sem_rede(monkeypatch: pytest.MonkeyPatch):
    """
    PT-PT: Substitui as duas funções que tocam na rede. Devolve uma função que
           configura o que elas devem responder.
    EN-UK: Replaces the two functions that touch the network, returning a
           function that configures what they should answer.
    """

    def configurar(impressao: str, cadeia_valida: bool = False, inacessivel: bool = False) -> None:
        def buscar(host: str, port: int = 443, timeout: float = 10.0) -> CertificateInfo:
            if inacessivel:
                raise OSError("ligação recusada")
            return CertificateInfo(
                fingerprint_sha256=impressao,
                subject="CN=esx01.lab.local",
                issuer="CN=esx01.lab.local",
                not_after="Jun 15 12:00:00 2027 GMT",
                self_signed=True,
            )

        monkeypatch.setattr(connection, "fetch_certificate", buscar)
        monkeypatch.setattr(
            connection, "_chain_validates", lambda host, port, timeout: cadeia_valida
        )

    return configurar


class TestImpressaoDigital:
    """PT-PT: O formato importa. / EN-UK: The format matters."""

    def test_formato_igual_ao_do_vsphere(self) -> None:
        # PT-PT: Grupos de dois em maiúsculas, separados por dois pontos. É para
        #        ser comparada à vista com o ecrã do servidor, e um formato
        #        diferente obriga a traduzir de cabeça — onde se erra.
        # EN-UK: Uppercase pairs separated by colons. It is compared by eye
        #        against the server's screen, and a different format forces a
        #        mental translation, which is where mistakes happen.
        impressao = fingerprint_of(b"qualquer coisa")
        assert impressao == impressao.upper()
        assert len(impressao.split(":")) == 32
        assert all(len(g) == 2 for g in impressao.split(":"))

    def test_e_determinista(self) -> None:
        assert fingerprint_of(b"x") == fingerprint_of(b"x")

    def test_bytes_diferentes_dao_impressoes_diferentes(self) -> None:
        assert fingerprint_of(b"x") != fingerprint_of(b"y")

    def test_versao_curta_para_cabecalhos(self) -> None:
        certificado = CertificateInfo(fingerprint_sha256=IMPRESSAO_A)
        curta = certificado.short_fingerprint
        assert "..." in curta
        assert curta.startswith("AA:BB:CC")
        assert len(curta) < len(IMPRESSAO_A)

    def test_versao_curta_sem_certificado(self) -> None:
        assert CertificateInfo().short_fingerprint == "--"


class TestDecisaoDeConfianca:
    """PT-PT: Onde se decide. / EN-UK: Where it is decided."""

    def test_cadeia_valida_prossegue(self, sem_rede) -> None:
        sem_rede(IMPRESSAO_A, cadeia_valida=True)
        resultado = connection.evaluate_trust("vc.lab.local")
        assert resultado.decision is TrustDecision.VALID_CHAIN
        assert resultado.may_connect
        assert not resultado.needs_decision

    def test_cadeia_valida_ignora_a_impressao_guardada(self, sem_rede) -> None:
        # PT-PT: Um parque que instalou uma autoridade interna deixa de precisar
        #        das impressões guardadas, e a antiga não pode passar a ser um
        #        motivo de aviso.
        # EN-UK: An estate that installed an internal CA no longer needs the
        #        pins, and the old one must not become a reason to warn.
        sem_rede(IMPRESSAO_A, cadeia_valida=True)
        resultado = connection.evaluate_trust("vc.lab.local", pinned_fingerprint=IMPRESSAO_B)
        assert resultado.decision is TrustDecision.VALID_CHAIN

    def test_certificado_novo_pede_decisao(self, sem_rede) -> None:
        sem_rede(IMPRESSAO_A)
        resultado = connection.evaluate_trust("esx01.lab.local")
        assert resultado.decision is TrustDecision.UNKNOWN_CERTIFICATE
        assert not resultado.may_connect
        assert resultado.needs_decision
        # PT-PT: A impressão digital tem de estar na mensagem: é o que a pessoa
        #        vai comparar.
        # EN-UK: The fingerprint has to be in the message: it is what the person
        #        will compare.
        assert IMPRESSAO_A in resultado.message

    def test_impressao_conhecida_prossegue(self, sem_rede) -> None:
        sem_rede(IMPRESSAO_A)
        resultado = connection.evaluate_trust("esx01.lab.local", pinned_fingerprint=IMPRESSAO_A)
        assert resultado.decision is TrustDecision.PINNED_MATCH
        assert resultado.may_connect

    def test_impressao_guardada_em_minusculas_ainda_coincide(self, sem_rede) -> None:
        # PT-PT: O ficheiro pode ter sido editado à mão. Um servidor de sempre
        #        que passa a "certificado mudou" por causa de maiúsculas seria um
        #        falso alarme — e falsos alarmes ensinam a ignorar os verdadeiros.
        # EN-UK: The file may have been hand-edited. A known server turning into
        #        "certificate changed" over letter case would be a false alarm,
        #        and false alarms teach people to ignore the real ones.
        sem_rede(IMPRESSAO_A)
        resultado = connection.evaluate_trust(
            "esx01.lab.local", pinned_fingerprint=IMPRESSAO_A.lower()
        )
        assert resultado.decision is TrustDecision.PINNED_MATCH

    def test_impressao_diferente_para_tudo(self, sem_rede) -> None:
        # PT-PT: O teste mais importante do ficheiro.
        # EN-UK: The most important test in the file.
        sem_rede(IMPRESSAO_B)
        resultado = connection.evaluate_trust("esx01.lab.local", pinned_fingerprint=IMPRESSAO_A)
        assert resultado.decision is TrustDecision.FINGERPRINT_CHANGED
        assert not resultado.may_connect
        assert resultado.needs_decision

    def test_a_mensagem_da_mudanca_mostra_as_duas(self, sem_rede) -> None:
        # PT-PT: Sem as duas lado a lado, não há como perceber o que mudou.
        # EN-UK: Without both side by side there is no way to see what changed.
        sem_rede(IMPRESSAO_B)
        resultado = connection.evaluate_trust("esx01.lab.local", pinned_fingerprint=IMPRESSAO_A)
        assert IMPRESSAO_A in resultado.message
        assert IMPRESSAO_B in resultado.message

    def test_servidor_inacessivel_e_distinto_de_certificado_mau(self, sem_rede) -> None:
        # PT-PT: Um cabo desligado não é um problema de confiança, e tratá-lo
        #        como tal mandaria alguém verificar um certificado por causa de
        #        uma rota em falta.
        # EN-UK: An unplugged cable is not a trust problem, and treating it as
        #        one would send somebody checking a certificate over a missing
        #        route.
        sem_rede(IMPRESSAO_A, inacessivel=True)
        resultado = connection.evaluate_trust("nao.existe")
        assert resultado.decision is TrustDecision.UNREACHABLE
        assert not resultado.may_connect
        assert not resultado.needs_decision


class TestEndpoint:
    """PT-PT: O que se guarda de um servidor. / EN-UK: What is kept about a server."""

    def test_nao_ha_campo_para_senha(self) -> None:
        # PT-PT: Testa-se a ausência de propósito. Se alguém acrescentar um
        #        campo de senha ao Endpoint, este teste falha e pergunta porquê.
        # EN-UK: The absence is tested on purpose. If somebody adds a password
        #        field to Endpoint, this test fails and asks why.
        campos = set(connection.Endpoint.__dataclass_fields__)
        assert not campos & {"password", "senha", "pwd", "secret"}

    def test_porta_por_omissao(self) -> None:
        assert connection.Endpoint(host="h", username="u").port == 443
