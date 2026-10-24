#!/usr/bin/env python3
"""
PT-PT: Exportações — o equivalente ao "manual" para quem vai ao bastidor.

       * **Constatações (CSV)** — a lista de trabalho: o quê, onde, porquê e o
         que fazer.
       * **Lista de cabos (CSV)** — cada cabo com piso, sala, portas, VLANs
         desenhadas em cada ponta e estado. É o que se imprime e leva para o
         bastidor; a configuração em si continua a sair do Config Builder, que
         é quem a sabe escrever para cada fabricante.

       CSV com `;` e BOM UTF-8, porque é assim que o Excel em português o abre
       à primeira, com acentos e colunas no sítio.

EN-UK: Exports — the "manual" for whoever walks to the rack.

       CSV with `;` and a UTF-8 BOM, because that is how Portuguese Excel opens
       it first time, accents and columns intact.

Created by Redfox using Claude
"""

from __future__ import annotations

import csv
from pathlib import Path

from .engine import Result
from .models import Twin
from .scene import physical_positions

_ESTADO = {"ok": "OK", "info": "Info", "aviso": "Aviso", "erro": "ERRO"}


def write_findings_csv(result: Result, path: Path) -> Path:
    """PT-PT: Constatações em CSV. / EN-UK: Findings as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as ficheiro:
        escritor = csv.writer(ficheiro, delimiter=";")
        escritor.writerow(["Gravidade", "Código", "Constatação", "Detalhe", "Correcção", "Equipamentos"])
        for f in result.findings:
            escritor.writerow(
                [_ESTADO[f.severity.value], f.code, f.title, f.detail, f.fix, ", ".join(f.devices)]
            )
    return path


def write_cable_list_csv(twin: Twin, result: Result, path: Path) -> Path:
    """PT-PT: Lista de cabos em CSV. / EN-UK: Cable list as CSV."""
    posicoes = physical_positions(twin)

    def onde(equipamento: str) -> tuple[str, str, str]:
        p = posicoes.get(equipamento)
        if not p:
            return ("", "", "")
        sitio = f"{p['sala']} · {p['bastidor']} U{p['u']}" if p.get("bastidor") else p["sala"]
        return (p["edificio"], p["piso"], sitio)

    def vlans(equipamento: str, porta: str) -> str:
        d = twin.devices.get(equipamento)
        desenhada = d.designed_ports.get(porta) if d else None
        if desenhada is None:
            return ""
        if desenhada.mode == "trunk":
            marcadas = ",".join(map(str, sorted(desenhada.tagged_vlans)))
            return f"trunk nativa {desenhada.native_vlan} | {marcadas}"
        if desenhada.mode == "disabled" or not desenhada.enabled:
            return "desactivada"
        voz = f" voz {desenhada.voice_vlan}" if desenhada.voice_vlan is not None else ""
        return f"acesso {desenhada.access_vlan}{voz}"

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as ficheiro:
        escritor = csv.writer(ficheiro, delimiter=";")
        escritor.writerow(
            [
                "Estado",
                "Edifício A", "Piso A", "Sala / bastidor A", "Equipamento A", "Porta A", "VLANs A",
                "Edifício B", "Piso B", "Sala / bastidor B", "Equipamento B", "Porta B", "VLANs B",
                "Descoberto", "Desenhado", "Nota",
            ]
        )
        for lig in sorted(twin.links, key=lambda x: (onde(x.a), x.a, x.a_port)):
            veredicto = result.link_verdicts.get(lig.id)
            escritor.writerow(
                [
                    _ESTADO[veredicto.value] if veredicto else "OK",
                    *onde(lig.a), lig.a, lig.a_port, vlans(lig.a, lig.a_port),
                    *onde(lig.b), lig.b, lig.b_port, vlans(lig.b, lig.b_port),
                    "sim" if lig.discovered else "não",
                    "sim" if lig.designed else "não",
                    lig.note,
                ]
            )
    return path
