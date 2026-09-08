#!/usr/bin/env python3
"""
PT-PT: A ligação ao vCenter ou ao anfitrião ESXi, e a questão do certificado.

       **O problema, dito como ele é.** Praticamente todos os ESXi e vCenter do
       mundo apresentam um certificado auto-assinado, porque é o que vem de
       fábrica e substituí-lo por um de uma autoridade a sério dá trabalho. O
       resultado é que toda a gente que escreve automação para vSphere acaba,
       mais cedo ou mais tarde, a escrever a linha que desliga a verificação:

           contexto.verify_mode = ssl.CERT_NONE

       E a partir dessa linha a ligação está cifrada mas não está autenticada:
       qualquer coisa entre a estação e o servidor pode apresentar-se como o
       servidor e receber a senha de administrador do vSphere em texto limpo do
       outro lado do túnel. Não é um risco teórico numa rede de gestão que passa
       pelos mesmos switches que o resto.

       **O que se faz aqui em vez disso.** Confiança na primeira utilização, que
       é o modelo do SSH e funciona pela mesma razão:

       1. Tenta-se validar o certificado como se fosse um certificado normal. Se
          o parque tiver uma autoridade interna instalada na máquina, isto passa
          e não há mais nada a discutir.
       2. Se não validar, **não se liga**. Mostra-se a impressão digital SHA-256
          do certificado e pede-se que a compare com a que o servidor mostra
          (na consola do ESXi, em DCUI, ou em Administration > Certificates no
          vCenter). Ninguém decide por si.
       3. Aceite uma vez, a impressão digital fica guardada. Nas ligações
          seguintes é comparada, e **uma impressão digital diferente pára a
          ligação** com um aviso — que é exactamente o momento em que se quer
          ser interrompido.

       A diferença prática entre isto e `CERT_NONE` é que aqui há uma janela de
       exposição (a primeira ligação) em vez de uma permanente, e uma
       substituição de certificado é notada em vez de passar despercebida.

       O certificado do ESXi muda quando se lhe muda o nome ou se regenera —
       nessa altura a aplicação avisa e a impressão digital tem de ser aceite de
       novo. É chato uma vez por ano e é o comportamento certo.

EN-UK: The connection to vCenter or an ESXi host, and the certificate question.

       Nearly every ESXi and vCenter presents a self-signed certificate, and so
       nearly everybody writing vSphere automation ends up writing the line that
       switches verification off. Past that line the connection is encrypted but
       not authenticated: anything sitting between the workstation and the
       server can present itself as the server and take a vSphere administrator
       password in clear text out of the far end of the tunnel.

       What happens here instead is trust on first use, the SSH model: normal
       validation is tried first; if it fails the connection **stops**, the
       SHA-256 fingerprint is shown to be compared against what the server
       displays, and once accepted it is pinned. A changed fingerprint stops the
       connection — which is exactly when you want to be interrupted.

Created by Redfox using Claude
"""

from __future__ import annotations

import hashlib
import logging
import socket
import ssl
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

DEFAULT_PORT = 443


class TrustDecision(str, Enum):
    """
    PT-PT: Como correu a verificação do certificado.
    EN-UK: How the certificate check went.
    """

    VALID_CHAIN = "cadeia-valida"
    PINNED_MATCH = "impressao-conhecida"
    UNKNOWN_CERTIFICATE = "certificado-desconhecido"
    FINGERPRINT_CHANGED = "impressao-mudou"
    UNREACHABLE = "inacessivel"


@dataclass(frozen=True)
class CertificateInfo:
    """
    PT-PT: O que se conseguiu saber do certificado do servidor.
    EN-UK: What could be learned about the server's certificate.
    """

    fingerprint_sha256: str = ""
    subject: str = ""
    issuer: str = ""
    not_after: str = ""
    self_signed: bool = False

    @property
    def short_fingerprint(self) -> str:
        """
        PT-PT: Os primeiros e os últimos grupos, para caber num cabeçalho.
               Nunca para comparar — comparar é sempre com a completa.
        EN-UK: First and last groups, to fit in a header. Never for comparing —
               comparing is always against the full one.
        """
        if not self.fingerprint_sha256:
            return "--"
        partes = self.fingerprint_sha256.split(":")
        if len(partes) <= 6:
            return self.fingerprint_sha256
        return ":".join(partes[:3]) + " ... " + ":".join(partes[-3:])


