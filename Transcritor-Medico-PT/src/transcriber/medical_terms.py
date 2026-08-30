#!/usr/bin/env python3
"""
PT-PT: Vocabulário médico em português europeu.
       Este módulo contém apenas dados — sem lógica — para que possa ser
       revisto por pessoal clínico sem necessidade de perceber de código.
       A ortografia segue o Acordo Ortográfico de 1990, em vigor em Portugal.

EN-UK: European Portuguese medical vocabulary.
       This module holds data only — no logic — so that it can be reviewed by
       clinical staff without any need to understand the code.
       Spelling follows the 1990 Orthographic Agreement, in force in Portugal.

PT-PT: Nota de desenho importante. A versão anterior desta aplicação continha
       centenas de entradas do tipo "paciente" -> "paciente", que não faziam
       nada a não ser gastar tempo de CPU numa expressão regular por termo.
       Regra desta tabela: se a chave for igual ao valor, a entrada não entra.
       Os dados estão separados em quatro estruturas com propósitos distintos.

EN-UK: Important design note. The previous version of this application held
       hundreds of entries of the form "paciente" -> "paciente", which did
       nothing but burn CPU time on one regular expression per term.
       Rule for these tables: if key equals value, the entry does not belong.
       The data is split into four structures with distinct purposes.

Created by Redfox using Claude
"""

from __future__ import annotations

from itertools import pairwise

# ---------------------------------------------------------------------------
# PT-PT: 1. Correcções ortográficas — erros frequentes de transcrição.
# EN-UK: 1. Spelling corrections — frequent transcription errors.
#
# PT-PT: Chave = forma errada; valor = forma correcta. Correspondência feita
#        sem distinguir maiúsculas, por palavras inteiras.
# EN-UK: Key = incorrect form; value = correct form. Matched case-insensitively
#        on whole words.
# ---------------------------------------------------------------------------
SPELLING_CORRECTIONS: dict[str, str] = {
    # PT-PT: Erros de escuta / EN-UK: Mishearings
    "paciente presenta": "paciente apresenta",
    "presenta": "apresenta",
    "ultrasssom": "ultrassom",
    "biópia": "biópsia",
    "biopia": "biópsia",
    "espinhal medula": "espinal medula",
    # PT-PT: Hifenização e aglutinação / EN-UK: Hyphenation and compounding
    "raio x": "raio-x",
    "anti inflamatório": "anti-inflamatório",
    "anti biótico": "antibiótico",
    "eletro cardiograma": "eletrocardiograma",
    "eco cardiograma": "ecocardiograma",
    "electrocardiograma": "eletrocardiograma",
    # PT-PT: Acentos perdidos pelo modelo / EN-UK: Accents dropped by the model
    "ressonancia magnetica": "ressonância magnética",
    "tensao arterial": "tensão arterial",
    "pressao arterial": "pressão arterial",
    "frequencia cardiaca": "frequência cardíaca",
    "saturacao": "saturação",
    "medicacao": "medicação",
    "recomendacao": "recomendação",
    "analise": "análise",
    "analises": "análises",
    "diagnostico": "diagnóstico",
    "prognostico": "prognóstico",
    "obstipacao": "obstipação",
    "insonia": "insónia",
    # PT-PT: Formas pré-Acordo ainda produzidas pelo modelo.
    # EN-UK: Pre-Agreement forms the model still produces.
    "infecção": "infeção",
    "infeccao": "infeção",
    "injecção": "injeção",
    "injeccao": "injeção",
    "objectivo": "objetivo",
    "acta": "ata",
}

# ---------------------------------------------------------------------------
# PT-PT: 2. Conversões pt-BR -> pt-PT.
# EN-UK: 2. pt-BR -> pt-PT conversions.
#
# PT-PT: Os modelos Whisper são treinados maioritariamente com português do
#        Brasil, por isso produzem sistematicamente estas formas. É a correcção
#        de maior impacto de toda a aplicação.
# EN-UK: Whisper models are trained predominantly on Brazilian Portuguese and
#        therefore produce these forms systematically. This is the highest
#        impact correction in the whole application.
# ---------------------------------------------------------------------------
BRAZILIAN_TO_EUROPEAN: dict[str, str] = {
    # PT-PT: Clínico / EN-UK: Clinical
    "vômito": "vómito",
    "vômitos": "vómitos",
    "vomito": "vómito",
    "câncer": "cancro",
    "coceira": "comichão",
    "curativo": "penso",
    "curativos": "pensos",
    "esparadrapo": "adesivo",
    "prontuário": "processo clínico",
    "aids": "SIDA",
    "hiv": "VIH",
    "enfaixar": "ligar",
    "gesso ortopédico": "tala de gesso",
    "pronto socorro": "urgência",
    "pronto-socorro": "urgência",
    "plantão": "turno",
    "plantonista": "médico de serviço",
    "leito": "cama",
    "leitos": "camas",
    "estresse": "stress",
    "estressado": "stressado",
    "fumante": "fumador",
    "fumantes": "fumadora",
    # PT-PT: Geral / EN-UK: General
    "usuário": "utente",
    "usuária": "utente",
    "registro": "registo",
    "registros": "registos",
    "arquivo": "ficheiro",
    "planejamento": "planeamento",
    "café da manhã": "pequeno-almoço",
    "tela": "ecrã",
}

