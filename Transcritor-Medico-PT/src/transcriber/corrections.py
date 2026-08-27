#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Motor de correcção de texto.
       Aplica o dicionário médico, as correcções aprendidas com o utilizador e
       normalização de capitalização. Aprende automaticamente quando o
       utilizador edita uma transcrição no editor integrado.

EN-UK: Text correction engine.
       Applies the medical dictionary, corrections learned from the user, and
       capitalisation normalisation. It learns automatically when the user
       edits a transcription in the built-in editor.

PT-PT: Melhorias face à versão anterior:
       - Uma única expressão regular compilada para todos os termos, em vez de
         uma passagem por termo (era O(n) sobre o texto, n = tamanho do
         dicionário).
       - A capitalização original é preservada na substituição.
       - A aprendizagem usa difflib, funcionando mesmo quando o utilizador
         acrescenta ou remove palavras. A versão anterior exigia que o número
         de palavras fosse idêntico, o que raramente acontece numa edição real.

EN-UK: Improvements over the previous version:
       - A single compiled regular expression covering all terms, rather than
         one pass per term (which was O(n) over the text, n = dictionary size).
       - Original capitalisation is preserved during substitution.
       - Learning uses difflib, so it works even when the user adds or removes
         words. The previous version required the word count to match exactly,
         which rarely happens in a real edit.