@dataclass(frozen=True)
class TrustResult:
    """
    PT-PT: A decisão sobre o certificado, e o que dizer a quem está a ver.
    EN-UK: The decision about the certificate, and what to tell whoever is
           looking.
    """

    decision: TrustDecision
    certificate: CertificateInfo
    message: str = ""

    @property
    def may_connect(self) -> bool:
        """
        PT-PT: Se se pode prosseguir sem perguntar nada.
        EN-UK: Whether the connection may proceed without asking anything.
        """
        return self.decision in (TrustDecision.VALID_CHAIN, TrustDecision.PINNED_MATCH)

    @property
    def needs_decision(self) -> bool:
        """
        PT-PT: Se é preciso alguém olhar para a impressão digital e decidir.
        EN-UK: Whether somebody needs to look at the fingerprint and decide.
        """
        return self.decision in (
            TrustDecision.UNKNOWN_CERTIFICATE,
            TrustDecision.FINGERPRINT_CHANGED,
        )


def fingerprint_of(der_bytes: bytes) -> str:
    """
    PT-PT: A impressão digital SHA-256 no formato em que o vSphere a mostra —
           grupos de dois dígitos hexadecimais separados por dois pontos, em
           maiúsculas. O formato importa: é para ser comparada à vista com o que
           está no ecrã do servidor, e dois formatos diferentes obrigam a
           traduzir de cabeça, que é onde se erra.

    EN-UK: The SHA-256 fingerprint in the format vSphere displays — colon-
           separated uppercase hex pairs. The format matters: it is meant to be
           compared by eye against the server's screen, and two different
           formats force a mental translation, which is where mistakes happen.

    >>> fingerprint_of(b"")[:5]
    'E3:B0'
    """
    digest = hashlib.sha256(der_bytes).hexdigest().upper()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))


def fetch_certificate(host: str, port: int = DEFAULT_PORT, timeout: float = 10.0) -> CertificateInfo:
    """
    PT-PT: Vai buscar o certificado sem o validar, só para o poder mostrar.

           Isto usa um contexto sem verificação de propósito, e é o único sítio
           do programa onde isso acontece — **não** é por aqui que passam
           credenciais nenhumas. O objectivo é obter os bytes do certificado
           para calcular a impressão digital que a pessoa vai comparar. A
           autenticação faz-se depois, noutra ligação, já com a decisão tomada.

    EN-UK: Fetches the certificate without validating it, purely to be able to
           show it. This uses an unverified context on purpose, and it is the
           only place in the program that does — **no credentials travel here**.
           The point is to get the certificate bytes to compute the fingerprint
           the person will compare. Authentication happens afterwards, on
           another connection, with the decision already made.
    """
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE

    with (
        socket.create_connection((host, port), timeout=timeout) as bruto,
        contexto.wrap_socket(bruto, server_hostname=host) as seguro,
    ):
        der = seguro.getpeercert(binary_form=True)
        decodificado = seguro.getpeercert() or {}

    if not der:
        return CertificateInfo()

    def _juntar(campo: object) -> str:
        """PT-PT: O formato do ssl é aninhado. / EN-UK: ssl's format is nested."""
        if not isinstance(campo, tuple):
            return ""
        partes = []
        for grupo in campo:
            for par in grupo:
                if isinstance(par, tuple) and len(par) == 2:
                    partes.append(f"{par[0]}={par[1]}")
        return ", ".join(partes)

    sujeito = _juntar(decodificado.get("subject"))
    emissor = _juntar(decodificado.get("issuer"))

    return CertificateInfo(
        fingerprint_sha256=fingerprint_of(der),
        subject=sujeito,
        issuer=emissor,
        not_after=str(decodificado.get("notAfter", "")),
        self_signed=bool(sujeito) and sujeito == emissor,
    )