# ---------------------------------------------------------------------------
# PT-PT: 3. Pontuação ditada. Em ditado clínico é prática corrente dizer os
#        sinais de pontuação em voz alta; o modelo transcreve-os como palavras.
# EN-UK: 3. Dictated punctuation. In clinical dictation it is standard practice
#        to speak the punctuation aloud; the model transcribes it as words.
#
# PT-PT: A ordem importa: as expressões mais longas têm de ser processadas
#        primeiro, senão "ponto parágrafo" seria partido por "ponto".
# EN-UK: Order matters: longer expressions must be processed first, otherwise
#        "ponto parágrafo" would be broken up by "ponto".
# ---------------------------------------------------------------------------
SPOKEN_PUNCTUATION: tuple[tuple[str, str], ...] = (
    # PT-PT: Três palavras / EN-UK: Three words
    ("ponto de interrogação", "?"),
    ("ponto de exclamação", "!"),
    ("ponto e vírgula", ";"),
    # PT-PT: Duas palavras / EN-UK: Two words
    ("ponto parágrafo", "\n\n"),
    ("novo parágrafo", "\n\n"),
    ("nova linha", "\n"),
    ("ponto final", "."),
    ("dois pontos", ":"),
    ("abre parêntesis", "("),
    ("fecha parêntesis", ")"),
    # PT-PT: Uma palavra / EN-UK: One word
    ("parágrafo", "\n\n"),
    ("reticências", "..."),
    ("vírgula", ","),
    ("travessão", " — "),
    ("hífen", "-"),
)

# ---------------------------------------------------------------------------
# PT-PT: 4. Vocabulário protegido — passado ao modelo como contexto inicial.
# EN-UK: 4. Protected vocabulary — passed to the model as initial context.
#
# PT-PT: O faster-whisper aceita um "initial_prompt" que enviesa a
#        descodificação em favor deste vocabulário. Corrigir à cabeça é muito
#        mais eficaz do que corrigir à posteriori com regex: o termo sai bem
#        logo à primeira. Manter abaixo de ~200 palavras — o prompt está
#        limitado a 224 tokens e o excesso é truncado silenciosamente.
# EN-UK: faster-whisper accepts an "initial_prompt" that biases decoding
#        towards this vocabulary. Correcting up front is far more effective
#        than correcting afterwards with regexes: the term comes out right
#        first time. Keep under roughly 200 words — the prompt is capped at
#        224 tokens and anything beyond is silently truncated.
# ---------------------------------------------------------------------------
PROTECTED_TERMS: tuple[str, ...] = (
    # PT-PT: Sinais vitais / EN-UK: Vital signs
    "tensão arterial", "frequência cardíaca", "saturação", "sistólica",
    "diastólica",
    # PT-PT: Sintomas / EN-UK: Symptoms
    "dispneia", "taquicardia", "bradicardia", "palpitações", "vertigem",
    "parestesias", "prurido", "edema", "cefaleia", "astenia", "toracalgia",
    "lombalgia", "disfagia",
    # PT-PT: Exames / EN-UK: Investigations
    "eletrocardiograma", "ecocardiograma", "ecografia", "tomografia",
    "ressonância magnética", "endoscopia", "hemograma", "creatinina",
    "hemoglobina glicada", "triglicéridos",
    # PT-PT: Patologias / EN-UK: Conditions
    "hipertensão arterial", "diabetes mellitus", "pneumonia", "obstipação",
    "insónia", "enxaqueca", "osteoporose", "artrose",
    "insuficiência cardíaca", "fibrilhação auricular", "cancro",
    # PT-PT: Terapêutica / EN-UK: Therapeutics
    "anti-inflamatório", "anticoagulante", "ansiolítico", "corticosteroide",
    "paracetamol", "ibuprofeno", "amoxicilina", "metformina",
    # PT-PT: Estrutura da consulta / EN-UK: Consultation structure
    "história clínica", "antecedentes pessoais", "medicação habitual",
    "alergias conhecidas", "exame objetivo", "hipótese diagnóstica",
    "plano terapêutico", "internamento", "alta clínica", "seguimento",
)


