"""
PT-PT: Relatorios em HTML.

       Uma nota que vale mais do que parece: tudo o que vem do Windows passa
       por `escape()` antes de entrar no HTML. As mensagens dos event logs
       contem caminhos, XML e, com alguma frequencia, sinais de menor e maior —
       o texto de erro do Internet Explorer e das aplicacoes .NET esta cheio
       deles. A v1.0 inseria essas mensagens directamente e o resultado eram
       relatorios com metade do conteudo invisivel, porque o navegador
       interpretava fragmentos da mensagem como etiquetas. Se em vez de um
       fragmento inofensivo aparecesse um `<script>`, o relatorio passava a
       executa-lo ao ser aberto.

EN-UK: HTML reports.

       One note worth more than it looks: everything coming from Windows goes
       through `escape()` before entering the HTML. Event log messages contain
       paths, XML and, fairly often, angle brackets. v1.0 inserted those
       messages directly and produced reports with half the content invisible,
       because the browser read fragments of the message as tags. Had a
       `<script>` appeared instead of a harmless fragment, the report would have
       executed it on opening.

Created by Redfox using Claude
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from html import escape
from pathlib import Path

from . import __credit__, __version__
from .models import Achado, Analise, Gravidade

log = logging.getLogger(__name__)

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  margin: 0; padding: 32px 24px; background: #f4f5f7; color: #1c2833;
  line-height: 1.55;
}
.folha { max-width: 1080px; margin: 0 auto; }
header { border-bottom: 3px solid #1c2833; padding-bottom: 16px; margin-bottom: 24px; }
h1 { font-size: 24px; margin: 0 0 4px; }
.sub { color: #5d6d7e; font-size: 14px; }
h2 { font-size: 18px; margin: 32px 0 12px; }
.cartoes { display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0; }
.cartao {
  background: #fff; border: 1px solid #d5d8dc; border-radius: 6px;
  padding: 14px 18px; min-width: 130px;
}
.cartao .n { font-size: 26px; font-weight: 600; }
.cartao .r { font-size: 12px; color: #5d6d7e; text-transform: uppercase; letter-spacing: .4px; }
.veredicto {
  background: #fff; border-left: 5px solid #1c2833; border-radius: 4px;
  padding: 14px 18px; margin: 20px 0; font-size: 15px;
}
.aviso {
  background: #fdf3e3; border-left: 5px solid #c87f0a; border-radius: 4px;
  padding: 12px 16px; margin: 12px 0; font-size: 14px;
}
.item {
  background: #fff; border: 1px solid #d5d8dc; border-left-width: 5px;
  border-radius: 4px; padding: 16px 18px; margin-bottom: 12px;
}
.item h3 { margin: 0 0 6px; font-size: 16px; }
.etiqueta {
  display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: .5px;
  color: #fff; border-radius: 3px; padding: 2px 8px; margin-right: 8px;
  vertical-align: 2px;
}
.meta { font-size: 12px; color: #5d6d7e; margin-bottom: 8px; }
.campo { margin-top: 8px; font-size: 14px; }
.campo b { display: block; font-size: 12px; text-transform: uppercase;
  letter-spacing: .4px; color: #5d6d7e; margin-bottom: 2px; }
pre {
  background: #f4f5f7; border: 1px solid #e5e7e9; border-radius: 3px;
  padding: 10px 12px; font-size: 12px; white-space: pre-wrap; word-break: break-word;
  margin: 6px 0 0; font-family: Consolas, "Courier New", monospace;
}
table { border-collapse: collapse; width: 100%; background: #fff;
  border: 1px solid #d5d8dc; border-radius: 4px; overflow: hidden; font-size: 14px; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #eaecee; }
th { background: #eaecee; font-size: 12px; text-transform: uppercase;
  letter-spacing: .4px; color: #5d6d7e; }
tr:last-child td { border-bottom: none; }
footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #d5d8dc;
  font-size: 12px; color: #5d6d7e; }
@media print { body { background: #fff; padding: 0; } .item, table { break-inside: avoid; } }
"""


