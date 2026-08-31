#!/usr/bin/env python3
"""
PT-PT: Testes do gravador.

       Nenhum destes testes abre um microfone. Abrir hardware num teste torna-o
       dependente da máquina onde corre, e a integração contínua não tem placa
       de som nenhuma — o teste passaria a verde no portátil e a vermelho no
       servidor, que é a pior espécie de teste.

       O que se testa é o que a aplicação faz com o áudio: escrevê-lo num WAV
       com o formato certo, medir o nível, e recusar gravações curtas de mais
       para valerem alguma coisa. Os blocos são injectados directamente no
       callback, exactamente como o PortAudio os entregaria.

EN-UK: Recorder tests.

       None of these tests opens a microphone. Opening hardware in a test makes
       it depend on the machine it runs on, and continuous integration has no
       sound card at all — the test would go green on the laptop and red on the
       server, which is the worst kind of test.

       What is tested is what the application does with the audio: write it
       into a WAV of the right format, measure the level, and refuse recordings
       too short to be worth anything. Blocks are injected straight into the
       callback, exactly as PortAudio would hand them over.

Created by Redfox using Claude
"""

from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path

import pytest

from transcriber import recorder as rec


def bloco(amplitude: float, frames: int = rec.BLOCK_SIZE) -> bytes:
    """
    PT-PT: Fabrica um bloco de áudio sinusoidal com a amplitude pedida.

    EN-UK: Fabricates a sinusoidal audio block at the requested amplitude.

    :param amplitude:
        PT-PT: 0 é silêncio, 1 é escala completa.
        EN-UK: 0 is silence, 1 is full scale.
    """
    pico = int(amplitude * 32767)
    amostras = array(
        "h",
        (
            int(pico * math.sin(2 * math.pi * 440 * n / rec.SAMPLE_RATE))
            for n in range(frames)
        ),
    )
    return amostras.tobytes()


class TestNomeSugerido:
    """PT-PT: Nomes de ficheiro. / EN-UK: Filenames."""

    def test_extensao_e_prefixo(self) -> None:
        nome = rec.suggest_filename()
        assert nome.startswith("ditado-")
        assert nome.endswith(".wav")

    def test_ordenavel_por_nome(self) -> None:
        """
        PT-PT: Ano-mês-dia faz com que ordenar por nome ordene por data.
        EN-UK: Year-month-day makes sorting by name sort by date.
        """
        nome = rec.suggest_filename()
        data = nome.removeprefix("ditado-").removesuffix(".wav")
        ano, mês, dia, hora = data.split("-")
        assert len(ano) == 4 and len(mês) == 2 and len(dia) == 2 and len(hora) == 6


