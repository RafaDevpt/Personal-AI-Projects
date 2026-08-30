#!/usr/bin/env python3
"""
PT-PT: Pacote de inglês britânico.

       O caso do inglês é o espelho exacto do português: os modelos Whisper são
       treinados sobretudo com inglês americano e produzem sistematicamente
       "hemoglobin", "edema", "anesthesia". Num registo clínico britânico ou
       irlandês essas formas estão erradas, e a tabela regional trata disso —
       tal como a tabela pt-BR -> pt-PT trata do português.

       Duas notas de segurança que valem mais do que qualquer outra entrada
       destas tabelas:

       Não há aqui nenhuma correcção de nomes de fármacos parecidos entre si.
       Trocar "hydralazine" por "hydroxyzine" mata pessoas, e um dicionário de
       substituição automática não tem informação nenhuma para decidir qual
       era. Esses termos vão para o vocabulário protegido, que ajuda o modelo a
       ouvir bem à primeira, e nunca para as tabelas de substituição.

       As abreviaturas perigosas — "U" por "units", "IU", "QD", "MSO4" — também
       não são expandidas automaticamente. Estão na lista proibida da ISMP
       precisamente por serem ambíguas.

EN-UK: British English pack.

       English mirrors Portuguese exactly: Whisper models are trained mostly on
       American English and systematically produce "hemoglobin", "edema",
       "anesthesia". In a British or Irish clinical record those forms are
       wrong, and the regional table handles it — just as the pt-BR -> pt-PT
       table handles Portuguese.

       Two safety notes worth more than any single entry in these tables:

       There is no correction here between look-alike drug names. Turning
       "hydralazine" into "hydroxyzine" kills people, and an automatic
       substitution dictionary has no information with which to decide which
       one was meant. Those terms go into the protected vocabulary, which helps
       the model hear correctly first time, and never into the substitution
       tables.

       Dangerous abbreviations — "U" for "units", "IU", "QD", "MSO4" — are not
       expanded automatically either. They are on the ISMP do-not-use list
       precisely because they are ambiguous.

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
    "patient present with": "patient presents with",
    "abdominal pain radiating too": "abdominal pain radiating to",
    "hart rate": "heart rate",
    "hart murmur": "heart murmur",
    "blood pleasure": "blood pressure",
    "saturation's": "saturations",
    "x ray": "x-ray",
    "c t scan": "CT scan",
    "m r i": "MRI",
    "e c g": "ECG",
    "u s s": "USS",
    # PT-PT: Fronteiras de palavra que o modelo perde.
    # EN-UK: Word boundaries the model loses.
    "short of breathe": "short of breath",
    "shortness of breathe": "shortness of breath",
    "loose weight": "lose weight",
    "past medical histry": "past medical history",
    "on examination the": "on examination, the",
    "no known drug allergys": "no known drug allergies",
    # PT-PT: Termos que o modelo parte ao meio.
    # EN-UK: Terms the model splits in half.
    "anti coagulant": "anticoagulant",
    "anti inflammatory": "anti-inflammatory",
    "anti biotic": "antibiotic",
    "echo cardiogram": "echocardiogram",
    "electro cardiogram": "electrocardiogram",
    "broncho dilator": "bronchodilator",
    "cortico steroid": "corticosteroid",
    "hyper tension": "hypertension",
    "hypo glycaemia": "hypoglycaemia",
    "tachy cardia": "tachycardia",
    "brady cardia": "bradycardia",
}

# ---------------------------------------------------------------------------
# PT-PT: 2. Conversões en-US -> en-GB.
#
#        Os sufixos gregos são a diferença mais visível na escrita clínica
#        britânica: -aemia, -oedema, -aesthesia, -haem-. O modelo escreve
#        sempre a forma americana.
#
# EN-UK: 2. en-US -> en-GB conversions.
#
#        The Greek digraphs are the most visible difference in British clinical
#        writing: -aemia, -oedema, -aesthesia, -haem-. The model always writes
#        the American form.
# ---------------------------------------------------------------------------
REGIONAL_CONVERSIONS: dict[str, str] = {
    # PT-PT: Dígrafos gregos / EN-UK: Greek digraphs
    "anemia": "anaemia",
    "anemic": "anaemic",
    "hypoglycemia": "hypoglycaemia",
    "hyperglycemia": "hyperglycaemia",
    "hypercalcemia": "hypercalcaemia",
    "hyponatremia": "hyponatraemia",
    "hyperkalemia": "hyperkalaemia",
    "bacteremia": "bacteraemia",
    "septicemia": "septicaemia",
    "ischemia": "ischaemia",
    "ischemic": "ischaemic",
    "leukemia": "leukaemia",
    "edema": "oedema",
    "edematous": "oedematous",
    "diarrhea": "diarrhoea",
    "gonorrhea": "gonorrhoea",
    "amenorrhea": "amenorrhoea",
    "hemorrhage": "haemorrhage",
    "hemorrhagic": "haemorrhagic",
    "hemoglobin": "haemoglobin",
    "hematoma": "haematoma",
    "hematuria": "haematuria",
    "hematology": "haematology",
    "hemodialysis": "haemodialysis",
    "hemostasis": "haemostasis",
    "anesthesia": "anaesthesia",
    "anesthetic": "anaesthetic",
    "anesthetist": "anaesthetist",
    "esophagus": "oesophagus",
    "esophageal": "oesophageal",
    "estrogen": "oestrogen",
    "orthopedic": "orthopaedic",
    "pediatric": "paediatric",
    "pediatrics": "paediatrics",
    "gynecology": "gynaecology",
    "gynecological": "gynaecological",
    "celiac": "coeliac",
    "fetal": "foetal",
    "diarrheal": "diarrhoeal",
    # PT-PT: Sufixos -ise e -yse / EN-UK: -ise and -yse endings
    "hospitalization": "hospitalisation",
    "hospitalized": "hospitalised",
    "immunization": "immunisation",
    "immunized": "immunised",
    "catheterization": "catheterisation",
    "catheterized": "catheterised",
    "nebulizer": "nebuliser",
    "randomized": "randomised",
    "normalized": "normalised",
    "analyze": "analyse",
    "analyzed": "analysed",
    "paralyzed": "paralysed",
    # PT-PT: Consoante dupla / EN-UK: Doubled consonant
    "labeled": "labelled",
    "counseling": "counselling",
    "vomiting blood": "haematemesis",
    # PT-PT: Vocabulário clínico distinto / EN-UK: Distinct clinical vocabulary
    "epinephrine": "adrenaline",
    "norepinephrine": "noradrenaline",
    "acetaminophen": "paracetamol",
    "albuterol": "salbutamol",
    "emergency room": "emergency department",
    "er": "emergency department",
    "operating room": "theatre",
    "attending physician": "consultant",
    "resident": "registrar",
    "intern": "foundation doctor",
    "drug store": "pharmacy",
    "band aid": "plaster",
    "shot": "injection",
    "gurney": "trolley",
    "primary care physician": "general practitioner",
}

# ---------------------------------------------------------------------------
# PT-PT: 3. Pontuação ditada.
# EN-UK: 3. Dictated punctuation.
# ---------------------------------------------------------------------------
SPOKEN_PUNCTUATION: tuple[tuple[str, str], ...] = (
    # PT-PT: Três palavras / EN-UK: Three words
    ("full stop new paragraph", ".\n\n"),
    ("open round bracket", "("),
    ("close round bracket", ")"),
    # PT-PT: Duas palavras / EN-UK: Two words
    ("new paragraph", "\n\n"),
    ("question mark", "?"),
    ("exclamation mark", "!"),
    ("full stop", "."),
    ("new line", "\n"),
    ("open bracket", "("),
    ("close bracket", ")"),
    ("open quote", "“"),
    ("close quote", "”"),
    # PT-PT: Uma palavra / EN-UK: One word
    ("paragraph", "\n\n"),
    ("semicolon", ";"),
    ("ellipsis", "..."),
    ("comma", ","),
    ("colon", ":"),
    ("dash", " — "),
    ("hyphen", "-"),
)

# ---------------------------------------------------------------------------
# PT-PT: 4. Vocabulário protegido.
#
#        É aqui que entram os fármacos parecidos entre si, precisamente porque
#        aqui não substituem nada — ajudam o modelo a ouvir bem à primeira.
#
# EN-UK: 4. Protected vocabulary.
#
#        This is where look-alike drug names belong, precisely because here
#        they replace nothing — they help the model hear correctly first time.
# ---------------------------------------------------------------------------
PROTECTED_TERMS: tuple[str, ...] = (
    # PT-PT: Sinais vitais / EN-UK: Vital signs
    "blood pressure", "heart rate", "respiratory rate", "oxygen saturations",
    "systolic", "diastolic",
    # PT-PT: Sintomas / EN-UK: Symptoms
    "dyspnoea", "orthopnoea", "tachycardia", "bradycardia", "palpitations",
    "paraesthesia", "pruritus", "oedema", "syncope", "dysphagia", "haemoptysis",
    # PT-PT: Exames / EN-UK: Investigations
    "electrocardiogram", "echocardiogram", "ultrasound", "full blood count",
    "urea and electrolytes", "creatinine", "glycated haemoglobin",
    "C-reactive protein", "chest radiograph",
    # PT-PT: Patologias / EN-UK: Conditions
    "hypertension", "diabetes mellitus", "atrial fibrillation",
    "heart failure", "chronic obstructive pulmonary disease", "pneumonia",
    "cerebrovascular accident", "osteoarthritis", "hypothyroidism",
    # PT-PT: Fármacos, incluindo pares que se confundem entre si.
    # EN-UK: Drugs, including pairs that are confused with one another.
    "amlodipine", "atorvastatin", "bisoprolol", "furosemide", "ramipril",
    "salbutamol", "levothyroxine", "metformin", "apixaban", "clopidogrel",
    "hydralazine", "hydroxyzine", "chlorpromazine", "chlorpropamide",
    # PT-PT: Estrutura da consulta / EN-UK: Consultation structure
    "presenting complaint", "history of presenting complaint",
    "past medical history", "drug history", "no known drug allergies",
    "on examination", "impression", "management plan", "follow-up",
)

PACK = LanguagePack(
    code="en-GB",
    whisper_code="en",
    name_native="English (United Kingdom)",
    name_en="English (United Kingdom)",
    spelling_corrections=SPELLING_CORRECTIONS,
    regional_conversions=REGIONAL_CONVERSIONS,
    regional_label="American → British English · Inglês americano → britânico",
    spoken_punctuation=SPOKEN_PUNCTUATION,
    protected_terms=PROTECTED_TERMS,
    prompt_opening=(
        "Transcript of a medical consultation in British English, "
        "punctuated, using British clinical spelling. Clinical vocabulary: "
    ),
)
