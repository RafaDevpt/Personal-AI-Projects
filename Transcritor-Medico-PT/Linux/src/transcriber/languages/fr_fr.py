#!/usr/bin/env python3
"""
PT-PT: Pacote de francês de França.

       O francês tem duas dificuldades que as outras línguas deste conjunto não
       têm.

       A primeira são os acentos, que em francês mudam o significado e não
       apenas a grafia: "cote", "côte" e "coté" são três palavras diferentes, e
       numa nota clínica "côte" é uma costela. O modelo perde-os com
       frequência.

       A segunda é a norma tipográfica: em francês, os sinais de pontuação
       duplos — dois pontos, ponto e vírgula, interrogação, exclamação — levam
       um espaço fino inseparável antes. Escrever "diagnostic:" em vez de
       "diagnostic :" é um erro de composição visível a quem lê. Por isso as
       substituições de pontuação ditada deste pacote já trazem esse espaço.

       A conversão regional aqui é canadiana -> francesa: o Whisper produz
       regularmente formas do francês do Quebeco, que num hospital francês
       estão fora de norma.

EN-UK: France French pack.

       French has two difficulties the other languages in this set do not.

       The first is accents, which in French change meaning rather than merely
       spelling: "cote", "côte" and "coté" are three different words, and in a
       clinical note "côte" is a rib. The model loses them often.

       The second is typographic convention: in French the double punctuation
       marks — colon, semicolon, question and exclamation mark — take a
       non-breaking thin space before them. Writing "diagnostic:" instead of
       "diagnostic :" is a typesetting error visible to any reader. The
       dictated punctuation replacements in this pack therefore already carry
       that space.

       The regional conversion here is Canadian -> France French: Whisper
       regularly produces Quebec forms, which in a French hospital are out of
       standard.

Created by Redfox using Claude
"""

from __future__ import annotations

from . import LanguagePack

# PT-PT: Espaço fino inseparável (U+202F), exigido antes dos sinais duplos.
# EN-UK: Narrow no-break space (U+202F), required before double marks.
FINE = " "

# ---------------------------------------------------------------------------
# PT-PT: 1. Correcções ortográficas — sobretudo acentos perdidos.
# EN-UK: 1. Spelling corrections — mostly dropped accents.
# ---------------------------------------------------------------------------
SPELLING_CORRECTIONS: dict[str, str] = {
    # PT-PT: Acentos perdidos / EN-UK: Dropped accents
    "etat general": "état général",
    "etat": "état",
    "systeme": "système",
    "arteriel": "artériel",
    "arterielle": "artérielle",
    "frequence cardiaque": "fréquence cardiaque",
    "temperature": "température",
    "oedeme": "œdème",
    "oedemes": "œdèmes",
    "cephalee": "céphalée",
    "cephalees": "céphalées",
    "asthenie": "asthénie",
    "dyspnee": "dyspnée",
    "diarrhee": "diarrhée",
    "epigastrique": "épigastrique",
    "hematome": "hématome",
    "anemie": "anémie",
    "insuffisance renale": "insuffisance rénale",
    "hepatique": "hépatique",
    "prealable": "préalable",
    "resultats": "résultats",
    "traitement medicamenteux": "traitement médicamenteux",
    "antecedents": "antécédents",
    "allergie medicamenteuse": "allergie médicamenteuse",
    "echographie": "échographie",
    "electrocardiogramme": "électrocardiogramme",
    # PT-PT: Ligadura œ, que o modelo escreve como duas letras.
    # EN-UK: The œ ligature, which the model writes as two letters.
    "oesophage": "œsophage",
    "oesophagien": "œsophagien",
    "coeur": "cœur",
    "foetal": "fœtal",
    # PT-PT: Termos partidos ao meio / EN-UK: Terms split in half
    "anti inflammatoire": "anti-inflammatoire",
    "anti coagulant": "anticoagulant",
    "anti biotique": "antibiotique",
    "echo cardiographie": "échocardiographie",
    "rayons x": "radiographie",
}

# ---------------------------------------------------------------------------
# PT-PT: 2. Conversões fr-CA -> fr-FR.
# EN-UK: 2. fr-CA -> fr-FR conversions.
# ---------------------------------------------------------------------------
REGIONAL_CONVERSIONS: dict[str, str] = {
    "salle d'urgence": "service des urgences",
    "urgence hospitalière": "urgences",
    "docteure": "docteur",
    "infirmière auxiliaire": "aide-soignante",
    "prescription électronique": "ordonnance électronique",
    "pilule contraceptive orale": "contraceptif oral",
    "assurance maladie provinciale": "assurance maladie",
    "cédule": "planning",
    "céduler": "planifier",
    "magasiner": "faire des courses",
    "char": "voiture",
    "chandail": "pull",
    "breuvage": "boisson",
    "dispendieux": "coûteux",
    "présentement": "actuellement",
    "à date": "à ce jour",
    "correct": "satisfaisant",
}

