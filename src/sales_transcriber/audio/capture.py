"""capture.py
Microphone capture with WebRTC VAD speech detection.
"""

from __future__ import annotations

import wave
from dataclasses import dataclass
from io import BytesIO

import numpy as np
import sounddevice as sd

from sales_transcriber.audio.vad import VoiceActivityDetector
from sales_transcriber.audio.segment_builder import SpeechSegmentBuilder
from sales_transcriber.config import AudioConfig



class MicrophoneError(RuntimeError):
    """Raised when the microphone cannot be opened or read."""



@dataclass(frozen=True)
class AudioChunk:
    """A detected speech segment ready for transcription."""

    pcm: bytes
    sample_rate: int
    channels: int


    @property
    def rms(self) -> float:
        """Return RMS amplitude."""

        samples = np.frombuffer(
            self.pcm,
            dtype=np.int16
        )

        if samples.size == 0:
            return 0.0

        return float(
            np.sqrt(
                np.mean(
                    samples.astype(np.float32) ** 2
                )
            )
        )


    def to_wav_file(self) -> BytesIO:
        """Return this chunk as an in-memory WAV file."""

        wav_file = BytesIO()

        with wave.open(
            wav_file,
            "wb"
        ) as wav:

            wav.setnchannels(
                self.channels
            )

            wav.setsampwidth(2)

            wav.setframerate(
                self.sample_rate
            )

            wav.writeframes(
                self.pcm
            )


        wav_file.seek(0)
        wav_file.name = "microphone_chunk.wav"

        return wav_file




class MicrophoneRecorder:
    """
    Capture microphone audio and emit detected speech segments.
    """


    FRAME_DURATION_MS = 30


    def __init__(
        self,
        config: AudioConfig,
    ) -> None:


        self._config = config


        self._vad = VoiceActivityDetector(
            aggressiveness=config.vad_aggressiveness
        )


        self._segment_builder = SpeechSegmentBuilder(

            silence_frames_to_stop=
            config.silence_frames_to_stop,

            sample_rate=
            config.sample_rate,

            max_segment_seconds=
            config.max_segment_seconds,

            overlap_seconds=
            config.overlap_seconds,

            min_segment_seconds=
            config.min_segment_seconds,
        )



    def validate_device(self) -> None:
        """Validate microphone availability."""

        try:

            sd.query_devices(
                device=self._config.device,
                kind="input",
            )

        except Exception as exc:

            raise MicrophoneError(
                "No se pudo encontrar o abrir un microfono de entrada."
            ) from exc




    def chunks(self):
        """
        Yield complete speech segments.
        """

        self.validate_device()


        frame_size = int(
            self._config.sample_rate
            *
            self.FRAME_DURATION_MS
            /
            1000
        )


        try:

            with sd.InputStream(

                samplerate=
                self._config.sample_rate,

                channels=
                self._config.channels,

                dtype="int16",

                device=
                self._config.device,

            ) as stream:


                while True:


                    data, overflowed = stream.read(
                        frame_size
                    )


                    if overflowed:
                        print(
                            "[Audio] Overflow detectado"
                        )


                    frame = (
                        data
                        .astype(np.int16)
                        .tobytes()
                    )


                    speech = self._vad.is_speech(
                        frame,
                        self._config.sample_rate,
                    )


                    segment = (
                        self._segment_builder.add_frame(
                            frame,
                            speech,
                        )
                    )


                    if segment:

                        yield AudioChunk(

                            pcm=segment,

                            sample_rate=
                            self._config.sample_rate,

                            channels=
                            self._config.channels,

                        )


        except KeyboardInterrupt:

            raise


        except Exception as exc:

            raise MicrophoneError(
                "La captura de audio se interrumpio inesperadamente."
            ) from exc