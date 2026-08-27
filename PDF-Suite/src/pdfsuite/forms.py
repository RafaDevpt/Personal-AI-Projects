# -*- coding: utf-8 -*-
"""
PT-PT: Escrita dos campos no PDF.

       Um PDF preenchivel e um PDF normal com duas coisas a mais: anotacoes do
       tipo Widget em cada pagina, e um dicionario AcroForm no catalogo a
       listar todos os campos. Este modulo escreve as duas, com o pypdf.

       Duas decisoes que valem explicacao.

       `NeedAppearances` fica a verdadeiro. E uma bandeira que diz ao leitor de
       PDF «gera tu o aspecto dos campos». A alternativa era desenhar a mao o
       fluxo de aparencia de cada campo em cada estado, o que significa
       reimplementar a composicao de texto — quebra de linha, alinhamento,
       recorte — e obter um resultado pior do que o do Acrobat. Com a bandeira,
       o leitor faz isso e faz melhor. O custo esta assinalado no README: alguns
       visualizadores muito simples ignoram-na e mostram o campo vazio ate lhe
       tocarem.

       As caixas de seleccao sao a excepcao. Essas levam fluxo de aparencia
       escrito a mao, porque um leitor que ignore o `NeedAppearances` numa
       caixa de texto mostra-a vazia — que e o estado correcto — mas numa caixa
       de seleccao mostra-a sem sequer a moldura, e o utilizador nao ve que ha
       ali algo para clicar.

EN-UK: Writing the fields into the PDF.

       A fillable PDF is a normal PDF with two additions: Widget annotations on
       each page, and an AcroForm dictionary in the catalogue listing every
       field. This module writes both, using pypdf.

       Two decisions worth explaining.

       `NeedAppearances` is set to true. It tells the reader "you generate the
       look of the fields". The alternative was hand-drawing an appearance
       stream per field per state, which means reimplementing text layout and
       getting a worse result than Acrobat's.

       Tick boxes are the exception and do carry hand-written appearance
       streams: a reader ignoring `NeedAppearances` shows an empty text box —
       the correct state — but shows a tick box with no frame at all, and the
       user cannot see there is anything to click.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from .models import Campo, TipoCampo

log = logging.getLogger(__name__)

# PT-PT: Bandeiras do campo (`/Ff`), tal como definidas na norma do PDF.
# EN-UK: Field flags (`/Ff`), as defined in the PDF specification.
FF_SO_LEITURA = 1 << 0
FF_OBRIGATORIO = 1 << 1
FF_MULTILINHA = 1 << 12
FF_COMBO = 1 << 17

# PT-PT: Bandeiras da anotacao (`/F`). 4 = imprimivel. Sem esta bandeira o
#        campo aparece no ecra e desaparece na impressao — o que num formulario
#        preenchido e a pior falha possivel, porque so se descobre depois de
#        estar assinado e entregue em papel.
# EN-UK: Annotation flags (`/F`). 4 = printable. Without it the field shows on
#        screen and vanishes when printed, which on a completed form is the
#        worst possible failure: it is only discovered after the paper copy is
#        signed and handed over.
F_IMPRIMIVEL = 4

COR_BORDA = (0.45, 0.45, 0.50)
COR_FUNDO = (0.94, 0.95, 0.98)
TAMANHO_LETRA = 10


def _rect(campo: Campo) -> ArrayObject:
    """PT-PT: Rectangulo da anotacao. / EN-UK: The annotation rectangle."""
    return ArrayObject(
        [FloatObject(campo.x0), FloatObject(campo.y0), FloatObject(campo.x1), FloatObject(campo.y1)]
    )


def _aparencia_marca(escrita: PdfWriter, largura: float, altura: float, marcada: bool):
    """
    PT-PT: Fluxo de aparencia de uma caixa de seleccao.

           Desenha a moldura sempre e a cruz so no estado marcado. A cruz e
           feita com dois tracos em vez do caracter de visto da ZapfDingbats:
           o visto obriga a declarar essa letra nos recursos do documento e,
           quando o leitor nao a tem, aparece um rectangulo vazio no lugar.
           Dois tracos desenhados nao dependem de letra nenhuma.

    EN-UK: A tick box's appearance stream. Draws the frame always and the cross
           only in the checked state. The cross is two strokes rather than the
           ZapfDingbats tick character: the tick requires declaring that font in
           the document resources and shows as an empty rectangle when the
           reader lacks it.
    """
    borda = f"{COR_BORDA[0]} {COR_BORDA[1]} {COR_BORDA[2]} RG"
    fundo = f"{COR_FUNDO[0]} {COR_FUNDO[1]} {COR_FUNDO[2]} rg"

    comandos = [
        "q",
        fundo,
        f"0 0 {largura:.2f} {altura:.2f} re f",
        borda,
        "0.8 w",
        f"0.4 0.4 {largura - 0.8:.2f} {altura - 0.8:.2f} re S",
    ]

    if marcada:
        folga = min(largura, altura) * 0.28
        comandos += [
            "0.1 0.1 0.1 RG",
            "1.4 w",
            f"{folga:.2f} {folga:.2f} m {largura - folga:.2f} {altura - folga:.2f} l S",
            f"{folga:.2f} {altura - folga:.2f} m {largura - folga:.2f} {folga:.2f} l S",
        ]

    comandos.append("Q")

    fluxo = DecodedStreamObject()
    fluxo.set_data("\n".join(comandos).encode("latin-1"))
    fluxo[NameObject("/Type")] = NameObject("/XObject")
    fluxo[NameObject("/Subtype")] = NameObject("/Form")
    fluxo[NameObject("/BBox")] = ArrayObject(
        [FloatObject(0), FloatObject(0), FloatObject(largura), FloatObject(altura)]
    )
    fluxo[NameObject("/Resources")] = DictionaryObject()
    return escrita._add_object(fluxo)


def _widget_base(campo: Campo, referencia_pagina) -> DictionaryObject:
    """PT-PT: Parte comum a todos os widgets. / EN-UK: Common to every widget."""
    widget = DictionaryObject()
    widget[NameObject("/Type")] = NameObject("/Annot")
    widget[NameObject("/Subtype")] = NameObject("/Widget")
    widget[NameObject("/Rect")] = _rect(campo)
    widget[NameObject("/T")] = TextStringObject(campo.nome)
    widget[NameObject("/F")] = NumberObject(F_IMPRIMIVEL)
    widget[NameObject("/P")] = referencia_pagina

    if campo.etiqueta:
        # PT-PT: `/TU` e o texto que aparece ao passar o rato e o que os
        #        leitores de ecra anunciam. Custa uma linha e e a diferenca
        #        entre um formulario acessivel e um formulario que so faz
        #        sentido a quem esta a ver a pagina.
        # EN-UK: `/TU` is the tooltip and what screen readers announce. It costs
        #        one line and is the difference between an accessible form and
        #        one that only makes sense to somebody looking at the page.
        widget[NameObject("/TU")] = TextStringObject(campo.etiqueta)

    aparencia = DictionaryObject()
    aparencia[NameObject("/BC")] = ArrayObject([FloatObject(c) for c in COR_BORDA])
    aparencia[NameObject("/BG")] = ArrayObject([FloatObject(c) for c in COR_FUNDO])
    widget[NameObject("/MK")] = aparencia

    return widget


def _widget_texto(escrita: PdfWriter, campo: Campo, referencia_pagina) -> DictionaryObject:
    """PT-PT: Campo de texto, data ou assinatura. / EN-UK: Text, date or signature."""
    widget = _widget_base(campo, referencia_pagina)
    widget[NameObject("/FT")] = NameObject("/Tx")
    widget[NameObject("/V")] = TextStringObject("")
    widget[NameObject("/DA")] = TextStringObject(f"/Helv {TAMANHO_LETRA} Tf 0 g")

    bandeiras = 0
    if campo.tipo is TipoCampo.MULTILINHA:
        bandeiras |= FF_MULTILINHA
    if campo.obrigatorio:
        bandeiras |= FF_OBRIGATORIO
    widget[NameObject("/Ff")] = NumberObject(bandeiras)

    if campo.tipo is TipoCampo.DATA:
        # PT-PT: Formato imposto pelo proprio PDF, em JavaScript. Sem isto, num
        #        formulario preenchido por vinte pessoas aparecem seis formatos
        #        de data diferentes e a coluna deixa de ser ordenavel.
        # EN-UK: Format enforced by the PDF itself, in JavaScript. Without it, a
        #        form filled in by twenty people comes back with six different
        #        date formats.
        accao = DictionaryObject()
        formato = DictionaryObject()
        formato[NameObject("/S")] = NameObject("/JavaScript")
        formato[NameObject("/JS")] = TextStringObject("AFDate_FormatEx('dd/mm/yyyy');")
        validacao = DictionaryObject()
        validacao[NameObject("/S")] = NameObject("/JavaScript")
        validacao[NameObject("/JS")] = TextStringObject("AFDate_KeystrokeEx('dd/mm/yyyy');")
        accao[NameObject("/F")] = escrita._add_object(formato)
        accao[NameObject("/K")] = escrita._add_object(validacao)
        widget[NameObject("/AA")] = accao
        widget[NameObject("/TU")] = TextStringObject(
            f"{campo.etiqueta or 'Data'} (dd/mm/aaaa)".strip()
        )

    if campo.tipo is TipoCampo.ASSINATURA:
        widget[NameObject("/TU")] = TextStringObject(
            f"{campo.etiqueta or 'Assinatura'} — escreva o nome ou assine depois de imprimir"
        )

    return widget


def _widget_caixa(escrita: PdfWriter, campo: Campo, referencia_pagina) -> DictionaryObject:
    """PT-PT: Caixa de seleccao. / EN-UK: Tick box."""
    widget = _widget_base(campo, referencia_pagina)
    widget[NameObject("/FT")] = NameObject("/Btn")
    widget[NameObject("/V")] = NameObject("/Off")
    widget[NameObject("/AS")] = NameObject("/Off")
    widget[NameObject("/DA")] = TextStringObject("/Helv 0 Tf 0 g")
    widget[NameObject("/Ff")] = NumberObject(FF_OBRIGATORIO if campo.obrigatorio else 0)

    largura = max(campo.largura, 6)
    altura = max(campo.altura, 6)

    estados = DictionaryObject()
    estados[NameObject("/Sim")] = _aparencia_marca(escrita, largura, altura, True)
    estados[NameObject("/Off")] = _aparencia_marca(escrita, largura, altura, False)

    aparencia = DictionaryObject()
    aparencia[NameObject("/N")] = estados
    widget[NameObject("/AP")] = aparencia

    return widget


def _widget_escolha(escrita: PdfWriter, campo: Campo, referencia_pagina) -> DictionaryObject:
    """PT-PT: Lista de opcoes. / EN-UK: Dropdown list."""
    widget = _widget_base(campo, referencia_pagina)
    widget[NameObject("/FT")] = NameObject("/Ch")
    widget[NameObject("/V")] = TextStringObject("")
    widget[NameObject("/DA")] = TextStringObject(f"/Helv {TAMANHO_LETRA} Tf 0 g")
    widget[NameObject("/Ff")] = NumberObject(
        FF_COMBO | (FF_OBRIGATORIO if campo.obrigatorio else 0)
    )
    widget[NameObject("/Opt")] = ArrayObject(
        [TextStringObject(o) for o in campo.opcoes]
    )
    return widget


def _recursos_do_formulario() -> DictionaryObject:
    """
    PT-PT: Recursos partilhados pelos campos: a letra Helvetica.

           Tem de estar declarada aqui, no `/DR` do AcroForm, e nao apenas
           referida no `/DA` de cada campo. Um leitor que encontre `/Helv` sem
           a encontrar nos recursos ou nao mostra o texto ou escolhe uma letra
           ao acaso — e ai o formulario abre com aspectos diferentes em cada
           maquina.

    EN-UK: Resources shared by the fields: the Helvetica font. It must be
           declared here, in the AcroForm's `/DR`, not merely referenced in each
           field's `/DA`. A reader that meets `/Helv` without finding it in the
           resources either shows no text or picks a font at random.
    """
    letra = DictionaryObject()
    letra[NameObject("/Type")] = NameObject("/Font")
    letra[NameObject("/Subtype")] = NameObject("/Type1")
    letra[NameObject("/BaseFont")] = NameObject("/Helvetica")
    letra[NameObject("/Encoding")] = NameObject("/WinAnsiEncoding")

    # PT-PT: A ZapfDingbats e a letra dos simbolos de visto. Nao a usamos para
    #        desenhar — as caixas levam fluxo de aparencia proprio — mas os
    #        leitores que regeneram as aparencias das caixas de seleccao
    #        procuram-na por reflexo. Sem ela declarada, o poppler avisa
    #        «Unknown font tag ZaDb» e o Acrobat mostra um rectangulo vazio no
    #        lugar do visto. Declara-la custa quatro linhas.
    # EN-UK: ZapfDingbats is the tick symbol font. We do not draw with it — tick
    #        boxes carry their own appearance streams — but readers that
    #        regenerate tick box appearances reach for it by reflex. Without it
    #        declared, poppler warns and Acrobat shows an empty rectangle where
    #        the tick should be.
    simbolos = DictionaryObject()
    simbolos[NameObject("/Type")] = NameObject("/Font")
    simbolos[NameObject("/Subtype")] = NameObject("/Type1")
    simbolos[NameObject("/BaseFont")] = NameObject("/ZapfDingbats")

    letras = DictionaryObject()
    letras[NameObject("/Helv")] = letra
    letras[NameObject("/ZaDb")] = simbolos

    recursos = DictionaryObject()
    recursos[NameObject("/Font")] = letras
    return recursos


def tem_formulario(caminho: Path | str) -> int:
    """
    PT-PT: Quantos campos ja existem no PDF.

           Vale a pena verificar antes de acrescentar: um PDF que ja e
           preenchivel nao precisa de ser convertido, e sobrepor campos novos
           aos antigos produz um formulario onde metade dos campos nao grava.

    EN-UK: How many fields the PDF already has. Worth checking before adding:
           a PDF that is already fillable does not need converting, and layering
           new fields over old ones produces a form where half the fields do not
           save.
    """
    try:
        leitor = PdfReader(str(caminho))
        campos = leitor.get_fields()
        return len(campos) if campos else 0
    except Exception as exc:  # noqa: BLE001
        log.debug("Não foi possível verificar campos em %s: %s", caminho, exc)
        return 0


def criar_formulario(
    origem: Path | str,
    destino: Path | str,
    campos: list[Campo],
    substituir_existentes: bool = False,
) -> tuple[int, list[str]]:
    """
    PT-PT: Grava uma copia do PDF com os campos indicados.

    EN-UK: Writes a copy of the PDF carrying the given fields.

    :param substituir_existentes:
        PT-PT: Se o PDF ja tiver campos, remove-os antes de acrescentar os
               novos. Por omissao os campos novos juntam-se aos existentes.
        EN-UK: If the PDF already has fields, remove them before adding the new
               ones. By default new fields join the existing ones.
    :return:
        PT-PT: (campos escritos, avisos).
        EN-UK: (fields written, warnings).
    """
    origem = Path(origem)
    destino = Path(destino)
    avisos: list[str] = []

    leitor = PdfReader(str(origem))
    escrita = PdfWriter()

    if leitor.is_encrypted:
        # PT-PT: Um PDF protegido so por dono abre sem password mas nao se
        #        deixa modificar. Tentar com password vazia resolve esse caso,
        #        que e o mais comum em documentos de fornecedores.
        # EN-UK: An owner-protected PDF opens without a password but refuses
        #        modification. Trying an empty password covers that case.
        try:
            if not leitor.decrypt(""):
                raise ValueError("O PDF está protegido por password.")
            avisos.append(
                "O PDF tinha protecção contra alterações. Foi aberto e o ficheiro "
                "gerado fica sem essa protecção."
            )
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"O PDF está protegido e não pode ser modificado: {exc}"
            ) from exc

    for pagina in leitor.pages:
        escrita.add_page(pagina)

    existentes = 0
    if substituir_existentes:
        for pagina in escrita.pages:
            if "/Annots" in pagina:
                anotacoes = pagina["/Annots"]
                mantidas = ArrayObject()
                for referencia in anotacoes:
                    try:
                        objecto = referencia.get_object()
                        if objecto.get("/Subtype") == "/Widget":
                            existentes += 1
                            continue
                    except Exception:  # noqa: BLE001
                        pass
                    mantidas.append(referencia)
                pagina[NameObject("/Annots")] = mantidas
        if existentes:
            avisos.append(f"Removidos {existentes} campo(s) que já existiam no PDF.")

    lista_campos = ArrayObject()
    escritos = 0

    for campo in campos:
        campo.normalizar()

        if not campo.valido():
            avisos.append(
                f"Campo «{campo.nome or campo.etiqueta or '?'}» ignorado: "
                "área demasiado pequena para ser utilizável."
            )
            continue

        if not 0 <= campo.pagina < len(escrita.pages):
            avisos.append(
                f"Campo «{campo.nome}» ignorado: aponta para a página "
                f"{campo.pagina + 1}, que não existe neste PDF."
            )
            continue

        pagina = escrita.pages[campo.pagina]
        referencia_pagina = pagina.indirect_reference

        if campo.tipo is TipoCampo.CAIXA:
            widget = _widget_caixa(escrita, campo, referencia_pagina)
        elif campo.tipo is TipoCampo.ESCOLHA and campo.opcoes:
            widget = _widget_escolha(escrita, campo, referencia_pagina)
        else:
            if campo.tipo is TipoCampo.ESCOLHA:
                avisos.append(
                    f"Campo «{campo.nome}» era uma lista sem opções definidas; "
                    "foi gravado como campo de texto."
                )
            widget = _widget_texto(escrita, campo, referencia_pagina)

        referencia = escrita._add_object(widget)

        if "/Annots" not in pagina:
            pagina[NameObject("/Annots")] = ArrayObject()
        pagina[NameObject("/Annots")].append(referencia)
        lista_campos.append(referencia)
        escritos += 1

    if not escritos:
        raise ValueError(
            "Nenhum campo válido para gravar. Verifique a lista antes de continuar."
        )

    formulario = DictionaryObject()
    formulario[NameObject("/Fields")] = lista_campos
    formulario[NameObject("/DR")] = _recursos_do_formulario()
    formulario[NameObject("/DA")] = TextStringObject(f"/Helv {TAMANHO_LETRA} Tf 0 g")
    formulario[NameObject("/NeedAppearances")] = BooleanObject(True)
    # PT-PT: 3 significa «campos e anotacoes visiveis e imprimiveis».
    # EN-UK: 3 means "fields and annotations visible and printable".
    formulario[NameObject("/SigFlags")] = NumberObject(0)

    catalogo = escrita._root_object
    if "/AcroForm" in catalogo and not substituir_existentes:
        # PT-PT: Ja havia formulario: juntar os campos novos a lista existente
        #        em vez de a substituir, senao os campos antigos deixam de estar
        #        listados e a maioria dos leitores para de os gravar.
        # EN-UK: A form already existed: append to the list rather than replace
        #        it, or the old fields stop being listed and most readers stop
        #        saving them.
        try:
            antigo = catalogo["/AcroForm"]
            anteriores = antigo.get("/Fields", ArrayObject())
            for referencia in anteriores:
                lista_campos.append(referencia)
            antigo[NameObject("/Fields")] = lista_campos
            antigo[NameObject("/NeedAppearances")] = BooleanObject(True)
            if "/DR" not in antigo:
                antigo[NameObject("/DR")] = _recursos_do_formulario()
            avisos.append(
                f"O PDF já tinha {len(anteriores)} campo(s); os novos foram acrescentados."
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Não foi possível juntar ao AcroForm existente: %s", exc)
            catalogo[NameObject("/AcroForm")] = escrita._add_object(formulario)
    else:
        catalogo[NameObject("/AcroForm")] = escrita._add_object(formulario)

    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as ficheiro:
        escrita.write(ficheiro)

    log.info("Formulário gravado em %s com %d campo(s).", destino, escritos)
    return escritos, avisos


def preencher(
    origem: Path | str, destino: Path | str, valores: dict[str, str], achatar: bool = False
) -> int:
    """
    PT-PT: Preenche um PDF ja preenchivel com valores.

           Serve para gerar em serie: o mesmo formulario com os dados de vinte
           pessoas, sem ninguem escrever nada. `achatar` transforma os campos em
           conteudo fixo da pagina, para o documento seguir sem poder ser
           alterado.

    EN-UK: Fills an already-fillable PDF with values. Meant for batch
           generation: the same form with twenty people's data, with nobody
           typing anything. `achatar` turns the fields into fixed page content.
    """
    leitor = PdfReader(str(origem))
    escrita = PdfWriter()
    escrita.append(leitor)

    escritos = 0
    for pagina in escrita.pages:
        try:
            escrita.update_page_form_field_values(pagina, valores, auto_regenerate=False)
            escritos = len(valores)
        except Exception as exc:  # noqa: BLE001
            log.warning("Falha ao preencher uma página: %s", exc)

    if "/AcroForm" in escrita._root_object:
        escrita._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(
            not achatar
        )

    if achatar:
        # PT-PT: Achatar a serio — converter cada campo em conteudo da pagina —
        #        obriga a gerar o fluxo de aparencia de cada valor, o que e o
        #        trabalho que o NeedAppearances existe para evitar. A alternativa
        #        honesta e marcar os campos como so-leitura: o resultado visivel
        #        e o mesmo, ninguem altera o documento, e nao ha risco de o
        #        texto sair diferente do que estava no ecra.
        # EN-UK: Genuine flattening requires generating an appearance stream per
        #        value, which is the work NeedAppearances exists to avoid. The
        #        honest alternative is marking the fields read-only: the visible
        #        result is the same and there is no risk of the text coming out
        #        different from what was on screen.
        for pagina in escrita.pages:
            for referencia in pagina.get("/Annots", []) or []:
                try:
                    objecto = referencia.get_object()
                    if objecto.get("/Subtype") == "/Widget":
                        actuais = int(objecto.get("/Ff", 0))
                        objecto[NameObject("/Ff")] = NumberObject(actuais | FF_SO_LEITURA)
                except Exception:  # noqa: BLE001
                    continue

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as ficheiro:
        escrita.write(ficheiro)

    return escritos


def listar_campos(caminho: Path | str) -> list[tuple[str, str, str]]:
    """
    PT-PT: Campos de um PDF preenchivel: (nome, tipo, valor).
           Usado para verificar o resultado e para exportar os dados de
           formularios ja preenchidos.
    EN-UK: A fillable PDF's fields: (name, type, value). Used to check the
           result and to export data from forms already filled in.
    """
    try:
        leitor = PdfReader(str(caminho))
        campos = leitor.get_fields() or {}
    except Exception as exc:  # noqa: BLE001
        log.warning("Não foi possível ler os campos de %s: %s", caminho, exc)
        return []

    tipos = {"/Tx": "Texto", "/Btn": "Caixa", "/Ch": "Lista", "/Sig": "Assinatura"}
    resultado = []
    for nome, dados in campos.items():
        tipo = tipos.get(str(dados.get("/FT", "")), "?")
        valor = dados.get("/V", "")
        resultado.append((str(nome), tipo, str(valor) if valor is not None else ""))
    return sorted(resultado)
