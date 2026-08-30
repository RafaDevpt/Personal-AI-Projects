#!/usr/bin/env python3
"""
PT-PT: Testes do vocabulário médico.
       Este ficheiro é sobretudo uma rede de segurança para futuras edições do
       dicionário. O vocabulário é a parte da aplicação que mais vai crescer,
       e é editado por quem percebe de medicina e não necessariamente de
       código — convém que um erro comum seja apanhado por um teste.

EN-UK: Tests for the medical vocabulary.
       This file is chiefly a safety net for future edits to the dictionary.
       The vocabulary is the part of the application most likely to grow, and
       it is edited by people who understand medicine and not necessarily
       code — a common mistake had better be caught by a test.

Created by Redfox using Claude
"""

from __future__ import annotations

from transcriber import medical_terms as terms


class TestTableConsistency:
    """
    PT-PT: Coerência das tabelas de substituição.
    EN-UK: Consistency of the substitution tables.
    """

    def test_sanity_check_passes(self) -> None:
        """
        PT-PT: A verificação interna não encontra problemas. Falha aqui
               significa que uma edição recente introduziu uma entrada inútil
               ou desordenou a pontuação ditada.

        EN-UK: The internal check finds no problems. A failure here means a
               recent edit introduced a useless entry or disordered the
               dictated punctuation.
        """
        assert terms.sanity_check() == []

    def test_no_identity_mappings(self) -> None:
        """
        PT-PT: Nenhuma entrada mapeia uma palavra para si própria. Era este o
               defeito da versão anterior: centenas de pares "x" -> "x" que só
               consumiam tempo de processamento.

        EN-UK: No entry maps a word to itself. This was the previous version's
               flaw: hundreds of "x" -> "x" pairs that only consumed
               processing time.
        """
        for table in (terms.SPELLING_CORRECTIONS, terms.BRAZILIAN_TO_EUROPEAN):
            for wrong, right in table.items():
                assert wrong != right, f"entrada inútil: {wrong}"

    def test_keys_are_lower_case(self) -> None:
        """
        PT-PT: As chaves estão em minúsculas. A procura é feita sem distinguir
               maiúsculas, pelo que uma chave capitalizada seria redundante e
               daria a falsa impressão de cobrir um caso adicional.

        EN-UK: Keys are lower-case. Lookup is case-insensitive, so a
               capitalised key would be redundant and would give the false
               impression of covering an extra case.
        """
        for table in (terms.SPELLING_CORRECTIONS, terms.BRAZILIAN_TO_EUROPEAN):
            for wrong in table:
                assert wrong == wrong.lower(), f"chave com maiúscula: {wrong}"

    def test_no_leading_or_trailing_spaces(self) -> None:
        """
        PT-PT: Espaços nas extremidades impedem a correspondência por palavra
               inteira e são invisíveis a olho nu no código-fonte.

        EN-UK: Leading or trailing spaces break whole-word matching and are
               invisible to the naked eye in the source.
        """
        for table in (terms.SPELLING_CORRECTIONS, terms.BRAZILIAN_TO_EUROPEAN):
            for wrong, right in table.items():
                assert wrong == wrong.strip()
                assert right == right.strip()


class TestInitialPrompt:
    """
    PT-PT: Contexto inicial entregue ao modelo.
    EN-UK: Initial context handed to the model.
    """

    def test_respects_character_budget(self) -> None:
        """
        PT-PT: O contexto cabe no limite. Acima dele o Whisper trunca sem
               avisar e os termos do fim deixam de ter efeito — uma falha
               silenciosa que ninguém notaria em uso normal.

        EN-UK: The context fits within the limit. Beyond it Whisper truncates
               without warning and the terms at the end stop having any effect
               — a silent failure nobody would notice in normal use.
        """
        assert len(terms.build_initial_prompt()) <= terms.MAX_PROMPT_CHARS

    def test_truncates_at_whole_terms(self) -> None:
        """
        PT-PT: Com um orçamento apertado, o contexto é cortado entre termos e
               nunca a meio de um.

        EN-UK: With a tight budget, the context is cut between terms and never
               part-way through one.
        """
        prompt = terms.build_initial_prompt(max_chars=200)
        assert len(prompt) <= 200
        assert prompt.endswith(".")

    def test_declares_european_portuguese(self) -> None:
        """
        PT-PT: A frase de abertura tem de referir português europeu — é o que
               mais reduz os brasileirismos na saída do modelo.

        EN-UK: The opening sentence must mention European Portuguese — it does
               more than anything else to cut Brazilianisms in the model's
               output.
        """
        assert "português europeu" in terms.build_initial_prompt().lower()