def _nome_seguro(texto: str) -> str:
    """
    PT-PT: Reduz um texto a um nome de ficheiro valido em Windows.

           Os caracteres proibidos vao fora, e os espacos tambem — um nome com
           espacos obriga a aspas em qualquer linha de comandos que lhe toque
           depois.

    EN-UK: Reduces text to a valid Windows file name. Forbidden characters go,
           and so do spaces — a name with spaces forces quoting in any command
           line that later touches it.
    """
    limpo = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", texto).strip(" .")
    limpo = re.sub(r"\s+", "_", limpo)
    return limpo[:60] or "relatorio"


def _cabecalho(titulo: str, identificacao: dict[str, str]) -> str:
    """PT-PT: Bloco de cabecalho comum. / EN-UK: Common header block."""
    agora = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linhas = " · ".join(
        f"{escape(k)}: <b>{escape(str(v))}</b>" for k, v in identificacao.items()
    )
    return (
        "<header>"
        f"<h1>{escape(titulo)}</h1>"
        f'<div class="sub">{linhas}</div>'
        f'<div class="sub">Gerado em {escape(agora)} · IT Toolkit {escape(__version__)}</div>'
        "</header>"
    )


def _documento(titulo: str, corpo: str) -> str:
    """PT-PT: Envolve o corpo num HTML completo. / EN-UK: Wraps body in full HTML."""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="pt-PT"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(titulo)}</title><style>{_CSS}</style></head>"
        f'<body><div class="folha">{corpo}'
        f'<footer>{escape(__credit__)}</footer>'
        "</div></body></html>"
    )


def _etiqueta(gravidade: Gravidade) -> str:
    """PT-PT: Etiqueta colorida de gravidade. / EN-UK: Coloured severity tag."""
    return (
        f'<span class="etiqueta" style="background:{gravidade.cor}">'
        f"{escape(gravidade.etiqueta)}</span>"
    )


def _bloco_grupo(grupo) -> str:
    """PT-PT: Um grupo de eventos em HTML. / EN-UK: One event group as HTML."""
    regra = grupo.regra
    titulo = regra.titulo if regra else f"Evento {grupo.event_id} sem entrada na base"
    partes = [
        f'<div class="item" style="border-left-color:{grupo.gravidade.cor}">',
        f"<h3>{_etiqueta(grupo.gravidade)}{escape(titulo)}</h3>",
        '<div class="meta">',
        f"Event ID {grupo.event_id} · {escape(grupo.provider)} · log {escape(grupo.log)} · "
        f"{grupo.contagem} ocorrência(s)",
    ]
    if grupo.recorrente:
        partes.append(" · <b>recorrente</b>")
    if grupo.primeiro and grupo.ultimo and grupo.primeiro != grupo.ultimo:
        partes.append(f" · de {escape(grupo.primeiro)} a {escape(grupo.ultimo)}")
    elif grupo.ultimo:
        partes.append(f" · {escape(grupo.ultimo)}")
    partes.append("</div>")

    if regra:
        partes.append(f'<div class="campo"><b>Causa provável</b>{escape(regra.causa)}</div>')
        partes.append(f'<div class="campo"><b>O que verificar</b>{escape(regra.solucao)}</div>')
    else:
        partes.append(
            '<div class="campo"><b>O que verificar</b>'
            "Este evento não tem entrada na base de conhecimento. A repetição é o "
            "motivo de estar aqui. Procurar o Event ID e o provider na documentação "
            "do fabricante.</div>"
        )

    if grupo.exemplo:
        partes.append(f"<div class=\"campo\"><b>Mensagem</b><pre>{escape(grupo.exemplo)}</pre></div>")

    partes.append("</div>")
    return "".join(partes)


def _bloco_achado(achado: Achado) -> str:
    """PT-PT: Um achado em HTML. / EN-UK: One finding as HTML."""
    partes = [
        f'<div class="item" style="border-left-color:{achado.gravidade.cor}">',
        f"<h3>{_etiqueta(achado.gravidade)}{escape(achado.titulo)}</h3>",
        f'<div class="meta">{escape(achado.modulo)}</div>',
        f'<div class="campo"><b>Detalhe</b>{escape(achado.detalhe)}</div>',
    ]
    if achado.solucao:
        partes.append(f'<div class="campo"><b>O que verificar</b>{escape(achado.solucao)}</div>')
    partes.append("</div>")
    return "".join(partes)


