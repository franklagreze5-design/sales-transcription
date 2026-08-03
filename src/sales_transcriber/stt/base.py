"""Provider-neutral transcription interfaces."""

from __future__ import annotations

from typing import Callable, Protocol

from sales_transcriber.audio.capture import AudioChunk

TranscriptCallback = Callable[[str], None]


class SpeechToTextClient(Protocol):
    """Contract implemented by any reusable speech-to-text provider."""

    def transcribe(self, chunk: AudioChunk, on_delta: TranscriptCallback) -> str:
        """Transcribe a chunk and call on_delta as text arrives."""
