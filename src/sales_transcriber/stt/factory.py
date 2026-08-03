"""Factory for speech-to-text providers."""

from __future__ import annotations

from sales_transcriber.config import TranscriptionConfig
from sales_transcriber.stt.openai_client import OpenAITranscriber
from sales_transcriber.stt.whisper_local import WhisperTranscriber


def create_transcriber(config: TranscriptionConfig):
    """Create the configured transcription provider."""

    if config.provider == "openai":
        return OpenAITranscriber(config)

    if config.provider in {"whisper", "whisper-local"}:
        return WhisperTranscriber(config)

    raise ValueError(f"Proveedor STT desconocido: {config.provider}")