def relatorio_eventos(analise: Analise, identificacao: dict[str, str]) -> str:
    """
    PT-PT: Relatorio HTML da analise de eventos.
    EN-UK: HTML report of the event analysis.
    """
    corpo = [_cabecalho("Análise de Event Logs", identificacao)]

    corpo.append('<div class="cartoes">')
    corpo.append(
        f'<div class="cartao"><div class="n">{analise.total}</div>'
        f'<div class="r">eventos lidos</div></div>'
    )
    corpo.append(
        f'<div class="cartao"><div class="n">{len(analise.acionaveis)}</div>'
        f'<div class="r">a precisar de atenção</div></div>'
    )
    corpo.append(
        f'<div class="cartao"><div class="n">{analise.criticos}</div>'
        f'<div class="r">críticos</div></div>'
    )
    corpo.append(
        f'<div class="cartao"><div class="n">{analise.horas}h</div>'
        f'<div class="r">período</div></div>'
    )
    corpo.append("</div>")

    corpo.append(f'<div class="veredicto">{escape(analise.veredicto)}</div>')

    for aviso in analise.avisos:
        corpo.append(f'<div class="aviso">{escape(aviso)}</div>')

    if analise.problemas:
        corpo.append("<h2>Problemas identificados</h2>")
        corpo.extend(_bloco_grupo(g) for g in analise.problemas)

    if analise.outros:
        corpo.append("<h2>Outros eventos registados</h2>")
        corpo.append(
            "<table><tr><th>ID</th><th>Origem</th><th>Log</th><th>Nível</th>"
            "<th>Ocorrências</th><th>Último</th></tr>"
        )
        for grupo in analise.outros[:60]:
            corpo.append(
                f"<tr><td>{grupo.event_id}</td><td>{escape(grupo.provider)}</td>"
                f"<td>{escape(grupo.log)}</td><td>{escape(grupo.nivel_texto)}</td>"
                f"<td>{grupo.contagem}</td><td>{escape(grupo.ultimo)}</td></tr>"
            )
        corpo.append("</table>")
        if len(analise.outros) > 60:
            corpo.append(
                f'<div class="sub">Mais {len(analise.outros) - 60} tipo(s) de evento '
                "não listados.</div>"
            )

    return _documento("Análise de Event Logs", "".join(corpo))


def relatorio_saude(
    achados: list[Achado],
    identificacao: dict[str, str],
    analise: Analise | None = None,
) -> str:
    """
    PT-PT: Relatorio de saude da maquina, opcionalmente com os eventos.
    EN-UK: Machine health report, optionally including the events.
    """
    corpo = [_cabecalho("Relatório de Saúde da Máquina", identificacao)]

    por_gravidade = dict.fromkeys(Gravidade, 0)
    for achado in achados:
        por_gravidade[achado.gravidade] += 1

    corpo.append('<div class="cartoes">')
    for gravidade in (Gravidade.CRITICA, Gravidade.ALTA, Gravidade.MEDIA, Gravidade.BAIXA):
        corpo.append(
            f'<div class="cartao"><div class="n" style="color:{gravidade.cor}">'
            f'{por_gravidade[gravidade]}</div>'
            f'<div class="r">{escape(gravidade.etiqueta.lower())}</div></div>'
        )
    corpo.append("</div>")

    if por_gravidade[Gravidade.CRITICA]:
        veredicto = (
            f"{por_gravidade[Gravidade.CRITICA]} problema(s) crítico(s) a exigir "
            "acção imediata."
        )
    elif achados:
        veredicto = f"{len(achados)} problema(s) identificado(s), nenhum crítico."
    else:
        veredicto = "Nenhum problema identificado nas verificações efectuadas."
    corpo.append(f'<div class="veredicto">{escape(veredicto)}</div>')

    if achados:
        corpo.append("<h2>Verificações do sistema</h2>")
        ordenados = sorted(achados, key=lambda a: a.gravidade.value)
        corpo.extend(_bloco_achado(a) for a in ordenados)

    if analise is not None and analise.problemas:
        corpo.append("<h2>Event logs</h2>")
        corpo.append(f'<div class="veredicto">{escape(analise.veredicto)}</div>')
        for aviso in analise.avisos:
            corpo.append(f'<div class="aviso">{escape(aviso)}</div>')
        corpo.extend(_bloco_grupo(g) for g in analise.problemas)

    return _documento("Relatório de Saúde", "".join(corpo))