class TestEscritaDoFicheiro:
    """
    PT-PT: O WAV tem de sair no formato que o Whisper consome, sem reamostrar.
    EN-UK: The WAV must come out in the format Whisper consumes, unresampled.
    """

    @staticmethod
    def _gravador_aberto(destino: Path) -> rec.AudioRecorder:
        """
        PT-PT: Prepara um gravador com o ficheiro aberto, sem tocar no
               microfone: é `start` sem a parte do hardware.
        EN-UK: Prepares a recorder with the file open, without touching the
               microphone: it is `start` minus the hardware part.
        """
        gravador = rec.AudioRecorder(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        # PT-PT: Aberto de proposito sem gestor de contexto: e o proprio
        #        gravador que o fecha em stop(), que e o que se esta a testar.
        # EN-UK: Deliberately opened without a context manager: the recorder
        #        itself closes it in stop(), which is what is under test.
        gravador._wave = wave.open(str(destino), "wb")  # noqa: SIM115
        gravador._wave.setnchannels(rec.CHANNELS)
        gravador._wave.setsampwidth(rec.SAMPLE_WIDTH)
        gravador._wave.setframerate(rec.SAMPLE_RATE)
        gravador._recording = True
        return gravador

    def test_formato_do_wav(self, tmp_path: Path) -> None:
        destino = tmp_path / "d.wav"
        gravador = self._gravador_aberto(destino)
        for _ in range(20):
            gravador._on_block(bloco(0.5), rec.BLOCK_SIZE, None, None)
        gravador.stop()

        with wave.open(str(destino), "rb") as w:
            assert w.getframerate() == 16_000
            assert w.getnchannels() == 1
            assert w.getsampwidth() == 2

    def test_duracao_corresponde_aos_blocos_escritos(self, tmp_path: Path) -> None:
        destino = tmp_path / "d.wav"
        gravador = self._gravador_aberto(destino)
        # PT-PT: 30 blocos de 100 ms são três segundos.
        # EN-UK: 30 blocks of 100 ms are three seconds.
        for _ in range(30):
            gravador._on_block(bloco(0.3), rec.BLOCK_SIZE, None, None)

        assert gravador.seconds == pytest.approx(3.0, abs=0.01)

    def test_pausa_nao_escreve(self, tmp_path: Path) -> None:
        """
        PT-PT: Em pausa os blocos continuam a chegar e são deitados fora.
        EN-UK: While paused, blocks keep arriving and are thrown away.
        """
        destino = tmp_path / "d.wav"
        gravador = self._gravador_aberto(destino)

        for _ in range(10):
            gravador._on_block(bloco(0.5), rec.BLOCK_SIZE, None, None)
        antes = gravador.seconds

        gravador.pause()
        for _ in range(10):
            gravador._on_block(bloco(0.5), rec.BLOCK_SIZE, None, None)
        assert gravador.seconds == antes

        gravador.resume()
        for _ in range(10):
            gravador._on_block(bloco(0.5), rec.BLOCK_SIZE, None, None)
        assert gravador.seconds > antes


class TestMedidorDeNivel:
    """
    PT-PT: O medidor é a peça que distingue «a aplicação está viva» de «o
           microfone está ligado». Se mentir, mente sobre a única coisa que
           interessa saber a meio de um ditado.
    EN-UK: The meter is what separates "the application is alive" from "the
           microphone is connected". If it lies, it lies about the one thing
           worth knowing mid-dictation.
    """

    @staticmethod
    def _nivel(amplitude: float, tmp_path: Path) -> float:
        gravador = TestEscritaDoFicheiro._gravador_aberto(tmp_path / "n.wav")
        gravador._on_block(bloco(amplitude), rec.BLOCK_SIZE, None, None)
        nível = gravador.level
        gravador.stop()
        return nível

    def test_silencio_fica_no_fundo(self, tmp_path: Path) -> None:
        assert self._nivel(0.0, tmp_path) < 0.02

    def test_voz_normal_e_visivel(self, tmp_path: Path) -> None:
        """
        PT-PT: Uma amplitude de conversação tem de acender o medidor de forma
               inequívoca. Um medidor que mal se mexe com voz normal não serve
               para nada.
        EN-UK: A conversational amplitude must light the meter unambiguously. A
               meter that barely moves at normal speech is of no use at all.
        """
        assert self._nivel(0.1, tmp_path) > 0.4

    def test_escala_e_monotona(self, tmp_path: Path) -> None:
        níveis = [self._nivel(a, tmp_path) for a in (0.01, 0.05, 0.2, 0.8)]
        assert níveis == sorted(níveis)

    def test_nunca_sai_do_intervalo(self, tmp_path: Path) -> None:
        for amplitude in (0.0, 0.001, 0.5, 1.0):
            assert 0.0 <= self._nivel(amplitude, tmp_path) <= 1.0


class TestGravacoesCurtas:
    """
    PT-PT: Um clique acidental no botão não deve produzir um ficheiro para
           transcrever. Entregá-lo ao modelo só produz ruído com aspecto de
           texto clínico, que é pior do que não produzir nada.
    EN-UK: An accidental click on the button must not produce a file to
           transcribe. Handing it to the model only produces noise shaped like
           clinical text, which is worse than producing nothing.
    """

    def test_gravacao_curta_e_descartada(self, tmp_path: Path) -> None:
        destino = tmp_path / "curta.wav"
        gravador = TestEscritaDoFicheiro._gravador_aberto(destino)
        # PT-PT: Dois blocos são 200 ms, abaixo do limiar de meio segundo.
        # EN-UK: Two blocks are 200 ms, below the half-second threshold.
        for _ in range(2):
            gravador._on_block(bloco(0.5), rec.BLOCK_SIZE, None, None)

        assert gravador.stop() is None
        assert not destino.exists()

    def test_gravacao_util_e_devolvida(self, tmp_path: Path) -> None:
        destino = tmp_path / "util.wav"
        gravador = TestEscritaDoFicheiro._gravador_aberto(destino)
        for _ in range(10):
            gravador._on_block(bloco(0.5), rec.BLOCK_SIZE, None, None)

        assert gravador.stop() == destino
        assert destino.exists()

    def test_parar_duas_vezes_nao_rebenta(self, tmp_path: Path) -> None:
        gravador = TestEscritaDoFicheiro._gravador_aberto(tmp_path / "d.wav")
        for _ in range(10):
            gravador._on_block(bloco(0.5), rec.BLOCK_SIZE, None, None)
        gravador.stop()
        assert gravador.stop() is None


class TestDisponibilidade:
    """PT-PT: Degradação graciosa. / EN-UK: Graceful degradation."""

    def test_devolve_par_com_explicacao(self) -> None:
        """
        PT-PT: A resposta traz sempre um motivo legível, porque a solução é
               diferente conforme falte a biblioteca ou o microfone.
        EN-UK: The answer always carries a readable reason, because the remedy
               differs depending on whether the library or the microphone is
               missing.
        """
        disponível, motivo = rec.dependencies_available()
        assert isinstance(disponível, bool)
        assert motivo.strip()

    def test_lista_de_microfones_nunca_rebenta(self) -> None:
        """
        PT-PT: Quem chama está a encher uma caixa de escolha; uma lista vazia é
               uma resposta legítima e uma excepção não é.
        EN-UK: The caller is filling a selection box; an empty list is a
               legitimate answer and an exception is not.
        """
        assert isinstance(rec.input_devices(), list)