Created by Redfox using Claude
"""

from __future__ import annotations

import difflib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .medical_terms import BRAZILIAN_TO_EUROPEAN, SPELLING_CORRECTIONS

_log = logging.getLogger(__name__)

# PT-PT: Abreviaturas que terminam em ponto sem terminarem a frase. Sem esta
#        lista a capitalização parte "Dr. silva" em duas frases.
# EN-UK: Abbreviations ending in a full stop without ending the sentence.
#        Without this list, capitalisation splits "Dr. silva" into two sentences.
_ABBREVIATIONS: frozenset[str] = frozenset({
    "dr", "dra", "sr", "sra", "prof", "eng", "enf", "etc", "ex", "aprox",
    "mg", "ml", "cm", "mm", "kg", "un", "obs", "pág", "fig", "n",
})


class CorrectionEngine:
    """
    PT-PT: Aplica e aprende correcções de texto clínico.

    EN-UK: Applies and learns clinical text corrections.
    """

    def __init__(self, store_path: Path) -> None:
        """
        :param store_path:
            PT-PT: Ficheiro JSON onde as correcções aprendidas são guardadas.
                   Contém texto derivado de transcrições reais, pelo que é
                   dado clínico e nunca deve ir para controlo de versões.
            EN-UK: JSON file in which learned corrections are stored. It holds
                   text derived from real transcriptions, so it is clinical
                   data and must never go into version control.
        """
        self.store_path = store_path
        self.learned: dict[str, str] = {}
        self.stats: dict[str, object] = {"total_edits": 0, "last_updated": None}
        self._pattern: re.Pattern[str] | None = None
        self._lookup: dict[str, str] = {}

        self.load()
        self._rebuild_pattern()

    # -----------------------------------------------------------------------
    # PT-PT: Persistência / EN-UK: Persistence
    # -----------------------------------------------------------------------

    def load(self) -> None:
        """
        PT-PT: Carrega as correcções aprendidas do disco, se existirem.
        EN-UK: Loads learned corrections from disk, if any exist.
        """
        if not self.store_path.is_file():
            _log.info("Sem correcções aprendidas em %s.", self.store_path)
            return

        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("Correcções aprendidas ilegíveis: %s", exc)
            return

        if isinstance(data.get("learned"), dict):
            self.learned = {str(k): str(v) for k, v in data["learned"].items()}
        if isinstance(data.get("stats"), dict):
            self.stats.update(data["stats"])

        _log.info("Carregadas %d correcções aprendidas.", len(self.learned))

    def save(self) -> bool:
        """
        PT-PT: Grava as correcções aprendidas.
        EN-UK: Writes learned corrections to disk.

        :return:
            PT-PT: True se gravou com sucesso.
            EN-UK: True if the write succeeded.
        """
        self.stats["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            self.store_path.write_text(
                json.dumps(
                    {"learned": self.learned, "stats": self.stats},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return True
        except OSError as exc:
            _log.error("Não foi possível gravar as correcções: %s", exc)
            return False

    # -----------------------------------------------------------------------
    # PT-PT: Construção do padrão / EN-UK: Pattern construction
    # -----------------------------------------------------------------------

    def _rebuild_pattern(self) -> None:
        """
        PT-PT: Compila todos os termos numa única expressão regular.

               A ordem importa: os termos mais longos vêm primeiro, para que
               "paciente presenta" seja apanhado antes de "presenta" sozinho.
               A alternância de expressões regulares em Python devolve a
               primeira alternativa que corresponda, não a mais longa.

        EN-UK: Compiles every term into a single regular expression.

               Order matters: longer terms come first, so that "paciente
               presenta" is matched before "presenta" on its own. Python's
               regular expression alternation returns the first alternative
               that matches, not the longest one.
        """
        self._lookup = {}
        # PT-PT: Prioridade crescente — o aprendido sobrepõe-se ao embutido.
        # EN-UK: Increasing priority — learned overrides built-in.
        for source in (SPELLING_CORRECTIONS, BRAZILIAN_TO_EUROPEAN, self.learned):
            for wrong, right in source.items():
                if wrong.strip() and wrong.lower() != right.lower():
                    self._lookup[wrong.lower()] = right

        if not self._lookup:
            self._pattern = None
            return

        ordered = sorted(self._lookup, key=len, reverse=True)
        joined = "|".join(re.escape(term) for term in ordered)
        # PT-PT: \b não funciona antes/depois de acentos em todos os casos, por
        #        isso usamos limites explícitos baseados em caracteres de
        #        palavra Unicode.
        # EN-UK: \b is unreliable around accented characters in some cases, so
        #        explicit boundaries based on Unicode word characters are used.
        self._pattern = re.compile(
            rf"(?<!\w)(?:{joined})(?!\w)",
            re.IGNORECASE | re.UNICODE,
        )

    # -----------------------------------------------------------------------
    # PT-PT: Aplicação / EN-UK: Application
    # -----------------------------------------------------------------------

    @staticmethod
    def _match_case(original: str, replacement: str) -> str:
        """
        PT-PT: Devolve a substituição com a capitalização do texto original.
               Sem isto, corrigir "Vomito" no início de uma frase produzia
               "vómito" em minúscula e partia a pontuação.

        EN-UK: Returns the replacement carrying the original text's
               capitalisation. Without this, correcting "Vomito" at the start
               of a sentence produced a lower-case "vómito" and broke the
               punctuation.
        """
        if original.isupper() and len(original) > 1:
            return replacement.upper()
        if original[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    def apply_dictionary(self, text: str) -> str:
        """
        PT-PT: Aplica o dicionário médico e as correcções aprendidas.
        EN-UK: Applies the medical dictionary and learned corrections.
        """
        if not text or self._pattern is None:
            return text

        def _replace(match: re.Match[str]) -> str:
            found = match.group(0)
            return self._match_case(found, self._lookup[found.lower()])

        return self._pattern.sub(_replace, text)

    @staticmethod
    def normalise_capitalisation(text: str) -> str:
        """
        PT-PT: Coloca maiúscula no início de cada frase, respeitando
               abreviaturas. Substitui o "acrescentar um ponto no fim" da
               versão anterior, que produzia frases sem sentido em texto longo.

        EN-UK: Capitalises the start of each sentence, respecting
               abbreviations. It replaces the previous version's "append a full
               stop at the end", which produced nonsense on longer text.
        """
        if not text:
            return text

        result: list[str] = []
        capitalise_next = True

        # PT-PT: Percorre por token para saber se um ponto termina abreviatura.
        # EN-UK: Walks token by token to tell whether a full stop ends an
        #        abbreviation.
        for token in re.split(r"(\s+)", text):
            if not token.strip():
                result.append(token)
                continue

            word = token
            if capitalise_next and word[:1].isalpha():
                word = word[:1].upper() + word[1:]
                capitalise_next = False

            stripped = word.rstrip('"\')]}')
            if stripped.endswith((".", "!", "?", "…")):
                bare = stripped.rstrip(".!?…").lower()
                capitalise_next = bare not in _ABBREVIATIONS

            result.append(word)

        return "".join(result)

    @staticmethod
    def tidy_whitespace(text: str) -> str:
        """
        PT-PT: Remove espaços antes de pontuação e colapsa espaços repetidos,
               preservando as quebras de parágrafo.

        EN-UK: Removes spaces before punctuation and collapses repeated spaces,
               while preserving paragraph breaks.
        """
        text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def apply(self, text: str) -> str:
        """
        PT-PT: Executa a cadeia completa de correcção.
        EN-UK: Runs the full correction chain.

        PT-PT: A ordem é deliberada — o dicionário primeiro (pode introduzir
               pontuação, como em "raio x" -> "raio-x"), a capitalização
               depois, e a limpeza de espaços no fim.
        EN-UK: The order is deliberate — dictionary first (it can introduce
               punctuation, as in "raio x" -> "raio-x"), capitalisation next,
               and whitespace tidying last.
        """
        if not text:
            return text
        text = self.apply_dictionary(text)
        text = self.normalise_capitalisation(text)
        return self.tidy_whitespace(text)

    # -----------------------------------------------------------------------
    # PT-PT: Aprendizagem / EN-UK: Learning
    # -----------------------------------------------------------------------

    def learn(self, original: str, corrected: str) -> list[tuple[str, str]]:
        """
        PT-PT: Deduz regras de substituição comparando o texto antes e depois
               da edição do utilizador.

               Usa difflib para alinhar as duas versões, pelo que funciona
               mesmo com palavras acrescentadas ou removidas. Só regista
               substituições palavra-a-palavra: alterações mais complexas são
               ignoradas por serem específicas de um contexto e produzirem
               regras que estragariam outras transcrições.

        EN-UK: Derives replacement rules by comparing the text before and after
               the user's edit.

               It uses difflib to align both versions, so it works even when
               words are added or removed. Only one-for-one word replacements
               are recorded: more complex changes are ignored because they are
               context-specific and would yield rules that damage other
               transcriptions.

        :return:
            PT-PT: Lista de pares (errado, correcto) efectivamente aprendidos.
            EN-UK: List of (wrong, right) pairs actually learned.
        """
        if not original or original == corrected:
            return []

        before = original.split()
        after = corrected.split()
        matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
        learned_now: list[tuple[str, str]] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            # PT-PT: Só interessa "replace" de igual dimensão dos dois lados.
            # EN-UK: Only "replace" with equal length on both sides is of use.
            if tag != "replace" or (i2 - i1) != (j2 - j1):
                continue

            for wrong_raw, right_raw in zip(before[i1:i2], after[j1:j2]):
                wrong = self._strip_punctuation(wrong_raw)
                right = self._strip_punctuation(right_raw)

                if not self._is_learnable(wrong, right):
                    continue

                key = wrong.lower()
                if self.learned.get(key) == right:
                    continue

                self.learned[key] = right
                learned_now.append((wrong, right))

        if learned_now:
            self.stats["total_edits"] = int(self.stats.get("total_edits", 0)) + 1
            self._rebuild_pattern()
            self.save()
            # PT-PT: Regista a contagem, não os termos — os termos são texto
            #        clínico e não pertencem ao ficheiro de registo.
            # EN-UK: Logs the count, not the terms — the terms are clinical
            #        text and do not belong in the log file.
            _log.info("Aprendidas %d novas correcções.", len(learned_now))

        return learned_now

    @staticmethod
    def _strip_punctuation(word: str) -> str:
        """
        PT-PT: Retira pontuação das extremidades de uma palavra.
        EN-UK: Strips punctuation from the edges of a word.
        """
        return word.strip(".,;:!?\"'()[]{}«»…")

    @staticmethod
    def _is_learnable(wrong: str, right: str) -> bool:
        """
        PT-PT: Decide se um par merece virar regra permanente.

               Rejeita pares vazios, iguais, com dígitos (números são únicos de
               cada consulta e nunca se repetem) e palavras de uma só letra.
               Rejeita também pares demasiado distantes: se a semelhança for
               baixa, o utilizador reescreveu a ideia em vez de corrigir uma
               transcrição errada.

        EN-UK: Decides whether a pair deserves to become a permanent rule.

               It rejects pairs that are empty, identical, contain digits
               (numbers are unique to each consultation and never recur), or
               are single letters. It also rejects pairs that are too far
               apart: if similarity is low, the user rewrote the idea rather
               than correcting a mistranscription.
        """
        if not wrong or not right:
            return False
        if wrong.lower() == right.lower():
            return False
        if len(wrong) < 2 or len(right) < 2:
            return False
        if any(char.isdigit() for char in wrong + right):
            return False

        similarity = difflib.SequenceMatcher(a=wrong.lower(), b=right.lower()).ratio()
        return similarity >= 0.5

    def forget(self, wrong: str) -> bool:
        """
        PT-PT: Remove uma regra aprendida. Necessário porque a aprendizagem
               automática engana-se, e uma regra má aplica-se a todas as
               transcrições futuras.

        EN-UK: Removes a learned rule. Necessary because automatic learning
               makes mistakes, and a bad rule applies to every future
               transcription.
        """
        if self.learned.pop(wrong.lower(), None) is None:
            return False
        self._rebuild_pattern()
        self.save()
        return True

    def summary(self) -> dict[str, object]:
        """
        PT-PT: Números para apresentar na interface.
        EN-UK: Figures for display in the interface.
        """
        return {
            "built_in_terms": len(SPELLING_CORRECTIONS) + len(BRAZILIAN_TO_EUROPEAN),
            "learned_terms": len(self.learned),
            "total_edits": self.stats.get("total_edits", 0),
            "last_updated": self.stats.get("last_updated"),
        }

    def learned_items(self) -> Iterable[tuple[str, str]]:
        """
        PT-PT: Itera as regras aprendidas por ordem alfabética.
        EN-UK: Iterates learned rules in alphabetical order.
        """
        return sorted(self.learned.items())