def relatorio_inventario(
    hardware: dict[str, str],
    sistema: dict[str, str],
    software: list[dict],
    actualizacoes: list[dict],
    identificacao: dict[str, str],
) -> str:
    """
    PT-PT: Relatorio de inventario da maquina.
    EN-UK: Machine inventory report.
    """
    corpo = [_cabecalho("Inventário da Máquina", identificacao)]

    for titulo, dados in (("Hardware", hardware), ("Sistema operativo", sistema)):
        if not dados:
            continue
        corpo.append(f"<h2>{escape(titulo)}</h2><table>")
        for chave, valor in dados.items():
            corpo.append(f"<tr><th>{escape(chave)}</th><td>{escape(str(valor))}</td></tr>")
        corpo.append("</table>")

    if actualizacoes:
        corpo.append("<h2>Últimas actualizações</h2><table>")
        corpo.append("<tr><th>Identificador</th><th>Tipo</th><th>Instalada</th></tr>")
        for item in actualizacoes:
            corpo.append(
                f"<tr><td>{escape(str(item.get('HotFixID') or '?'))}</td>"
                f"<td>{escape(str(item.get('Description') or ''))}</td>"
                f"<td>{escape(str(item.get('Quando') or ''))}</td></tr>"
            )
        corpo.append("</table>")

    if software:
        corpo.append(f"<h2>Software instalado ({len(software)})</h2><table>")
        corpo.append("<tr><th>Nome</th><th>Versão</th><th>Fornecedor</th></tr>")
        for item in software:
            corpo.append(
                f"<tr><td>{escape(str(item.get('DisplayName') or ''))}</td>"
                f"<td>{escape(str(item.get('DisplayVersion') or ''))}</td>"
                f"<td>{escape(str(item.get('Publisher') or ''))}</td></tr>"
            )
        corpo.append("</table>")

    return _documento("Inventário da Máquina", "".join(corpo))


def gravar(html: str, pasta: Path, prefixo: str) -> Path:
    """
    PT-PT: Grava o HTML com data e hora no nome.

           O carimbo temporal esta no nome de proposito: um relatorio nunca
           sobrepoe outro. A v1.0 usava um nome fixo por tipo, e quem corresse
           duas analises seguidas perdia a primeira — que era muitas vezes a que
           interessava, tirada antes de mexer na maquina.

    EN-UK: Writes the HTML with date and time in the name. The timestamp is
           deliberate: a report never overwrites another. v1.0 used a fixed name
           per type, so running two analyses in a row lost the first — often the
           one that mattered, taken before touching the machine.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = _nome_seguro(prefixo)
    destino = pasta / f"{base}_{carimbo}.html"

    # PT-PT: O carimbo tem resolucao de um segundo, e gerar dois relatorios
    #        seguidos leva menos do que isso — carregar em «relatório de saúde»
    #        e logo a seguir em «relatório de eventos» chega. Sem este
    #        contador, o segundo apagava o primeiro, que e precisamente o
    #        problema que o carimbo existia para evitar.
    # EN-UK: The stamp has one-second resolution, and producing two reports in a
    #        row takes less than that. Without this counter the second
    #        overwrote the first — exactly the problem the stamp existed to
    #        prevent.
    contador = 2
    while destino.exists():
        destino = pasta / f"{base}_{carimbo}_{contador}.html"
        contador += 1

    destino.write_text(html, encoding="utf-8")
    log.info("Relatório gravado em %s", destino)
    return destino


def listar_relatorios(pasta: Path) -> list[Path]:
    """
    PT-PT: Relatorios existentes, do mais recente para o mais antigo.
    EN-UK: Existing reports, newest first.
    """
    if not pasta.is_dir():
        return []
    try:
        ficheiros = [p for p in pasta.glob("*.html") if p.is_file()]
    except OSError as exc:
        log.warning("Não foi possível listar %s: %s", pasta, exc)
        return []
    return sorted(ficheiros, key=lambda p: p.stat().st_mtime, reverse=True)
