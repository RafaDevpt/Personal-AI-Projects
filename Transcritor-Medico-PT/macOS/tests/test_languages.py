#!/usr/bin/env python3
"""
PT-PT: Testes dos pacotes de língua.

       Estes testes correm sobre **todos** os pacotes registados, e não sobre
       uma lista escrita à mão. Quem acrescentar uma língua nova fica com ela
       testada sem escrever um teste — e, mais importante, fica impedido de a
       acrescentar mal.

EN-UK: Language pack tests.

       These tests run over **every** registered pack, not over a hand-written
       list. Anyone adding a new language gets it tested without writing a test
       — and, more importantly, is stopped from adding it badly.

Created by Redfox using Claude
"""

from __future__ import annotations

import pytest

from transcriber import languages as idiomas
from transcriber.corrections import CorrectionEngine

TODOS = pytest.mark.parametrize(
    "pack", idiomas.PACKS.values(), ids=[código for código in idiomas.PACKS]
)


class TestIntegridadeDosPacotes:
    """PT-PT: Integridade dos dados. / EN-UK: Data integrity."""

    @TODOS
    def test_sanity_check_passa(self, pack: idiomas.LanguagePack) -> None:
        """
        PT-PT: Nenhum pacote tem entradas inúteis nem pontuação fora de ordem.

               Este é o teste que apanhou dois erros reais quando os pacotes de
               espanhol e francês foram escritos: uma entrada que se traduzia a
               si própria, e listas de pontuação em que uma expressão de duas
               palavras vinha depois de uma de uma só. A segunda é traiçoeira:
               a aplicação continua a funcionar, apenas deixa de reconhecer as
               expressões mais longas, sem erro nenhum visível.

        EN-UK: No pack has useless entries or out-of-order punctuation.

               This is the test that caught two real errors when the Spanish
               and French packs were written: an entry translating to itself,
               and punctuation lists where a two-word expression came after a
               one-word one. The second is treacherous: the application keeps
               working, it merely stops recognising the longer expressions,
               with no visible error at all.
        """
        assert pack.sanity_check() == []

    @TODOS
    def test_contexto_inicial_cabe_no_orcamento(self, pack: idiomas.LanguagePack) -> None:
        """
        PT-PT: O contexto inicial não excede o que o Whisper aceita.

               Acima do limite o modelo trunca sem avisar, e os termos do fim
               da lista deixam de ter efeito nenhum. Falha silenciosa.

        EN-UK: The initial context does not exceed what Whisper accepts.

               Beyond the limit the model truncates without warning, and terms
               at the end of the list stop having any effect. A silent failure.
        """
        assert len(pack.build_initial_prompt()) <= idiomas.MAX_PROMPT_CHARS

    @TODOS
    def test_contexto_inicial_termina_em_termo_inteiro(
        self, pack: idiomas.LanguagePack
    ) -> None:
        """
        PT-PT: O corte nunca parte um termo ao meio.
        EN-UK: The cut never splits a term in half.
        """
        prompt = pack.build_initial_prompt(max_chars=250)
        assert prompt.endswith(".")
        corpo = prompt[len(pack.prompt_opening) : -1]
        for termo in (t.strip() for t in corpo.split(",") if t.strip()):
            assert termo in pack.protected_terms

    @TODOS
    def test_identificadores_coerentes(self, pack: idiomas.LanguagePack) -> None:
        """
        PT-PT: O código do Whisper tem duas letras e o do pacote traz região.
        EN-UK: The Whisper code is two letters and the pack code carries region.
        """
        assert len(pack.whisper_code) == 2
        assert pack.whisper_code.islower()
        assert "-" in pack.code
        assert pack.code.startswith(pack.whisper_code)

    @TODOS
    def test_tabelas_sem_chaves_repetidas_entre_si(
        self, pack: idiomas.LanguagePack
    ) -> None:
        """
        PT-PT: Uma chave em duas tabelas torna uma delas morta.

               Ambas alimentam a mesma expressão regular, e a segunda a ser
               carregada ganha. Ter a mesma chave nas duas significa que uma
               das entradas nunca é usada — e quem a escreveu não sabe qual.

        EN-UK: A key in two tables makes one of them dead.

               Both feed the same regular expression, and the second one loaded
               wins. Having the same key in both means one of the entries is
               never used — and whoever wrote it does not know which.
        """
        repetidas = set(pack.spelling_corrections) & set(pack.regional_conversions)
        assert repetidas == set(), f"chaves em ambas as tabelas: {sorted(repetidas)}"