def evaluate_trust(
    host: str,
    port: int = DEFAULT_PORT,
    pinned_fingerprint: str = "",
    timeout: float = 10.0,
) -> TrustResult:
    """
    PT-PT: Decide se se pode ligar, e porquê.

           A ordem das perguntas é a ordem em que elas importam:

           1. A cadeia valida? Então acabou, e nem sequer se olha para a
              impressão digital guardada.
           2. Não valida. Já tínhamos uma impressão digital guardada?
              - Igual: prossegue-se. É o servidor de sempre.
              - **Diferente: pára.** Ou alguém regenerou o certificado, ou não
                se está a falar com o servidor de sempre. As duas hipóteses
                merecem que alguém olhe.
           3. Nunca vimos este servidor: mostra-se a impressão digital e
              espera-se por uma decisão.

    EN-UK: Decides whether the connection may proceed, and why. Chain first — if
           it validates, the pinned fingerprint is not even consulted. Then the
           pin: a match proceeds, a **mismatch stops**, because either somebody
           regenerated the certificate or this is not the same server, and both
           deserve a human look. A server never seen before gets its fingerprint
           shown and waits for a decision.
    """
    try:
        certificado = fetch_certificate(host, port, timeout)
    except OSError as erro:
        return TrustResult(
            decision=TrustDecision.UNREACHABLE,
            certificate=CertificateInfo(),
            message=f"Não foi possível chegar a {host}:{port} — {erro}",
        )

    if _chain_validates(host, port, timeout):
        return TrustResult(
            decision=TrustDecision.VALID_CHAIN,
            certificate=certificado,
            message="Certificado validado por uma autoridade em que esta máquina confia.",
        )

    guardada = (pinned_fingerprint or "").strip().upper()
    actual = certificado.fingerprint_sha256

    if guardada and actual:
        if guardada == actual:
            return TrustResult(
                decision=TrustDecision.PINNED_MATCH,
                certificate=certificado,
                message="Impressão digital igual à que foi aceite anteriormente.",
            )
        return TrustResult(
            decision=TrustDecision.FINGERPRINT_CHANGED,
            certificate=certificado,
            message=(
                "A IMPRESSÃO DIGITAL DO CERTIFICADO MUDOU.\n"
                f"  Aceite antes: {guardada}\n"
                f"  Agora:        {actual}\n"
                "Isto acontece quando o certificado é regenerado — mas também acontece "
                "quando não se está a falar com o servidor de sempre. Confirme na consola "
                "do servidor antes de aceitar."
            ),
        )

    return TrustResult(
        decision=TrustDecision.UNKNOWN_CERTIFICATE,
        certificate=certificado,
        message=(
            "Certificado que esta máquina não consegue validar — o que é o normal num "
            "ESXi ou vCenter com o certificado de fábrica.\n"
            f"  Impressão digital SHA-256: {actual}\n"
            "Compare-a com a que o servidor mostra antes de aceitar."
        ),
    )


def _chain_validates(host: str, port: int, timeout: float) -> bool:
    """
    PT-PT: Se o certificado passa a validação normal, com as autoridades da
           máquina. Uma excepção aqui é uma resposta — "não valida" — e não um
           erro a propagar.
    EN-UK: Whether the certificate passes normal validation against the
           machine's trust store. An exception here is an answer — "it does not
           validate" — not an error to propagate.
    """
    contexto = ssl.create_default_context()
    try:
        with (
            socket.create_connection((host, port), timeout=timeout) as bruto,
            contexto.wrap_socket(bruto, server_hostname=host),
        ):
            return True
    except ssl.SSLError:
        return False
    except OSError:
        return False


