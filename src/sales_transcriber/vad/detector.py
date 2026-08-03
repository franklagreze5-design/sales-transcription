from __future__ import annotations

import webrtcvad


class VoiceActivityDetector:
    """
    Detecta si un frame contiene voz.
    """

    def __init__(
        self,
        aggressiveness: int = 2,
    ) -> None:

        self._vad = webrtcvad.Vad(
            aggressiveness
        )

    def is_speech(
        self,
        pcm: bytes,
        sample_rate: int,
    ) -> bool:

        return self._vad.is_speech(
            pcm,
            sample_rate,
        )