from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SpeechSegment:
    pcm: bytes
    sample_rate: int
    channels: int


class SpeechSegmentBuilder:

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        max_silence_frames: int = 20,
    ) -> None:

        self.sample_rate = sample_rate
        self.channels = channels

        self.max_silence_frames = max_silence_frames

        self._buffers: list[bytes] = []
        self._silence_count = 0
        self._speaking = False

    def add_frame(
        self,
        frame: bytes,
        speech_detected: bool,
    ) -> SpeechSegment | None:

        if speech_detected:

            self._speaking = True
            self._silence_count = 0

            self._buffers.append(frame)

            return None

        if self._speaking:

            self._silence_count += 1

            self._buffers.append(frame)

            if (
                self._silence_count
                >= self.max_silence_frames
            ):

                segment = SpeechSegment(
                    pcm=b"".join(
                        self._buffers
                    ),
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                )

                self._buffers.clear()

                self._silence_count = 0

                self._speaking = False

                return segment

        return None