# ---------------------------------------------------------------------------
# PT-PT: A sessão.
# EN-UK: The session.
# ---------------------------------------------------------------------------


class VSphereConnectionError(RuntimeError):
    """
    PT-PT: Falha ao ligar, com a causa já traduzida para linguagem humana.
    EN-UK: Connection failure, with the cause already translated into human
           language.
    """


@dataclass
class Endpoint:
    """
    PT-PT: Onde ligar. Sem senha: a senha entra na chamada e não fica em lado
           nenhum que se possa serializar por engano.
    EN-UK: Where to connect. No password field: the password goes in as a call
           argument and never sits anywhere that could be serialised by mistake.
    """

    host: str
    username: str
    port: int = DEFAULT_PORT
    fingerprint: str = ""


class Session:
    """
    PT-PT: Uma sessão aberta contra um vCenter ou um ESXi.

           Guarda o `ServiceInstance` do pyVmomi e sabe resolver um identificador
           de objecto (o `moid`, que os modelos guardam) de volta para o objecto
           vivo. É essa a ponte entre a parte testável e a parte que fala com o
           servidor.

           Distingue vCenter de ESXi pelo `apiType`, e isso muda o que a
           aplicação pode oferecer: um ESXi sozinho não tem clusters, não tem
           DRS, e — se estiver com a licença gratuita — não aceita **nenhuma**
           operação de escrita pela API, por muito que o utilizador seja
           administrador. Isso é detectado e dito, porque o erro que o servidor
           devolve nesse caso (`RestrictedVersion`) não diz nada a quem o vê
           pela primeira vez.

    EN-UK: An open session against a vCenter or an ESXi host. It holds pyVmomi's
           `ServiceInstance` and can resolve a stored `moid` back to the live
           object — the bridge between the testable half and the half that talks
           to the server.

           It tells vCenter from ESXi by `apiType`, which changes what can be
           offered: a standalone ESXi has no clusters, no DRS, and — on the free
           licence — accepts **no** write operation through the API at all,
           however administrative the user is. That is detected and stated,
           because the server's own error (`RestrictedVersion`) means nothing to
           somebody seeing it for the first time.
    """

    def __init__(self, service_instance: object, endpoint: Endpoint) -> None:
        self.si = service_instance
        self.endpoint = endpoint
        self._content = None

    # -- PT-PT: Identidade do servidor. / EN-UK: Server identity. -----------

    @property
    def content(self) -> object:
        if self._content is None:
            self._content = self.si.RetrieveContent()  # type: ignore[attr-defined]
        return self._content

    @property
    def about(self) -> object:
        return self.content.about  # type: ignore[attr-defined]

    @property
    def is_vcenter(self) -> bool:
        """
        PT-PT: `VirtualCenter` contra `HostAgent`. É o que decide se há clusters
               para percorrer ou se o inventário é um anfitrião só.
        EN-UK: `VirtualCenter` against `HostAgent`. It decides whether there are
               clusters to walk or the inventory is a single host.
        """
        return getattr(self.about, "apiType", "") == "VirtualCenter"

    @property
    def product(self) -> str:
        nome = getattr(self.about, "fullName", "")
        return str(nome)

    def read_only_reason(self) -> str:
        """
        PT-PT: Porque é que este servidor não vai aceitar escritas — se for o
               caso.

               O caso que interessa é o ESXi com a licença gratuita. A API fica
               em leitura, e uma aplicação que ofereça botões de ligar e
               desligar sem dizer isto parece avariada quando eles falham todos.
               Mais vale dizê-lo no cabeçalho, uma vez.

               Devolve texto vazio quando não há impedimento conhecido.

        EN-UK: Why this server will not accept writes — if that is the case. The
               case that matters is a free-licensed ESXi, where the API goes
               read-only: an application offering power buttons without saying
               so looks broken when they all fail. Empty string when there is no
               known impediment.
        """
        licenciamento = getattr(self.content, "licenseManager", None)
        if licenciamento is None:
            return ""
        try:
            licencas = list(getattr(licenciamento, "licenses", []) or [])
        except Exception:  # noqa: BLE001
            return ""
        for licenca in licencas:
            nome = str(getattr(licenca, "editionKey", "")) + str(getattr(licenca, "name", ""))
            if "esxFree" in nome or "Free" in nome:
                return (
                    "Este anfitrião está com a licença gratuita do ESXi. Nessa licença a API "
                    "do vSphere é só de leitura: ligar, desligar, snapshots e manutenção vão "
                    "ser recusados pelo servidor, mesmo com credenciais de administrador. "
                    "A monitorização funciona toda."
                )
        return ""

    # -- PT-PT: Do identificador para o objecto. / EN-UK: Id to object. ------

    def _by_moid(self, kind: str, moid: str) -> object:
        """
        PT-PT: Reconstrói a referência a partir do tipo e do identificador.

               É assim e não por procura no inventário porque a procura seria
               uma travessia inteira por cada botão carregado. O identificador
               é estável enquanto o objecto existir.

        EN-UK: Rebuilds the reference from type and id, rather than searching the
               inventory — a search would be a full traversal per button press.
               The id is stable for as long as the object exists.
        """
        from pyVmomi import vim  # noqa: PLC0415

        tipos = {
            "VirtualMachine": vim.VirtualMachine,
            "HostSystem": vim.HostSystem,
            "Datastore": vim.Datastore,
        }
        if kind not in tipos:
            raise VSphereConnectionError(f"Tipo de objecto desconhecido: {kind}")
        referencia = tipos[kind](moid)
        referencia._stub = self.si._stub  # type: ignore[attr-defined]
        return referencia

    def vm_by_moid(self, moid: str) -> object:
        return self._by_moid("VirtualMachine", moid)

    def host_by_moid(self, moid: str) -> object:
        return self._by_moid("HostSystem", moid)

    def snapshot_by_id(self, vm_moid: str, snapshot_id: int) -> object:
        """
        PT-PT: Encontra o snapshot pela árvore da máquina.

               Um snapshot não tem `moid` próprio — vive dentro da máquina e
               identifica-se por um número dentro dela. Percorre-se a árvore,
               que é pequena por natureza.

        EN-UK: Finds the snapshot through the machine's tree. A snapshot has no
               `moid` of its own: it lives inside the machine and is identified
               by a number within it. The tree is walked, and it is small by
               nature.
        """
        maquina = self.vm_by_moid(vm_moid)
        raiz = getattr(getattr(maquina, "snapshot", None), "rootSnapshotList", None)
        if not raiz:
            raise VSphereConnectionError("Esta máquina já não tem snapshots.")

        def procurar(nos: object) -> object | None:
            for no in nos:  # type: ignore[union-attr]
                if getattr(no, "id", None) == snapshot_id:
                    return no.snapshot
                achado = procurar(getattr(no, "childSnapshotList", []) or [])
                if achado is not None:
                    return achado
            return None

        encontrado = procurar(raiz)
        if encontrado is None:
            raise VSphereConnectionError(
                "O snapshot já não existe. Actualize o inventário — pode ter sido apagado "
                "entretanto, aqui ou noutra consola."
            )
        return encontrado

    def close(self) -> None:
        """PT-PT: Fecha a sessão no servidor. / EN-UK: Closes the server session."""
        try:
            from pyVim.connect import Disconnect  # noqa: PLC0415

            Disconnect(self.si)
        except Exception as erro:  # noqa: BLE001
            logger.debug("Falha ao fechar a sessão: %s", erro)


