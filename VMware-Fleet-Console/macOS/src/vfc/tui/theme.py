#!/usr/bin/env python3
"""
PT-PT: O aspecto da interface.

       Duas decisões que não são gosto:

       **As cores de gravidade são sempre acompanhadas de texto.** O vermelho
       nunca é a única coisa que distingue um crítico de um aviso — há sempre a
       palavra ao lado. Cerca de um em cada doze homens não distingue vermelho
       de verde, e uma ferramenta de operações que comunique o essencial só por
       cor é uma ferramenta que não serve a essa pessoa. Também resolve o
       terminal monocromático e a captura de ecrã impressa a preto e branco que
       vai no relatório.

       **O contraste é alto de propósito.** Isto vai ser lido numa sala de
       servidores, num portátil com brilho no ecrã, e às vezes por cima do
       ombro de alguém. Não é onde os cinzentos subtis funcionam.

EN-UK: The interface's appearance.

       Two decisions that are not taste. **Severity colours always come with
       text**: red is never the only thing separating a critical from a warning.
       About one man in twelve does not distinguish red from green, and an
       operations tool that carries the essential meaning in colour alone is a
       tool that fails that person. It also handles the monochrome terminal and
       the black-and-white printout.

       **Contrast is high on purpose**: this gets read in a server room, on a
       laptop with glare, sometimes over somebody's shoulder. Not where subtle
       greys work.

Created by Redfox using Claude
"""

from __future__ import annotations

CSS = """
Screen {
    background: $surface;
}

#cabecalho-parque {
    height: auto;
    padding: 0 1;
    background: $panel;
    border-bottom: solid $primary;
}

#linha-estado {
    height: 1;
    padding: 0 1;
    background: $panel;
    color: $text-muted;
}

.aviso-licenca {
    padding: 1 2;
    margin: 1 0;
    background: $warning 20%;
    border-left: thick $warning;
    color: $text;
}

.critico { color: $error; text-style: bold; }
.aviso   { color: $warning; }
.info    { color: $text-muted; }
.ok      { color: $success; }

DataTable {
    height: 1fr;
}

DataTable > .datatable--cursor {
    background: $primary;
    color: $text;
}

/* --- PT-PT: Ecrã de ligação / EN-UK: Connection screen ------------------ */

#caixa-ligacao {
    width: 72;
    height: auto;
    padding: 1 2;
    border: round $primary;
    background: $panel;
}

#caixa-ligacao Input {
    margin-bottom: 1;
}

#titulo-ligacao {
    text-style: bold;
    padding-bottom: 1;
}

#servidores-guardados {
    height: auto;
    max-height: 8;
    margin-bottom: 1;
    border: round $primary 50%;
}

#erro-ligacao {
    color: $error;
    padding: 1 0;
    height: auto;
}

/* --- PT-PT: Modais / EN-UK: Modals -------------------------------------- */

ModalScreen {
    align: center middle;
}

#caixa-modal {
    width: 84;
    max-width: 90%;
    height: auto;
    max-height: 80%;
    padding: 1 2;
    border: thick $error;
    background: $panel;
}

#caixa-modal.confianca {
    border: thick $warning;
}

#titulo-modal {
    text-style: bold;
    padding-bottom: 1;
}

#texto-modal {
    height: auto;
    padding-bottom: 1;
}

#impressao-digital {
    padding: 1;
    margin-bottom: 1;
    background: $surface;
    border: round $warning;
    color: $text;
}

#botoes-modal {
    height: auto;
    align-horizontal: right;
}

#botoes-modal Button {
    margin-left: 2;
}

#detalhe {
    height: auto;
    max-height: 14;
    padding: 1;
    border-top: solid $primary 50%;
}
"""
