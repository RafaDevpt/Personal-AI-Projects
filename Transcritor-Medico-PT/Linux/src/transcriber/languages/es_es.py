#!/usr/bin/env python3
"""
PT-PT: Pacote de espanhol de Espanha.

       Mesmo padrão do português e do inglês: o Whisper é treinado sobretudo
       com espanhol da América Latina e escreve "doctor", "chequeo",
       "resfriado", "celular". Num registo clínico espanhol dizem-se outras
       coisas, e a tabela regional trata disso.

       O espanhol tem ainda um problema próprio: o modelo perde regularmente os
       acentos e o "ñ". "Rinon" por "riñón" e "corazon" por "corazón" são os
       erros mais frequentes de todos, e o mais barato de corrigir.

EN-UK: Spain Spanish pack.

       Same pattern as Portuguese and English: Whisper is trained mostly on
       Latin American Spanish and writes "doctor", "chequeo", "resfriado",
       "celular". A Spanish clinical record says other things, and the regional
       table handles it.

       Spanish has a problem of its own too: the model regularly loses accents
       and the "ñ". "Rinon" for "riñón" and "corazon" for "corazón" are the
       commonest errors of all, and the cheapest to fix.

Created by Redfox using Claude
"""

from __future__ import annotations

from . import LanguagePack

# ---------------------------------------------------------------------------
# PT-PT: 1. Correcções ortográficas — sobretudo acentos e "ñ" perdidos.
# EN-UK: 1. Spelling corrections — mostly lost accents and "ñ".
# ---------------------------------------------------------------------------
SPELLING_CORRECTIONS: dict[str, str] = {
    # PT-PT: Acentos perdidos / EN-UK: Dropped accents
    "corazon": "corazón",
    "presion arterial": "presión arterial",
    "saturacion": "saturación",
    "medicacion": "medicación",
    "exploracion": "exploración",
    "evolucion": "evolución",
    "auscultacion": "auscultación",
    "palpitacion": "palpitación",
    "palpitaciones cardiacas": "palpitaciones cardíacas",
    "frecuencia cardiaca": "frecuencia cardíaca",
    "analisis": "análisis",
    "diagnostico": "diagnóstico",
    "pronostico": "pronóstico",
    "cronico": "crónico",
    "cronica": "crónica",
    "clinico": "clínico",
    "clinica": "clínica",
    "quirurgico": "quirúrgico",
    "hepatico": "hepático",
    "gastrico": "gástrico",
    "toracico": "torácico",
    "cefalea tensional cronica": "cefalea tensional crónica",
    "hipertension": "hipertensión",
    "hipotension": "hipotensión",
    "infeccion": "infección",
    "inflamacion": "inflamación",
    "insuficiencia renal cronica": "insuficiencia renal crónica",
    # PT-PT: "ñ" perdido / EN-UK: Lost "ñ"
    "rinon": "riñón",
    "rinones": "riñones",
    "muneca": "muñeca",
    "ninos": "niños",
    "nino": "niño",
    "senal": "señal",
    # PT-PT: Termos partidos ao meio / EN-UK: Terms split in half
    "electro cardiograma": "electrocardiograma",
    "eco cardiograma": "ecocardiograma",
    "anti inflamatorio": "antiinflamatorio",
    "anti biotico": "antibiótico",
    "rayos equis": "rayos X",
}

# ---------------------------------------------------------------------------
# PT-PT: 2. Conversões es-419 (América Latina) -> es-ES.
# EN-UK: 2. es-419 (Latin America) -> es-ES conversions.
# ---------------------------------------------------------------------------
REGIONAL_CONVERSIONS: dict[str, str] = {
    # PT-PT: Clínico / EN-UK: Clinical
    "chequeo": "revisión",
    "chequeo médico": "reconocimiento médico",
    "resfriado común": "catarro",
    "gripa": "gripe",
    "ambulancia de emergencias": "ambulancia",
    "sala de emergencias": "urgencias",
    "emergencias médicas": "urgencias",
    "quirófano de urgencia": "quirófano",
    "enfermera graduada": "enfermera",
    "doctora tratante": "médica responsable",
    "doctor tratante": "médico responsable",
    "curita": "tirita",
    "yeso": "escayola",
    "vendaje adhesivo": "esparadrapo",
    "anteojos": "gafas",
    "lentes": "gafas",
    "computadora": "ordenador",
    "celular": "móvil",
    "jugo": "zumo",
    "papas": "patatas",
    "manejar": "conducir",
    "tomar la presión": "tomar la tensión",
    "presión alta": "tensión alta",
    "diabetes tipo dos": "diabetes tipo 2",
}