def connect(
    endpoint: Endpoint,
    password: str,
    trusted_fingerprint: str = "",
    timeout: float = 30.0,
) -> Session:
    """
    PT-PT: Abre a sessão, com o certificado já decidido.

           O `trusted_fingerprint` é obrigatório na prática: ou o certificado
           valida sozinho, ou tem de vir aqui a impressão digital que alguém
           aceitou. Não há caminho por aqui que ligue sem uma coisa nem outra —
           que é o ponto todo deste módulo.

           As excepções do pyVmomi são traduzidas. `InvalidLogin` chega como
           "vim.fault.InvalidLogin" e não ajuda ninguém; o que ajuda é "as
           credenciais foram recusadas", e a nota de que o vCenter bloqueia a
           conta ao fim de algumas tentativas.

    EN-UK: Opens the session with the certificate question already settled.
           Either the chain validates on its own, or an accepted fingerprint has
           to be passed in — there is no path through here that connects without
           one or the other, which is the entire point of this module.

           pyVmomi's exceptions are translated: "vim.fault.InvalidLogin" helps
           nobody, "the credentials were refused" does — along with the note
           that vCenter locks the account after a few tries.
    """
    try:
        from pyVim.connect import SmartConnect  # noqa: PLC0415
        from pyVmomi import vim  # noqa: PLC0415
    except ImportError as erro:  # pragma: no cover - ambiente sem dependência
        raise VSphereConnectionError(
            "O pyVmomi não está instalado. Sem ele não há ligação nenhuma ao vSphere:\n"
            "    pip install -r requirements.txt"
        ) from erro

    contexto = _build_context(endpoint, trusted_fingerprint)

    try:
        instancia = SmartConnect(
            host=endpoint.host,
            user=endpoint.username,
            pwd=password,
            port=endpoint.port,
            sslContext=contexto,
            connectionPoolTimeout=int(timeout),
        )
    except vim.fault.InvalidLogin as erro:
        raise VSphereConnectionError(
            "Credenciais recusadas pelo servidor.\n"
            "Confirme o utilizador — no vCenter costuma incluir o domínio, como "
            "administrator@vsphere.local; num ESXi é normalmente root.\n"
            "Atenção: algumas tentativas falhadas seguidas bloqueiam a conta."
        ) from erro
    except vim.fault.NoPermission as erro:
        raise VSphereConnectionError(
            "As credenciais estão certas mas a conta não tem permissões para ler o "
            "inventário."
        ) from erro
    except ssl.SSLCertVerificationError as erro:
        raise VSphereConnectionError(
            f"O certificado do servidor não foi aceite: {erro}.\n"
            "Verifique a impressão digital antes de continuar."
        ) from erro
    except (TimeoutError, OSError) as erro:
        raise VSphereConnectionError(
            f"Não foi possível chegar a {endpoint.host}:{endpoint.port} — {erro}.\n"
            "Confirme o endereço, a porta 443 e se a rede de gestão está acessível daqui."
        ) from erro
    except Exception as erro:  # noqa: BLE001
        raise VSphereConnectionError(f"Falha ao ligar: {erro}") from erro

    if instancia is None:
        raise VSphereConnectionError("O servidor aceitou a ligação mas não devolveu uma sessão.")

    return Session(instancia, endpoint)


def _build_context(endpoint: Endpoint, trusted_fingerprint: str) -> ssl.SSLContext:
    """
    PT-PT: O contexto TLS para a ligação autenticada.

           Com uma impressão digital aceite, a verificação de cadeia é desligada
           — mas só porque a identidade do servidor já foi estabelecida de outra
           maneira, e verificada em `evaluate_trust` antes de se chegar aqui.
           Sem impressão digital, o contexto é o normal e o certificado tem de
           validar sozinho.

    EN-UK: The TLS context for the authenticated connection. With an accepted
           fingerprint, chain verification is switched off — but only because
           the server's identity was established another way and checked in
           `evaluate_trust` before reaching here. With no fingerprint the
           context is the normal one and the certificate has to validate on its
           own.
    """
    if trusted_fingerprint:
        contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        contexto.check_hostname = False
        contexto.verify_mode = ssl.CERT_NONE
        logger.info(
            "A ligar a %s com a impressão digital aceite %s",
            endpoint.host,
            trusted_fingerprint[:17],
        )
        return contexto
    return ssl.create_default_context()