class TestResolucaoDeCodigos:
    """PT-PT: Tradução de códigos. / EN-UK: Code resolution."""

    def test_codigo_completo(self) -> None:
        assert idiomas.resolve("pt-PT") is idiomas.PT_PT
        assert idiomas.resolve("fr-FR") is idiomas.FR_FR

    def test_codigo_curto_do_whisper(self) -> None:
        """
        PT-PT: As configurações antigas guardavam "pt" e têm de continuar a
               funcionar sem ninguém reconfigurar nada.
        EN-UK: Old configurations stored "pt" and must keep working with nobody
               reconfiguring anything.
        """
        assert idiomas.resolve("pt") is idiomas.PT_PT
        assert idiomas.resolve("en") is idiomas.EN_GB

    def test_lingua_sem_pacote_devolve_none(self) -> None:
        """
        PT-PT: Uma língua sem pacote é uma limitação conhecida, não um erro: a
               transcrição corre na mesma, sem a camada clínica.
        EN-UK: A language with no pack is a known limitation, not an error:
               transcription runs regardless, without the clinical layer.
        """
        assert idiomas.resolve("de") is None
        assert idiomas.resolve("auto") is None
        assert idiomas.resolve(None) is None

    def test_codigo_para_o_whisper(self) -> None:
        assert idiomas.whisper_code_for("pt-PT") == "pt"
        assert idiomas.whisper_code_for("es-ES") == "es"
        # PT-PT: None é o que o faster-whisper lê como «detecta tu».
        # EN-UK: None is what faster-whisper reads as "detect it yourself".
        assert idiomas.whisper_code_for("auto") is None

    def test_escolhas_comecam_por_automatico(self) -> None:
        escolhas = idiomas.choices()
        assert escolhas[0][0] == idiomas.AUTO_CODE
        assert len(escolhas) == len(idiomas.PACKS) + 1


class TestPontuacaoDitada:
    """
    PT-PT: A conversão de pontuação falada, que até agora existia em tabela
           mas nunca era aplicada por código nenhum.
    EN-UK: The spoken punctuation conversion, which until now existed as a
           table but was never applied by any code at all.
    """

    @staticmethod
    def _motor(tmp_path, código: str) -> CorrectionEngine:
        return CorrectionEngine(tmp_path / f"{código}.json", language=código)

    def test_portugues(self, tmp_path) -> None:
        motor = self._motor(tmp_path, "pt-PT")
        saída = motor.apply_spoken_punctuation("sem alterações ponto final")
        assert saída == "sem alterações."

    def test_ingles(self, tmp_path) -> None:
        motor = self._motor(tmp_path, "en-GB")
        saída = motor.apply_spoken_punctuation("no change full stop")
        assert saída == "no change."

    def test_expressao_longa_ganha_a_curta(self, tmp_path) -> None:
        """
        PT-PT: "ponto de interrogação" não pode ser partido por "ponto".

               É este o motivo de a ordem das tabelas importar, e o que o
               `sanity_check` protege.

        EN-UK: "question mark" must not be broken up by "mark".

               This is why the table order matters, and what `sanity_check`
               protects.
        """
        motor = self._motor(tmp_path, "pt-PT")
        assert motor.apply_spoken_punctuation("porquê ponto de interrogação") == "porquê?"

    def test_espaco_antes_do_sinal_e_absorvido(self, tmp_path) -> None:
        """
        PT-PT: O sinal cola-se à palavra anterior, como manda a tipografia.
        EN-UK: The mark attaches to the preceding word, as typography requires.
        """
        motor = self._motor(tmp_path, "pt-PT")
        assert " ." not in motor.apply_spoken_punctuation("dor torácica ponto final")

    def test_paragrafo_nao_deixa_espaco_pendurado(self, tmp_path) -> None:
        """
        PT-PT: Uma linha nova não pode começar por espaço.
        EN-UK: A new line must not begin on a space.
        """
        motor = self._motor(tmp_path, "en-GB")
        saída = motor.apply_spoken_punctuation("first new paragraph second")
        assert saída == "first\n\nsecond"

    def test_frances_poe_espaco_fino_antes_do_sinal_duplo(self, tmp_path) -> None:
        """
        PT-PT: Em francês os sinais duplos levam espaço fino inseparável antes.
               Escrever "diagnostic:" é um erro de composição.
        EN-UK: In French, double marks take a narrow no-break space before them.
               Writing "diagnostic:" is a typesetting error.
        """
        motor = self._motor(tmp_path, "fr-FR")
        saída = motor.apply_spoken_punctuation("diagnostic deux points hypertension")
        assert saída == "diagnostic : hypertension"

    def test_interruptor_desliga_a_conversao(self, tmp_path) -> None:
        """
        PT-PT: É a transformação mais arriscada da aplicação e tem de poder ser
               desligada por quem não dita a pontuação.
        EN-UK: It is the riskiest transformation in the application and must be
               switchable off by anyone who does not dictate punctuation.
        """
        motor = self._motor(tmp_path, "pt-PT")
        texto = "a vírgula decimal"
        assert motor.apply(texto, spoken_punctuation=False) == "A vírgula decimal"
        assert "," in motor.apply(texto, spoken_punctuation=True)


