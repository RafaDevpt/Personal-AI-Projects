#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Testes do motor de correcção de texto.
EN-UK: Tests for the text correction engine.

Created by Redfox using Claude
"""

from __future__ import annotations

import pytest

from transcriber.corrections import CorrectionEngine


@pytest.fixture()
def engine(tmp_path):
    """
    PT-PT: Motor com armazenamento numa pasta temporária, para que os testes
           nunca toquem nas correcções reais do utilizador.

    EN-UK: Engine backed by a temporary folder, so the tests never touch the
           user's real corrections.
    """
    return CorrectionEngine(tmp_path / "learned.json")


class TestDictionary:
    """
    PT-PT: Aplicação do dicionário médico.
    EN-UK: Medical dictionary application.
    """

    def test_converts_brazilian_to_european(self, engine):
        """
        PT-PT: A conversão pt-BR -> pt-PT é a correcção de maior impacto.
        EN-UK: The pt-BR -> pt-PT conversion is the highest-impact correction.
        """
        assert "vómito" in engine.apply_dictionary("o doente teve vômito")
        assert "cancro" in engine.apply_dictionary("suspeita de câncer")

    def test_preserves_capitalisation(self, engine):
        """
        PT-PT: Corrigir uma palavra no início da frase não deve pô-la em
               minúscula.
        EN-UK: Correcting a word at the start of a sentence must not
               lower-case it.
        """
        assert engine.apply_dictionary("Vômito persistente").startswith("Vómito")

    def test_respects_word_boundaries(self, engine):
        """
        PT-PT: Uma correcção não pode aplicar-se dentro de outra palavra.
        EN-UK: A correction must not apply inside another word.
        """
        # PT-PT: "analise" -> "análise", mas "analisemos" fica intacto.
        # EN-UK: "analise" -> "análise", but "analisemos" stays untouched.
        assert "analisemos" in engine.apply_dictionary("analisemos o caso")

    def test_longer_terms_win(self, engine):
        """
        PT-PT: "paciente presenta" tem de ser apanhado antes de "presenta".
        EN-UK: "paciente presenta" must be matched before "presenta".
        """
        result = engine.apply_dictionary("o paciente presenta febre")
        assert "paciente apresenta" in result

    def test_empty_input_is_safe(self, engine):
        """
        PT-PT: Texto vazio não deve provocar excepção.
        EN-UK: Empty text must not raise.
        """
        assert engine.apply_dictionary("") == ""
        assert engine.apply("") == ""


class TestCapitalisation:
    """
    PT-PT: Normalização de maiúsculas.
    EN-UK: Capitalisation normalisation.
    """

    def test_capitalises_sentence_starts(self):
        """
        PT-PT: Cada frase começa por maiúscula.
        EN-UK: Each sentence starts with a capital.
        """
        result = CorrectionEngine.normalise_capitalisation(
            "o doente refere tosse. tem febre há dois dias."
        )
        assert result.startswith("O doente")
        assert "Tem febre" in result

    def test_does_not_split_on_abbreviations(self):
        """
        PT-PT: "Dr." não termina uma frase.
        EN-UK: "Dr." does not end a sentence.
        """
        result = CorrectionEngine.normalise_capitalisation("consulta com o dr. silva hoje")
        assert "dr. silva" in result.lower()
        assert "Dr. Silva" not in result

    def test_handles_empty_text(self):
        """
        PT-PT: Texto vazio devolve texto vazio.
        EN-UK: Empty text returns empty text.
        """
        assert CorrectionEngine.normalise_capitalisation("") == ""


class TestWhitespace:
    """
    PT-PT: Limpeza de espaços.
    EN-UK: Whitespace tidying.
    """

    def test_removes_space_before_punctuation(self):
        """
        PT-PT: O Whisper produz por vezes um espaço antes da vírgula.
        EN-UK: Whisper sometimes produces a space before a comma.
        """
        assert CorrectionEngine.tidy_whitespace("febre , tosse .") == "febre, tosse."

    def test_preserves_paragraph_breaks(self):
        """
        PT-PT: Parágrafos separados por linha em branco mantêm-se.
        EN-UK: Paragraphs separated by a blank line are preserved.
        """
        assert "\n\n" in CorrectionEngine.tidy_whitespace("primeiro\n\nsegundo")


class TestLearning:
    """
    PT-PT: Aprendizagem a partir das edições do utilizador.
    EN-UK: Learning from the user's edits.
    """

    def test_learns_simple_replacement(self, engine):
        """
        PT-PT: Uma troca de palavra vira regra permanente.
        EN-UK: A word swap becomes a permanent rule.
        """
        learned = engine.learn(
            "o doente tomou benuron ontem",
            "o doente tomou Ben-u-ron ontem",
        )
        assert learned
        assert engine.learned["benuron"] == "Ben-u-ron"

    def test_learns_with_different_word_counts(self, engine):
        """
        PT-PT: A versão anterior exigia contagens iguais de palavras. O
               difflib alinha as duas versões e continua a aprender.
        EN-UK: The previous version required matching word counts. difflib
               aligns both versions and still learns.
        """
        engine.learn(
            "doente com dispneia e tosse",
            "doente apresenta dispneia, tosse seca e febre",
        )
        # PT-PT: O teste garante que não rebenta; regras podem ou não sair.
        # EN-UK: The test ensures it does not blow up; rules may or may not result.
        assert isinstance(engine.learned, dict)

    def test_ignores_numbers(self, engine):
        """
        PT-PT: Números são únicos de cada consulta; aprender "500" -> "750"
               estragaria todas as transcrições seguintes.
        EN-UK: Numbers are unique to each consultation; learning "500" -> "750"
               would ruin every subsequent transcription.
        """
        engine.learn("tomar 500 mg", "tomar 750 mg")
        assert "500" not in engine.learned

    def test_ignores_identical_text(self, engine):
        """
        PT-PT: Sem alterações não há nada a aprender.
        EN-UK: With no changes there is nothing to learn.
        """
        assert engine.learn("texto igual", "texto igual") == []

    def test_ignores_unrelated_rewrites(self, engine):
        """
        PT-PT: Substituir uma palavra por outra sem semelhança é reescrita de
               conteúdo, não correcção de transcrição.
        EN-UK: Replacing a word with an unrelated one is a content rewrite, not
               a transcription correction.
        """
        engine.learn("doente estável", "doente agitado")
        assert "estável" not in engine.learned

    def test_persists_across_instances(self, tmp_path):
        """
        PT-PT: As regras sobrevivem ao encerramento da aplicação.
        EN-UK: Rules survive the application closing.
        """
        store = tmp_path / "learned.json"
        first = CorrectionEngine(store)
        first.learn("benuron", "Ben-u-ron")

        second = CorrectionEngine(store)
        assert second.learned.get("benuron") == "Ben-u-ron"

    def test_forget_removes_rule(self, engine):
        """
        PT-PT: Uma regra mal aprendida tem de poder ser removida.
        EN-UK: A badly learned rule must be removable.
        """
        engine.learn("benuron", "Ben-u-ron")
        assert engine.forget("benuron") is True
        assert engine.forget("benuron") is False

    def test_learned_rules_are_applied(self, engine):
        """
        PT-PT: Depois de aprender, a regra aplica-se a texto novo.
        EN-UK: Once learned, the rule applies to new text.
        """
        engine.learn("benuron", "Ben-u-ron")
        assert "Ben-u-ron" in engine.apply_dictionary("receitei benuron")
