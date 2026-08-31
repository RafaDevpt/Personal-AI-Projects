#!/usr/bin/env python3
"""
PT-PT: Leitura e escrita da configuração em JSON.

       Um perfil gravado é o que permite fazer o mesmo switch vinte vezes sem
       o preencher vinte vezes, e é também o que se põe num repositório para
       haver histórico de quem mudou o quê. Por isso o formato é JSON legível
       e não um formato binário: um `git diff` de um perfil tem de se perceber.

       A leitura é deliberadamente tolerante com campos em falta — um perfil
       gravado por uma versão anterior deve continuar a abrir — e deliberadamente
       intolerante com valores errados: uma VLAN escrita como texto é um erro
       claro, e passar-lhe à frente só adia o problema para o momento em que o
       ficheiro é aplicado a um equipamento.

EN-UK: Reading and writing the configuration as JSON.

       A saved profile is what lets you build the same switch twenty times
       without filling the form twenty times, and it is also what goes into a
       repository so there is a history of who changed what. Hence a readable
       JSON format rather than a binary one: a `git diff` of a profile has to
       be understandable.

       Reading is deliberately tolerant of missing fields — a profile saved by
       an earlier version must still open — and deliberately intolerant of
       wrong values: a VLAN written as text is a clear mistake, and waving it
       through only defers the problem to the moment the file is applied to a
       device.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import (
    DeviceSpec,
    Interface,
    Management,
    Platform,
    PortMode,
    Security,
    Services,
    Vlan,
)

# PT-PT: Versão do formato. Se um dia mudar de forma incompatível, é por aqui
#        que a leitura sabe o que está a abrir.
# EN-UK: Format version. If it ever changes incompatibly, this is how the
#        reader knows what it is opening.
SPEC_FORMAT = 1


class SpecFileError(ValueError):
    """
    PT-PT: Ficheiro de perfil inválido, com a razão em português para poder
           ser mostrada ao utilizador tal como está.
    EN-UK: Invalid profile file, with the reason in Portuguese so it can be
           shown to the user as it stands.
    """


def to_dict(spec: DeviceSpec) -> dict[str, Any]:
    """
    PT-PT: Converte a configuração num dicionário pronto a serializar.
    EN-UK: Converts the configuration into a serialisable dictionary.
    """
    data = asdict(spec)
    data["platform"] = spec.platform.value
    for entry, interface in zip(data["interfaces"], spec.interfaces, strict=True):
        entry["mode"] = interface.mode.value
    return {"formato": SPEC_FORMAT, **data}


def from_dict(data: dict[str, Any]) -> DeviceSpec:
    """
    PT-PT: Reconstrói a configuração a partir de um dicionário.

    EN-UK: Rebuilds the configuration from a dictionary.

    :param data:
        PT-PT: Conteúdo lido do ficheiro. / EN-UK: Content read from the file.
    :return:
        PT-PT: Configuração pronta a usar. / EN-UK: Configuration ready to use.
    :raises SpecFileError:
        PT-PT: Se algum valor não for do tipo esperado.
        EN-UK: If any value is not of the expected type.
    """
    try:
        return DeviceSpec(
            platform=_platform(data.get("platform")),
            management=_management(data.get("management") or {}),
            vlans=[_vlan(v) for v in data.get("vlans") or []],
            interfaces=[_interface(i) for i in data.get("interfaces") or []],
            services=_services(data.get("services") or {}),
            security=_security(data.get("security") or {}),
            notes=str(data.get("notes") or ""),
        )
    except SpecFileError:
        raise
    except (TypeError, ValueError, AttributeError) as exc:
        raise SpecFileError(f"Perfil inválido: {exc}") from exc


def save(spec: DeviceSpec, path: Path) -> Path:
    """
    PT-PT: Grava a configuração em JSON, com acentos legíveis.

    EN-UK: Writes the configuration as JSON, with readable accents.

    :param spec:
        PT-PT: Configuração a gravar. / EN-UK: Configuration to save.
    :param path:
        PT-PT: Destino. A pasta é criada se faltar.
        EN-UK: Destination. The folder is created when missing.
    :return:
        PT-PT: O caminho gravado. / EN-UK: The written path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_dict(spec), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def load(path: Path) -> DeviceSpec:
    """
    PT-PT: Lê um perfil gravado.

    EN-UK: Reads a saved profile.

    :param path:
        PT-PT: Ficheiro a ler. / EN-UK: File to read.
    :return:
        PT-PT: Configuração. / EN-UK: Configuration.
    :raises SpecFileError:
        PT-PT: Se o ficheiro não existir ou não for JSON válido.
        EN-UK: If the file is missing or is not valid JSON.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpecFileError(f"Perfil não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SpecFileError(f"O perfil {path.name} não é JSON válido: {exc}") from exc

    if not isinstance(raw, dict):
        raise SpecFileError(f"O perfil {path.name} devia conter um objecto JSON.")
    return from_dict(raw)


# ---------------------------------------------------------------------------
# PT-PT: Conversores por secção.
# EN-UK: Per-section converters.
# ---------------------------------------------------------------------------


def _platform(value: Any) -> Platform:
    if value is None:
        return Platform.ARUBA_CX
    try:
        return Platform(str(value))
    except ValueError as exc:
        conhecidas = ", ".join(p.value for p in Platform)
        raise SpecFileError(f"Plataforma desconhecida: {value}. Conhecidas: {conhecidas}") from exc


def _mode(value: Any) -> PortMode:
    if value is None:
        return PortMode.ACCESS
    try:
        return PortMode(str(value))
    except ValueError as exc:
        conhecidos = ", ".join(m.value for m in PortMode)
        raise SpecFileError(f"Modo de porta desconhecido: {value}. Conhecidos: {conhecidos}") from exc


def _int_or_none(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise SpecFileError(f"{field_name}: esperava-se um número, veio {value!r}.") from exc


def _str_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def _int_list(value: Any, field_name: str) -> list[int]:
    return [int(v) for v in (_int_or_none(x, field_name) for x in _str_list(value)) if v is not None]


def _management(data: dict[str, Any]) -> Management:
    return Management(
        hostname=str(data.get("hostname") or ""),
        mgmt_vlan=_int_or_none(data.get("mgmt_vlan"), "vlan_gestao") or 1,
        mgmt_ip_cidr=str(data.get("mgmt_ip_cidr") or ""),
        gateway=str(data.get("gateway") or ""),
        domain=str(data.get("domain") or ""),
        dns_servers=_str_list(data.get("dns_servers")),
    )


def _vlan(data: dict[str, Any]) -> Vlan:
    vid = _int_or_none(data.get("vid"), "vlan")
    if vid is None:
        raise SpecFileError("VLAN sem identificador.")
    return Vlan(
        vid=vid,
        name=str(data.get("name") or ""),
        description=str(data.get("description") or ""),
        ip_cidr=str(data.get("ip_cidr") or ""),
    )


def _interface(data: dict[str, Any]) -> Interface:
    nome = str(data.get("name") or "").strip()
    if not nome:
        raise SpecFileError("Porta sem nome.")
    return Interface(
        name=nome,
        description=str(data.get("description") or ""),
        mode=_mode(data.get("mode")),
        access_vlan=_int_or_none(data.get("access_vlan"), f"porta {nome}"),
        native_vlan=_int_or_none(data.get("native_vlan"), f"porta {nome}"),
        tagged_vlans=_int_list(data.get("tagged_vlans"), f"porta {nome}"),
        voice_vlan=_int_or_none(data.get("voice_vlan"), f"porta {nome}"),
        poe=bool(data.get("poe", True)),
        enabled=bool(data.get("enabled", True)),
        edge_port=bool(data.get("edge_port", True)),
    )


def _services(data: dict[str, Any]) -> Services:
    return Services(
        ntp_servers=_str_list(data.get("ntp_servers")),
        syslog_servers=_str_list(data.get("syslog_servers")),
        timezone=str(data.get("timezone") or "WET"),
        snmp_community=str(data.get("snmp_community") or ""),
        snmp_location=str(data.get("snmp_location") or ""),
        snmp_contact=str(data.get("snmp_contact") or ""),
    )


def _security(data: dict[str, Any]) -> Security:
    return Security(
        admin_user=str(data.get("admin_user") or "admin"),
        banner=str(data.get("banner") or ""),
        disable_telnet=bool(data.get("disable_telnet", True)),
        disable_http=bool(data.get("disable_http", True)),
        rapid_stp=bool(data.get("rapid_stp", True)),
    )
