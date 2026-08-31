#!/usr/bin/env python3
"""
PT-PT: Pacote de português europeu.
       A ortografia segue o Acordo Ortográfico de 1990, em vigor em Portugal.

       Nota de desenho importante, herdada da primeira versão desta aplicação:
       ela continha centenas de entradas do tipo "paciente" -> "paciente", que
       não faziam nada a não ser gastar uma expressão regular por termo. Regra
       destas tabelas: se a chave for igual ao valor, a entrada não entra. O
       `sanity_check` do pacote base recusa-as.

EN-UK: European Portuguese pack.
       Spelling follows the 1990 Orthographic Agreement, in force in Portugal.

       An important design note, inherited from this application's first
       version: it held hundreds of entries of the form "patient" -> "patient",
       which did nothing but burn one regular expression per term. Rule for
       these tables: if key equals value, the entry does not belong. The base
       pack's `sanity_check` rejects them.

Created by Redfox using Claude
"""

from __future__ import annotations

from . import LanguagePack

# ---------------------------------------------------------------------------
# PT-PT: 1. Correcções ortográficas — erros frequentes de transcrição.
# EN-UK: 1. Spelling corrections — frequent transcription errors.
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
#
#        Os modelos Whisper são treinados maioritariamente com português do
#        Brasil, por isso produzem sistematicamente estas formas. É a correcção
#        de maior impacto de toda a aplicação.
#
# EN-UK: 2. pt-BR -> pt-PT conversions.
#
#        Whisper models are trained predominantly on Brazilian Portuguese and
#        therefore produce these forms systematically. This is the highest
#        impact correction in the whole application.
# ---------------------------------------------------------------------------
REGIONAL_CONVERSIONS: dict[str, str] = {
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
#        Corrigir à cabeça é muito mais eficaz do que corrigir à posteriori com
#        expressões regulares: o termo sai bem logo à primeira.
# EN-UK: 4. Protected vocabulary — passed to the model as initial context.
#        Correcting up front is far more effective than correcting afterwards
#        with regular expressions: the term comes out right first time.
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

PACK = LanguagePack(
    code="pt-PT",
    whisper_code="pt",
    name_native="Português (Portugal)",
    name_en="Portuguese (Portugal)",
    spelling_corrections=SPELLING_CORRECTIONS,
    regional_conversions=REGIONAL_CONVERSIONS,
    regional_label="Português do Brasil → europeu · Brazilian → European Portuguese",
    spoken_punctuation=SPOKEN_PUNCTUATION,
    protected_terms=PROTECTED_TERMS,
    prompt_opening=(
        "Transcrição de consulta médica em português europeu, "
        "com pontuação e acentuação. Vocabulário clínico: "
    ),
)
