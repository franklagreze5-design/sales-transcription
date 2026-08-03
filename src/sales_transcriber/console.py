"""Console output helpers for live transcription."""

from __future__ import annotations

from datetime import datetime


class ConsoleTranscriptWriter:
    """Print transcript deltas in a readable live format."""

    def __init__(self) -> None:
        self._segment_open = False

    def start(self) -> None:
        """Print the startup banner."""

        print("Transcripción en tiempo real iniciada. Presiona Ctrl+C para salir.\n")

    def write_delta(self, text: str) -> None:
        """Print a partial transcription delta without waiting for the full chunk."""

        if not self._segment_open:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] ", end="", flush=True)
            self._segment_open = True
        print(text, end="", flush=True)

    def end_segment(self) -> None:
        """Close the current console line after a chunk is processed."""

        if self._segment_open:
            print()
            self._segment_open = False

    def error(self, message: str) -> None:
        """Print a recoverable error without breaking the transcript flow."""

        self.end_segment()
        print(f"[Error] {message}")
