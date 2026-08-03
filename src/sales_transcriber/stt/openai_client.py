"""OpenAI speech-to-text implementation."""

from __future__ import annotations

import time

from openai import APIConnectionError, APIError, OpenAI, OpenAIError

from sales_transcriber.audio.capture import AudioChunk
from sales_transcriber.config import TranscriptionConfig
from sales_transcriber.stt.base import TranscriptCallback


class TranscriptionServiceError(RuntimeError):
    """Raised when the speech-to-text provider cannot complete a request."""


class OpenAITranscriber:
    """Transcribe audio chunks with OpenAI's modern speech-to-text models."""

    def __init__(self, config: TranscriptionConfig) -> None:
        if not config.api_key:
            raise TranscriptionServiceError(
                "Falta OPENAI_API_KEY. Crea un archivo .env o define la variable de entorno."
            )

        self._config = config
        self._client = OpenAI(api_key=config.api_key)

    def transcribe(self, chunk: AudioChunk, on_delta: TranscriptCallback) -> str:
        """Transcribe a chunk, streaming deltas to the callback when available."""

        for attempt in range(1, self._config.max_retries + 1):
            try:
                return self._transcribe_once(chunk, on_delta)
            except (APIConnectionError, APIError) as exc:
                if attempt >= self._config.max_retries:
                    raise TranscriptionServiceError(
                        "No se pudo completar la transcripción después de varios intentos."
                    ) from exc
                wait_seconds = min(2**attempt, 8)
                print(f"\n[STT] Conexión inestable. Reintentando en {wait_seconds}s...")
                time.sleep(wait_seconds)
            except OpenAIError as exc:
                raise TranscriptionServiceError(f"Error del servicio de transcripción: {exc}") from exc

        return ""

    def _transcribe_once(self, chunk: AudioChunk, on_delta: TranscriptCallback) -> str:
        """Send one WAV chunk to OpenAI and collect the final text."""

        wav_file = chunk.to_wav_file()
        stream = self._client.audio.transcriptions.create(
            model=self._config.model,
            file=wav_file,
            language=self._config.language,
            response_format="json",
            stream=True,
        )

        text_parts: list[str] = []
        for event in stream:
            if getattr(event, "type", "") == "transcript.text.delta":
                delta = getattr(event, "delta", "")
                if delta:
                    text_parts.append(delta)
                    on_delta(delta)

        return "".join(text_parts).strip()
