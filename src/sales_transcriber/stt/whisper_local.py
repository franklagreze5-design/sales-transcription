"""Local speech-to-text implementation using Faster Whisper."""

from __future__ import annotations

import os
import re
import tempfile

from faster_whisper import WhisperModel

from sales_transcriber.audio.capture import AudioChunk
from sales_transcriber.config import TranscriptionConfig
from sales_transcriber.stt.base import TranscriptCallback


class WhisperTranscriber:
    """Transcribe audio locally with Faster Whisper."""

    SILENCE_HALLUCINATIONS = {
        "y",
        "yy",
        "yyy",
        "yyyy",
        "eh",
        "ah",
        "mmm",
        "um",
        "uh",
        "hmm",
    }

    def __init__(self, config: TranscriptionConfig) -> None:
        self._config = config

        print(
            f"[Whisper] Cargando modelo local "
            f"'{config.whisper_model}'..."
        )

        # CPU estable para el MVP.
        device = "cpu"
        compute_type = "int8"

        print(
            f"[Whisper] Device={device} "
            f"Compute={compute_type}"
        )

        self._model = WhisperModel(
            config.whisper_model,
            device=device,
            compute_type=compute_type,
        )

        print("[Whisper] Modelo listo.")

    def transcribe(
        self,
        chunk: AudioChunk,
        on_delta: TranscriptCallback,
    ) -> str:
        """Transcribe an audio chunk."""

        temp_path = self._write_temp_wav(chunk)

        try:
            segments, info = self._model.transcribe(
                temp_path,
                language=self._config.language,
                beam_size=5,
                best_of=5,
                vad_filter=True,
                condition_on_previous_text=True,
                no_speech_threshold=self._config.whisper_no_speech_threshold,
                log_prob_threshold=self._config.whisper_log_prob_threshold,
            )

            if self._config.debug:
                language = getattr(
                    info,
                    "language",
                    "desconocido",
                )

                rms = getattr(
                    chunk,
                    "rms",
                    0,
                )

                print(
                    f"[DEBUG] "
                    f"Idioma={language} "
                    f"RMS={rms:.1f}"
                )

            text_parts: list[str] = []

            for segment in segments:

                text = self._clean_text(
                    segment.text
                )

                if not text:
                    continue

                if self._should_skip_segment(
                    segment,
                    text,
                ):
                    continue

                if self._config.debug:
                    print(
                        "[DEBUG] "
                        f"{segment.start:.2f}s -> "
                        f"{segment.end:.2f}s | "
                        f"{text!r}"
                    )

                text_parts.append(text)

                on_delta(
                    text + " "
                )

            return " ".join(
                text_parts
            ).strip()

        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def _write_temp_wav(
        self,
        chunk: AudioChunk,
    ) -> str:
        """Persist chunk to a temporary WAV file."""

        wav_file = chunk.to_wav_file()

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as tmp:

            tmp.write(
                wav_file.read()
            )

            return tmp.name

    def _clean_text(
        self,
        text: str,
    ) -> str:
        """Normalize common Whisper artifacts."""

        text = text.strip()

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text

    def _should_skip_segment(
        self,
        segment: object,
        text: str,
    ) -> bool:
        """Filter silence hallucinations."""

        normalized = (
            text.lower()
            .strip(" .,!?¡¿")
        )

        if (
            normalized
            in self.SILENCE_HALLUCINATIONS
        ):
            return True

        if (
            len(set(normalized))
            == 1
            and len(normalized) >= 3
        ):
            return True

        no_speech_prob = getattr(
            segment,
            "no_speech_prob",
            0.0,
        ) or 0.0

        avg_logprob = getattr(
            segment,
            "avg_logprob",
            0.0,
        ) or 0.0

        if (
            no_speech_prob
            > self._config.whisper_no_speech_threshold
        ):
            return True

        if (
            avg_logprob
            < self._config.whisper_log_prob_threshold
        ):
            return True

        return False