# ---------------------------------------------------------------------------
# PT-PT: 3. Pontuação ditada. Os sinais duplos levam espaço fino antes.
# EN-UK: 3. Dictated punctuation. Double marks carry a thin space before them.
# ---------------------------------------------------------------------------
# PT-PT: A ordem é por número de palavras separadas por espaço, da maior para
#        a menor — que é como o `sanity_check` conta. Atenção que
#        "point d'interrogation" conta duas palavras e não quatro: o apóstrofo
#        não separa. Foi exactamente aí que esta lista esteve mal.
# EN-UK: The order is by number of space-separated words, largest first — which
#        is how `sanity_check` counts. Note that "point d'interrogation" counts
#        as two words, not four: the apostrophe does not separate. That is
#        precisely where this list was wrong.
SPOKEN_PUNCTUATION: tuple[tuple[str, str], ...] = (
    # PT-PT: Quatro palavras / EN-UK: Four words
    ("point à la ligne", ".\n"),
    # PT-PT: Três palavras / EN-UK: Three words
    ("ouvrir la parenthèse", "("),
    ("fermer la parenthèse", ")"),
    ("point et virgule", f"{FINE};"),
    ("à la ligne", "\n"),
    # PT-PT: Duas palavras / EN-UK: Two words
    ("point d'interrogation", f"{FINE}?"),
    ("point d'exclamation", f"{FINE}!"),
    ("nouveau paragraphe", "\n\n"),
    ("point virgule", f"{FINE};"),
    ("point final", "."),
    ("deux points", f"{FINE}:"),
    ("tiret cadratin", " — "),
    # PT-PT: Uma palavra / EN-UK: One word
    ("paragraphe", "\n\n"),
    ("virgule", ","),
    ("point", "."),
    ("tiret", "-"),
)

# ---------------------------------------------------------------------------
# PT-PT: 4. Vocabulário protegido.
# EN-UK: 4. Protected vocabulary.
# ---------------------------------------------------------------------------
PROTECTED_TERMS: tuple[str, ...] = (
    # PT-PT: Sinais vitais / EN-UK: Vital signs
    "tension artérielle", "fréquence cardiaque", "saturation en oxygène",
    "systolique", "diastolique",
    # PT-PT: Sintomas / EN-UK: Symptoms
    "dyspnée", "tachycardie", "bradycardie", "palpitations", "paresthésies",
    "prurit", "œdème", "céphalée", "asthénie", "dysphagie", "malaise vagal",
    # PT-PT: Exames / EN-UK: Investigations
    "électrocardiogramme", "échocardiographie", "échographie", "scanner",
    "imagerie par résonance magnétique", "numération formule sanguine",
    "créatinine", "hémoglobine glyquée", "endoscopie",
    # PT-PT: Patologias / EN-UK: Conditions
    "hypertension artérielle", "diabète de type 2", "fibrillation auriculaire",
    "insuffisance cardiaque", "pneumopathie", "accident vasculaire cérébral",
    "hypothyroïdie", "arthrose", "migraine",
    # PT-PT: Terapêutica / EN-UK: Therapeutics
    "anti-inflammatoire", "anticoagulant", "anxiolytique", "corticoïde",
    "paracétamol", "ibuprofène", "amoxicilline", "metformine", "oméprazole",
    # PT-PT: Estrutura da consulta / EN-UK: Consultation structure
    "motif de consultation", "antécédents personnels", "traitement habituel",
    "allergies connues", "examen clinique", "hypothèse diagnostique",
    "conduite à tenir", "hospitalisation", "sortie", "suivi",
)

PACK = LanguagePack(
    code="fr-FR",
    whisper_code="fr",
    name_native="Français (France)",
    name_en="French (France)",
    spelling_corrections=SPELLING_CORRECTIONS,
    regional_conversions=REGIONAL_CONVERSIONS,
    regional_label="Français canadien → de France · Canadian → France French",
    spoken_punctuation=SPOKEN_PUNCTUATION,
    protected_terms=PROTECTED_TERMS,
    prompt_opening=(
        "Transcription d'une consultation médicale en français de France, "
        "avec ponctuation et accents. Vocabulaire clinique : "
    ),
)