# ---------------------------------------------------------------------------
# PT-PT: 3. Pontuação ditada.
# EN-UK: 3. Dictated punctuation.
# ---------------------------------------------------------------------------
SPOKEN_PUNCTUATION: tuple[tuple[str, str], ...] = (
    # PT-PT: Quatro palavras / EN-UK: Four words
    ("punto y aparte nuevo párrafo", "\n\n"),
    # PT-PT: Três palavras / EN-UK: Three words
    ("signo de interrogación", "?"),
    ("signo de exclamación", "!"),
    ("abre signo interrogación", "¿"),
    ("abre signo exclamación", "¡"),
    ("punto y coma", ";"),
    ("punto y aparte", "\n\n"),
    ("punto y seguido", ". "),
    ("abrir paréntesis", "("),
    ("cerrar paréntesis", ")"),
    # PT-PT: Duas palavras / EN-UK: Two words
    ("nuevo párrafo", "\n\n"),
    ("nueva línea", "\n"),
    ("punto final", "."),
    ("dos puntos", ":"),
    ("puntos suspensivos", "..."),
    # PT-PT: Uma palavra / EN-UK: One word
    ("párrafo", "\n\n"),
    ("coma", ","),
    ("guion", "-"),
    ("raya", " — "),
)

# ---------------------------------------------------------------------------
# PT-PT: 4. Vocabulário protegido.
# EN-UK: 4. Protected vocabulary.
# ---------------------------------------------------------------------------
PROTECTED_TERMS: tuple[str, ...] = (
    # PT-PT: Sinais vitais / EN-UK: Vital signs
    "tensión arterial", "frecuencia cardíaca", "saturación de oxígeno",
    "sistólica", "diastólica",
    # PT-PT: Sintomas / EN-UK: Symptoms
    "disnea", "taquicardia", "bradicardia", "palpitaciones", "parestesias",
    "prurito", "edema", "cefalea", "astenia", "disfagia", "síncope",
    # PT-PT: Exames / EN-UK: Investigations
    "electrocardiograma", "ecocardiograma", "ecografía", "tomografía",
    "resonancia magnética", "hemograma", "creatinina",
    "hemoglobina glicosilada", "endoscopia",
    # PT-PT: Patologias / EN-UK: Conditions
    "hipertensión arterial", "diabetes mellitus", "fibrilación auricular",
    "insuficiencia cardíaca", "neumonía", "cardiopatía isquémica",
    "hipotiroidismo", "artrosis", "migraña",
    # PT-PT: Terapêutica / EN-UK: Therapeutics
    "antiinflamatorio", "anticoagulante", "ansiolítico", "corticoide",
    "paracetamol", "ibuprofeno", "amoxicilina", "metformina", "omeprazol",
    "enalapril", "simvastatina",
    # PT-PT: Estrutura da consulta / EN-UK: Consultation structure
    "motivo de consulta", "antecedentes personales", "tratamiento habitual",
    "alergias conocidas", "exploración física", "juicio clínico",
    "plan terapéutico", "ingreso hospitalario", "alta médica", "seguimiento",
)

PACK = LanguagePack(
    code="es-ES",
    whisper_code="es",
    name_native="Español (España)",
    name_en="Spanish (Spain)",
    spelling_corrections=SPELLING_CORRECTIONS,
    regional_conversions=REGIONAL_CONVERSIONS,
    regional_label="Español latinoamericano → de España · Latin American → Spain Spanish",
    spoken_punctuation=SPOKEN_PUNCTUATION,
    protected_terms=PROTECTED_TERMS,
    prompt_opening=(
        "Transcripción de una consulta médica en español de España, "
        "con puntuación y acentuación. Vocabulario clínico: "
    ),
)