class TestTrocaDeLingua:
    """PT-PT: Mudar de língua em execução. / EN-UK: Switching language at runtime."""

    def test_tabelas_seguem_a_lingua(self, tmp_path) -> None:
        motor = CorrectionEngine(tmp_path / "l.json", language="en-GB")
        assert motor.apply_dictionary("hemoglobin") == "haemoglobin"

        motor.set_language("pt-PT")
        # PT-PT: A tabela inglesa deixou de estar carregada.
        # EN-UK: The English table is no longer loaded.
        assert motor.apply_dictionary("hemoglobin") == "hemoglobin"
        assert motor.apply_dictionary("vômito") == "vómito"

    def test_correccoes_aprendidas_sobrevivem_a_troca(self, tmp_path) -> None:
        """
        PT-PT: O que o utilizador ensinou é dele, não da língua. Quem dita em
               duas línguas corrige os mesmos nomes próprios em ambas.
        EN-UK: What the user taught is theirs, not the language's. Anyone
               dictating in two languages corrects the same proper nouns in both.
        """
        motor = CorrectionEngine(tmp_path / "l.json", language="pt-PT")
        # PT-PT: Uma correcção que muda letras, e não apenas maiúsculas: o
        #        motor descarta as que só mudam a caixa, porque a capitalização
        #        é tratada noutro passo da cadeia.
        # EN-UK: A correction changing letters, not merely case: the engine
        #        discards case-only ones, because capitalisation is handled by
        #        a different step of the chain.
        motor.learned["hospitl"] = "hospital"
        motor._rebuild_pattern()
        assert motor.apply_dictionary("hospitl") == "hospital"

        motor.set_language("fr-FR")
        assert motor.apply_dictionary("hospitl") == "hospital"

    def test_lingua_sem_pacote_fica_sem_tabelas_embutidas(self, tmp_path) -> None:
        motor = CorrectionEngine(tmp_path / "l.json", language="auto")
        assert motor.pack is None
        assert motor.summary()["built_in_terms"] == 0
        # PT-PT: E o texto atravessa a aplicação sem ser tocado.
        # EN-UK: And the text passes through the application untouched.
        assert motor.apply_dictionary("hemoglobin vômito") == "hemoglobin vômito"


class TestConversaoRegional:
    """
    PT-PT: A correcção de maior impacto: o modelo escreve sempre a variante
           maioritária no treino, que não é a europeia.
    EN-UK: The highest-impact correction: the model always writes the variant
           that dominated its training, which is not the European one.
    """

    @pytest.mark.parametrize(
        ("código", "entrada", "esperado"),
        [
            ("pt-PT", "vômito", "vómito"),
            ("pt-PT", "usuário", "utente"),
            ("en-GB", "anemia", "anaemia"),
            ("en-GB", "esophagus", "oesophagus"),
            ("en-GB", "acetaminophen", "paracetamol"),
            ("es-ES", "computadora", "ordenador"),
            ("fr-FR", "cédule", "planning"),
        ],
    )
    def test_variante(self, tmp_path, código: str, entrada: str, esperado: str) -> None:
        motor = CorrectionEngine(tmp_path / f"{código}.json", language=código)
        assert motor.apply_dictionary(entrada) == esperado
