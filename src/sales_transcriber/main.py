"""Command-line entry point."""

from __future__ import annotations

from sales_transcriber.app import TranscriptionApp
from sales_transcriber.config import load_config
from sales_transcriber.stt.openai_client import TranscriptionServiceError


def main() -> None:
    """Start the sales meeting transcription MVP."""

    try:
        config = load_config()
        app = TranscriptionApp(config)
        app.run()
    except (TranscriptionServiceError, ValueError) as exc:
        print(f"[Error] {exc}")


if __name__ == "__main__":
    main()
