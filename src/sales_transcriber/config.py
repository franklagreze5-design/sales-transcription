"""config.py
Application configuration loaded from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class AudioConfig:
    """Microphone capture settings."""

    sample_rate: int = 16000
    channels: int = 1
    chunk_seconds: float = 1.5
    device: str | int | None = None

    # Audio filtering
    min_rms: float = 50.0

    # WebRTC VAD
    vad_aggressiveness: int = 1
    silence_frames_to_stop: int = 35

    # Segment control
    max_segment_seconds: float = 10.0
    overlap_seconds: float = 1.0
    min_segment_seconds: float = 1.0


@dataclass(frozen=True)
class TranscriptionConfig:
    """Speech-to-text provider settings."""

    provider: str = "openai"
    model: str = "gpt-4o-transcribe"

    language: str | None = "es"
    api_key: str | None = None

    max_retries: int = 3
    debug: bool = False

    # Whisper local
    whisper_model: str = "small"
    whisper_no_speech_threshold: float = 0.8
    whisper_log_prob_threshold: float = -0.8


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""

    audio: AudioConfig
    transcription: TranscriptionConfig


def _optional_device(
    value: str | None,
) -> str | int | None:
    """Convert env device value."""

    if not value:
        return None

    try:
        return int(value)

    except ValueError:
        return value


def _env_bool(
    name: str,
    default: bool = False,
) -> bool:
    """Read boolean environment values."""

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def load_config() -> AppConfig:
    """Load configuration from .env."""

    load_dotenv()

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    default_provider = (
        "openai"
        if api_key
        and not api_key.startswith("sk-your-")
        else "whisper-local"
    )


    return AppConfig(

        audio=AudioConfig(

            sample_rate=int(
                os.getenv(
                    "AUDIO_SAMPLE_RATE",
                    "16000",
                )
            ),

            channels=int(
                os.getenv(
                    "AUDIO_CHANNELS",
                    "1",
                )
            ),

            chunk_seconds=float(
                os.getenv(
                    "AUDIO_CHUNK_SECONDS",
                    "1.5",
                )
            ),

            device=_optional_device(
                os.getenv(
                    "AUDIO_DEVICE"
                )
            ),

            min_rms=float(
                os.getenv(
                    "AUDIO_MIN_RMS",
                    "50",
                )
            ),


            vad_aggressiveness=int(
                os.getenv(
                    "VAD_AGGRESSIVENESS",
                    "1",
                )
            ),

            silence_frames_to_stop=int(
                os.getenv(
                    "VAD_SILENCE_FRAMES",
                    "35",
                )
            ),


            max_segment_seconds=float(
                os.getenv(
                    "MAX_SEGMENT_SECONDS",
                    "10",
                )
            ),

            overlap_seconds=float(
                os.getenv(
                    "OVERLAP_SECONDS",
                    "1",
                )
            ),

            min_segment_seconds=float(
                os.getenv(
                    "MIN_SEGMENT_SECONDS",
                    "1",
                )
            ),
        ),


        transcription=TranscriptionConfig(

            provider=os.getenv(
                "TRANSCRIBER_PROVIDER",
                default_provider,
            ).strip().lower(),


            model=os.getenv(
                "TRANSCRIBER_MODEL",
                "gpt-4o-transcribe",
            ),


            language=os.getenv(
                "TRANSCRIBER_LANGUAGE",
                "es",
            ) or None,


            api_key=api_key,


            max_retries=int(
                os.getenv(
                    "TRANSCRIBER_MAX_RETRIES",
                    "3",
                )
            ),


            debug=_env_bool(
                "TRANSCRIBER_DEBUG"
            ),


            whisper_model=os.getenv(
                "WHISPER_MODEL",
                "small",
            ),


            whisper_no_speech_threshold=float(
                os.getenv(
                    "WHISPER_NO_SPEECH_THRESHOLD",
                    "0.8",
                )
            ),


            whisper_log_prob_threshold=float(
                os.getenv(
                    "WHISPER_LOG_PROB_THRESHOLD",
                    "-0.8",
                )
            ),
        ),
    )