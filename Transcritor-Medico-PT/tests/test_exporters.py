#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Testes da exportação de ficheiros e da configuração.
EN-UK: Tests for file export and configuration.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

from transcriber.config import AppConfig
from transcriber.exporters import export_txt, safe_filename, unique_path


class TestSafeFilename:
    """
    PT-PT: Saneamento de nomes de ficheiro.
    EN-UK: File name sanitisation.
    """

    def test_removes_illegal_characters(self):
        """
        PT-PT: Os dois pontos e a barra são proibidos no Windows.
        EN-UK: Colons and slashes are forbidden on Windows.
        """
        result = safe_filename("consulta: 12/03")
        assert ":" not in result and "/" not in result

    def test_keeps_accents(self):
        """
        PT-PT: Os acentos são válidos em NTFS e devem manter-se.
        EN-UK: Accents are valid on NTFS and must be preserved.
        """
        assert "ção" in safe_filename("transcrição")

    def test_replaces_reserved_names(self):
        """
        PT-PT: "CON" é reservado pelo Windows e bloqueia a gravação.
        EN-UK: "CON" is reserved by Windows and blocks the write.
        """
        assert safe_filename("CON") == "transcricao"

    def test_falls_back_on_empty_input(self):
        """
        PT-PT: Um nome que fique vazio depois da limpeza usa o de reserva.
        EN-UK: A name left empty after cleaning uses the fallback.
        """
        assert safe_filename("...") == "transcricao"


class TestUniquePath:
    """
    PT-PT: Prevenção de sobreposição de ficheiros.
    EN-UK: Prevention of file overwriting.
    """

    def test_returns_original_when_free(self, tmp_path):
        """
        PT-PT: Se o caminho está livre, é devolvido tal e qual.
        EN-UK: If the path is free, it is returned unchanged.
        """
        target = tmp_path / "nota.txt"
        assert unique_path(target) == target

    def test_appends_counter_when_taken(self, tmp_path):
        """
        PT-PT: Uma transcrição clínica nunca deve ser sobreposta em silêncio.
        EN-UK: A clinical transcription must never be silently overwritten.
        """
        target = tmp_path / "nota.txt"
        target.write_text("existente", encoding="utf-8")
        assert unique_path(target).name == "nota (2).txt"


class TestExportTxt:
    """
    PT-PT: Gravação em texto simples.
    EN-UK: Plain-text writing.
    """

    def test_writes_utf8_with_bom(self, tmp_path):
        """
        PT-PT: O BOM evita que o Bloco de Notas mostre "diagnÃ³stico".
        EN-UK: The BOM stops Notepad displaying "diagnÃ³stico".
        """
        target = export_txt("diagnóstico", tmp_path / "n.txt")
        assert target.read_bytes().startswith(b"\xef\xbb\xbf")

    def test_round_trips_accents(self, tmp_path):
        """
        PT-PT: O texto lido de volta tem de ser idêntico ao gravado.
        EN-UK: The text read back must be identical to what was written.
        """
        target = export_txt("acentuação e cedilha", tmp_path / "n.txt")
        assert "acentuação e cedilha" in target.read_text(encoding="utf-8-sig")

    def test_creates_missing_folders(self, tmp_path):
        """
        PT-PT: A pasta de destino é criada se não existir.
        EN-UK: The destination folder is created if it does not exist.
        """
        target = export_txt("texto", tmp_path / "nova" / "sub" / "n.txt")
        assert target.is_file()

    def test_includes_header(self, tmp_path):
        """
        PT-PT: O cabeçalho de proveniência aparece antes do texto.
        EN-UK: The provenance header appears before the text.
        """
        target = export_txt("corpo", tmp_path / "n.txt", header="CABEÇALHO\n\n")
        content = target.read_text(encoding="utf-8-sig")
        assert content.index("CABEÇALHO") < content.index("corpo")


class TestConfig:
    """
    PT-PT: Carregamento e validação da configuração.
    EN-UK: Configuration loading and validation.
    """

    def test_rejects_invalid_model(self):
        """
        PT-PT: Um modelo inexistente recua para o valor por omissão em vez de
               rebentar no arranque.
        EN-UK: A non-existent model falls back to the default rather than
               crashing at start-up.
        """
        assert AppConfig(model_size="gigantesco").model_size == "small"

    def test_clamps_beam_size(self):
        """
        PT-PT: Valores fora do intervalo são limitados.
        EN-UK: Out-of-range values are clamped.
        """
        assert AppConfig(beam_size=99).beam_size == 10
        assert AppConfig(beam_size=0).beam_size == 1

    def test_survives_corrupt_file(self, tmp_path):
        """
        PT-PT: JSON inválido não pode impedir a aplicação de arrancar.
        EN-UK: Invalid JSON must not prevent the application from starting.
        """
        broken = tmp_path / "config.json"
        broken.write_text("{ isto não é json", encoding="utf-8")
        assert AppConfig.load(broken).model_size == "small"

    def test_round_trips(self, tmp_path):
        """
        PT-PT: Gravar e voltar a ler preserva as definições.
        EN-UK: Saving and reloading preserves the settings.
        """
        path = tmp_path / "config.json"
        original = AppConfig(model_size="medium", beam_size=3, audio_dir=tmp_path)
        assert original.save(path) is True

        restored = AppConfig.load(path)
        assert restored.model_size == "medium"
        assert restored.beam_size == 3
        assert restored.audio_dir == Path(tmp_path)

    def test_ignores_unknown_keys(self, tmp_path):
        """
        PT-PT: Uma configuração de uma versão futura não trava a actual.
        EN-UK: A configuration from a future version does not break this one.
        """
        path = tmp_path / "config.json"
        path.write_text('{"model_size": "base", "campo_do_futuro": 1}', encoding="utf-8")
        assert AppConfig.load(path).model_size == "base"
