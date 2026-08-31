#!/usr/bin/env python3
"""
PT-PT: Pacotes de língua — o vocabulário clínico e as regras de correcção,
       um conjunto por língua.

       O motor de transcrição (faster-whisper) fala perto de uma centena de
       línguas sem precisar de ajuda nenhuma. O que **não** é transferível é
       tudo o resto: os erros que o modelo comete são próprios de cada língua,
       a pontuação ditada diz-se por palavras diferentes, e o vocabulário
       clínico que interessa proteger muda com o país. Um pacote reúne
       exactamente essa parte, e nada mais.

       Consequência prática: transcrever numa língua sem pacote continua a
       funcionar — perde-se a correcção clínica, não a transcrição. É por isso
       que `resolve` nunca falha e devolve `None` em vez de levantar excepção.

       Cada pacote contém apenas dados e pode ser revisto por pessoal clínico
       sem perceber de código. Quem quiser acrescentar uma língua copia um
       ficheiro existente, traduz as tabelas e regista-o em `PACKS`.

EN-UK: Language packs — the clinical vocabulary and correction rules, one set
       per language.

       The transcription engine (faster-whisper) speaks close to a hundred
       languages with no help at all. What does **not** carry across is
       everything else: the mistakes the model makes are particular to each
       language, dictated punctuation is spoken with different words, and the
       clinical vocabulary worth protecting changes with the country. A pack
       gathers exactly that part, and nothing else.

       The practical consequence: transcribing in a language with no pack still
       works — what is lost is the clinical correction, not the transcription.
       That is why `resolve` never fails and returns `None` rather than raising.

       Each pack holds data only and can be reviewed by clinical staff with no
       understanding of code. To add a language, copy an existing file,
       translate the tables and register it in `PACKS`.

Created by Redfox using Claude
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise

# PT-PT: Orçamento de caracteres para o contexto inicial. O Whisper aceita 224
#        tokens; em línguas latinas cada token vale grosso modo 3 caracteres,
#        pelo que 700 caracteres deixam margem de segurança. Acima disto o
#        modelo trunca sem avisar, e os termos do fim da lista deixam de ter
#        qualquer efeito — o pior tipo de falha, porque parece funcionar.
# EN-UK: Character budget for the initial context. Whisper accepts 224 tokens;
#        in Latin languages a token is worth roughly 3 characters, so 700
#        characters leave a safety margin. Beyond this the model truncates
#        without warning and terms at the end of the list stop having any
#        effect — the worst kind of failure, because it looks like it works.
MAX_PROMPT_CHARS: int = 700


@dataclass(frozen=True)
class LanguagePack:
    """
    PT-PT: Tudo o que uma língua precisa para além do modelo de transcrição.

    EN-UK: Everything a language needs beyond the transcription model itself.
    """

    #: PT-PT: Identificador do pacote, com região. / EN-UK: Pack id, with region.
    code: str
    #: PT-PT: Código que o Whisper aceita. / EN-UK: Code Whisper accepts.
    whisper_code: str
    #: PT-PT: Nome na própria língua. / EN-UK: Name in the language itself.
    name_native: str
    #: PT-PT: Nome em inglês. / EN-UK: Name in English.
    name_en: str

    #: PT-PT: Erro -> forma correcta. / EN-UK: Mistake -> correct form.
    spelling_corrections: Mapping[str, str]

    #: PT-PT: Conversão entre variantes regionais da mesma língua.
    #: EN-UK: Conversion between regional variants of the same language.
    regional_conversions: Mapping[str, str]

    #: PT-PT: O que a conversão regional faz, para mostrar na interface.
    #: EN-UK: What the regional conversion does, for display in the interface.
    regional_label: str

    #: PT-PT: Expressão falada -> sinal. Ordenada da mais longa para a mais
    #:        curta, senão "ponto parágrafo" seria partido por "ponto".
    #: EN-UK: Spoken expression -> mark. Ordered longest to shortest, otherwise
    #:        "full stop new paragraph" would be broken up by "full stop".
    spoken_punctuation: tuple[tuple[str, str], ...]

    #: PT-PT: Vocabulário entregue ao modelo antes da descodificação.
    #: EN-UK: Vocabulary handed to the model before decoding.
    protected_terms: tuple[str, ...]

    #: PT-PT: Frase que abre o contexto inicial. Sinaliza a variante pretendida.
    #: EN-UK: Sentence opening the initial context. Signals the intended variant.
    prompt_opening: str

    def build_initial_prompt(self, max_chars: int = MAX_PROMPT_CHARS) -> str:
        """
        PT-PT: Constrói o contexto inicial entregue ao modelo de transcrição.

               A frase de abertura na variante pretendida é intencional: diz ao
               modelo em que língua e em que norma há-de escrever antes sequer
               de ouvir o áudio. É o que mais reduz a mistura de variantes na
               saída — mais do que qualquer correcção feita depois.

               Os termos são acrescentados até ao limite, sempre em palavras
               inteiras: cortar um termo a meio confundiria o modelo em vez de
               o ajudar.

        EN-UK: Builds the initial context handed to the transcription model.

               The opening sentence in the intended variant is deliberate: it
               tells the model which language and which standard to write in
               before it has even heard the audio. It does more to cut variant
               mixing in the output than any correction applied afterwards.

               Terms are added up to the limit, always as whole words: cutting
               a term in half would confuse the model rather than help it.

        :param max_chars:
            PT-PT: Limite de caracteres do contexto devolvido.
            EN-UK: Character limit of the returned context.
        :return:
            PT-PT: Texto pronto a passar ao parâmetro initial_prompt.
            EN-UK: Text ready to pass to the initial_prompt parameter.
        """
        parts: list[str] = []
        # PT-PT: +1 pelo ponto final que fecha a frase.
        # EN-UK: +1 for the full stop closing the sentence.
        used = len(self.prompt_opening) + 1

        for term in self.protected_terms:
            # PT-PT: +2 pela vírgula e espaço que separam os termos.
            # EN-UK: +2 for the comma and space separating the terms.
            cost = len(term) + 2
            if used + cost > max_chars:
                break
            parts.append(term)
            used += cost

        return self.prompt_opening + ", ".join(parts) + "."

    def sanity_check(self) -> list[str]:
        """
        PT-PT: Verifica a coerência das tabelas e devolve a lista de problemas.

               Corre nos testes automáticos e impede dois erros que já
               aconteceram neste projecto: entradas inúteis do tipo
               "paciente" -> "paciente", que só gastam uma expressão regular
               por termo, e pontuação ditada fora de ordem, que parte frases a
               meio sem ninguém dar por isso.

        EN-UK: Checks the tables for consistency and returns the problems found.

               Runs in the automated tests and blocks two mistakes that have
               already happened in this project: useless entries of the form
               "patient" -> "patient", which burn one regular expression per
               term for nothing, and out-of-order dictated punctuation, which
               cuts phrases in half with nobody noticing.

        :return:
            PT-PT: Descrições dos problemas; lista vazia significa tudo bem.
            EN-UK: Problem descriptions; an empty list means all is well.
        """
        problems: list[str] = []

        for name, table in (
            ("spelling_corrections", self.spelling_corrections),
            ("regional_conversions", self.regional_conversions),
        ):
            for wrong, right in table.items():
                if wrong == right:
                    problems.append(
                        f"{self.code}/{name}: entrada inútil {wrong!r} -> {right!r}"
                    )
                if not wrong.strip() or not right.strip():
                    problems.append(
                        f"{self.code}/{name}: entrada vazia {wrong!r} -> {right!r}"
                    )

        lengths = [len(phrase.split()) for phrase, _ in self.spoken_punctuation]
        for earlier, later in pairwise(lengths):
            if later > earlier:
                problems.append(
                    f"{self.code}/spoken_punctuation: expressões têm de estar "
                    "ordenadas da mais longa para a mais curta."
                )
                break

        if len(self.build_initial_prompt()) > MAX_PROMPT_CHARS:
            problems.append(
                f"{self.code}: o contexto inicial excede {MAX_PROMPT_CHARS} caracteres."
            )

        return problems

    @property
    def term_count(self) -> int:
        """PT-PT: Total de termos curados. / EN-UK: Total curated terms."""
        return (
            len(self.spelling_corrections)
            + len(self.regional_conversions)
            + len(self.spoken_punctuation)
            + len(self.protected_terms)
        )


# PT-PT: Os pacotes são importados aqui em baixo, depois de LanguagePack estar
#        definido, porque cada um constrói uma instância no momento da
#        importação. Importar em cima daria uma dependência circular.
# EN-UK: The packs are imported below, after LanguagePack is defined, because
#        each one builds an instance at import time. Importing at the top would
#        create a circular dependency.
from .en_gb import PACK as EN_GB  # noqa: E402
from .es_es import PACK as ES_ES  # noqa: E402
from .fr_fr import PACK as FR_FR  # noqa: E402
from .pt_pt import PACK as PT_PT  # noqa: E402

#: PT-PT: Registo de pacotes, por código. / EN-UK: Pack registry, keyed by code.
PACKS: dict[str, LanguagePack] = {
    pack.code: pack for pack in (PT_PT, EN_GB, ES_ES, FR_FR)
}

#: PT-PT: Usado quando nada foi escolhido. / EN-UK: Used when nothing is chosen.
DEFAULT_CODE: str = PT_PT.code

#: PT-PT: Valor que delega a escolha ao modelo, que a detecta pelo áudio.
#: EN-UK: Value delegating the choice to the model, which detects it from audio.
AUTO_CODE: str = "auto"


def resolve(code: str | None) -> LanguagePack | None:
    """
    PT-PT: Devolve o pacote correspondente ao código, ou None se não houver.

           Aceita tanto o código completo com região ("pt-PT") como o código
           curto do Whisper ("pt"), porque a configuração antiga guardava o
           curto e não vale a pena obrigar ninguém a reconfigurar.

           Devolver None em vez de levantar excepção é deliberado: uma língua
           sem pacote curado é uma limitação conhecida, não um erro. A
           transcrição corre na mesma, sem a camada clínica.

    EN-UK: Returns the pack matching the code, or None if there is none.

           Accepts both the full code with region ("pt-PT") and Whisper's short
           code ("pt"), because the old configuration stored the short one and
           there is no sense in forcing anyone to reconfigure.

           Returning None rather than raising is deliberate: a language with no
           curated pack is a known limitation, not an error. Transcription runs
           regardless, without the clinical layer.

    :param code:
        PT-PT: Código do pacote, código do Whisper, "auto", ou None.
        EN-UK: Pack code, Whisper code, "auto", or None.
    :return:
        PT-PT: O pacote, ou None se a língua não tiver um.
        EN-UK: The pack, or None if the language has none.
    """
    if not code or code == AUTO_CODE:
        return None

    if code in PACKS:
        return PACKS[code]

    # PT-PT: Código curto: o primeiro pacote que o declare ganha. A ordem de
    #        PACKS decide, e por isso pt-PT vem antes de qualquer outro pt.
    # EN-UK: Short code: the first pack declaring it wins. The order of PACKS
    #        decides, which is why pt-PT comes before any other pt.
    lowered = code.lower()
    for pack in PACKS.values():
        if pack.whisper_code == lowered or pack.code.lower() == lowered:
            return pack

    return None


def whisper_code_for(code: str | None) -> str | None:
    """
    PT-PT: Traduz um código de pacote para o que o Whisper espera.

           Devolve None para "auto", que é o que o faster-whisper interpreta
           como «detecta tu a língua a partir do áudio».

    EN-UK: Translates a pack code into what Whisper expects.

           Returns None for "auto", which is what faster-whisper reads as
           "detect the language from the audio yourself".

    :param code:
        PT-PT: Código do pacote ou "auto". / EN-UK: Pack code or "auto".
    :return:
        PT-PT: Código de duas letras, ou None para detecção automática.
        EN-UK: Two-letter code, or None for automatic detection.
    """
    if not code or code == AUTO_CODE:
        return None
    pack = resolve(code)
    return pack.whisper_code if pack else code


def choices() -> list[tuple[str, str]]:
    """
    PT-PT: Lista (código, rótulo) para as caixas de escolha da interface.

           "auto" vem primeiro por ser a opção segura para quem não sabe o que
           há-de escolher: o modelo detecta a língua e nada é corrigido a
           mais.

    EN-UK: List of (code, label) for the interface's selection boxes.

           "auto" comes first as the safe option for anyone unsure what to
           pick: the model detects the language and nothing is over-corrected.

    :return:
        PT-PT: Pares prontos a mostrar. / EN-UK: Pairs ready to display.
    """
    rotulos = [(AUTO_CODE, "Detecção automática · Automatic detection")]
    rotulos.extend(
        (pack.code, f"{pack.name_native} · {pack.name_en}") for pack in PACKS.values()
    )
    return rotulos


__all__ = [
    "AUTO_CODE",
    "DEFAULT_CODE",
    "EN_GB",
    "ES_ES",
    "FR_FR",
    "MAX_PROMPT_CHARS",
    "PACKS",
    "PT_PT",
    "LanguagePack",
    "choices",
    "resolve",
    "whisper_code_for",
]