# PT-PT: Orçamento de caracteres para o contexto inicial. O Whisper aceita 224
#        tokens; em português cada token vale grosso modo 3 caracteres, pelo que
#        700 caracteres deixam margem de segurança. Acima disto o modelo trunca
#        sem avisar, e os termos do fim da lista deixam de ter qualquer efeito.
# EN-UK: Character budget for the initial context. Whisper accepts 224 tokens;
#        in Portuguese a token is worth roughly 3 characters, so 700 characters
#        leave a safety margin. Beyond this the model truncates without warning
#        and terms at the end of the list stop having any effect at all.
MAX_PROMPT_CHARS: int = 700

_PROMPT_OPENING: str = (
    "Transcrição de consulta médica em português europeu, "
    "com pontuação e acentuação. Vocabulário clínico: "
)


def build_initial_prompt(max_chars: int = MAX_PROMPT_CHARS) -> str:
    """
    PT-PT: Constrói o contexto inicial entregue ao modelo de transcrição.
           A frase de abertura em português europeu é intencional: sinaliza ao
           modelo a variante linguística pretendida antes de ver o áudio, e é
           o que mais reduz o número de brasileirismos na saída.
           Os termos são acrescentados até ao limite de caracteres, sempre em
           palavras inteiras — cortar um termo a meio confundiria o modelo.

    EN-UK: Builds the initial context handed to the transcription model.
           The opening sentence in European Portuguese is deliberate: it
           signals the intended language variant to the model before it sees
           the audio, and does more than anything else to cut the number of
           Brazilianisms in the output.
           Terms are added up to the character limit, always as whole words —
           cutting a term in half would only confuse the model.

    :param max_chars:
        PT-PT: Limite de caracteres do contexto devolvido.
        EN-UK: Character limit of the returned context.
    :return:
        PT-PT: Texto de contexto pronto a passar ao parâmetro initial_prompt.
        EN-UK: Context text ready to pass to the initial_prompt parameter.
    """
    parts: list[str] = []
    used = len(_PROMPT_OPENING) + 1  # PT-PT: +1 para o ponto final / EN-UK: +1 for the full stop

    for term in PROTECTED_TERMS:
        # PT-PT: +2 pela vírgula e espaço que separam os termos.
        # EN-UK: +2 for the comma and space separating the terms.
        cost = len(term) + 2
        if used + cost > max_chars:
            break
        parts.append(term)
        used += cost

    return _PROMPT_OPENING + ", ".join(parts) + "."


def sanity_check() -> list[str]:
    """
    PT-PT: Verifica a coerência das tabelas e devolve a lista de problemas.
           Chamada pelos testes automáticos para impedir que voltem a entrar
           entradas inúteis (chave igual ao valor) neste ficheiro.

    EN-UK: Checks the consistency of the tables and returns a list of problems.
           Called by the automated tests to stop useless entries (key equal to
           value) from creeping back into this file.

    :return:
        PT-PT: Lista de descrições de problemas; vazia significa tudo bem.
        EN-UK: List of problem descriptions; empty means all is well.
    """
    problems: list[str] = []

    for name, table in (
        ("SPELLING_CORRECTIONS", SPELLING_CORRECTIONS),
        ("BRAZILIAN_TO_EUROPEAN", BRAZILIAN_TO_EUROPEAN),
    ):
        for wrong, right in table.items():
            if wrong == right:
                problems.append(f"{name}: entrada inútil {wrong!r} -> {right!r}")
            if not wrong.strip() or not right.strip():
                problems.append(f"{name}: entrada vazia {wrong!r} -> {right!r}")

    # PT-PT: A pontuação ditada tem de estar ordenada da expressão mais longa
    #        para a mais curta, senão a substituição parte frases a meio.
    # EN-UK: Dictated punctuation must run from longest to shortest expression,
    #        otherwise replacement cuts phrases in half.
    lengths = [len(phrase.split()) for phrase, _ in SPOKEN_PUNCTUATION]
    for earlier, later in pairwise(lengths):
        if later > earlier:
            problems.append(
                "SPOKEN_PUNCTUATION: expressões têm de estar ordenadas da mais "
                "longa para a mais curta."
            )
            break

    return problems
