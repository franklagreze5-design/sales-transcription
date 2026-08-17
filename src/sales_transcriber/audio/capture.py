"""capture.py
Microphone capture with WebRTC VAD speech detection.
"""

from __future__ import annotations

import wave
import queue
import sys
from dataclasses import dataclass
from io import BytesIO

import numpy as np
import pyaudiowpatch as pyaudio
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

        self._input_sample_rate = self._detect_input_sample_rate()
        self._system_sample_rate = self._detect_system_sample_rate()



    def validate_device(self) -> None:
        """Validate microphone availability."""

        if self._config.source in {"system", "both"}:
            self._validate_system_device()

        if self._config.source == "system":
            return

        try:

            sd.query_devices(
                device=self._config.device,
                kind="input",
            )

        except Exception as exc:

            raise MicrophoneError(
                "No se pudo encontrar o abrir un microfono de entrada."
            ) from exc

    def _validate_system_device(self) -> None:
        """Validate Windows system audio loopback availability."""

        if sys.platform != "win32":
            raise MicrophoneError(
                "La captura de audio del sistema solo esta disponible en Windows."
            )

        try:
            self._system_device_info()
        except Exception as exc:
            raise MicrophoneError(
                "No se pudo abrir el audio del sistema. "
                "Verifica que exista un dispositivo de salida activo en Windows."
            ) from exc


    def _detect_input_sample_rate(self) -> int:
        """Use the device native rate for capture and resample for VAD."""

        try:
            device = sd.query_devices(
                device=self._config.device,
                kind="input",
            )
        except Exception:
            return self._config.sample_rate

        return int(
            device.get(
                "defaultSampleRate",
                self._config.sample_rate,
            )
        )

    def _detect_system_sample_rate(self) -> int:
        """Use the output device native rate for loopback capture."""

        try:
            device = self._system_device_info()
        except Exception:
            return self._config.sample_rate

        return int(
            device.get(
                "default_samplerate",
                self._config.sample_rate,
            )
        )

    def _system_device_info(self) -> dict:
        """Return the configured or default output device info."""

        device_id = self._config.system_device
        if device_id is None:
            default_output = sd.default.device[1]
            if default_output is None or default_output < 0:
                raise MicrophoneError(
                    "No hay dispositivo de salida predeterminado para capturar."
                )
            device_id = int(default_output)

        audio = pyaudio.PyAudio()
        try:
            if device_id is None:
                return audio.get_default_wasapi_loopback()
            return audio.get_device_info_by_index(int(device_id))
        finally:
            audio.terminate()




    def chunks(self):
        """
        Yield complete speech segments.
        """

        self.validate_device()

        if self._config.source in {"system", "both"}:
            yield from self._loopback_chunks()
            return


        frame_size = int(
            self._input_sample_rate
            *
            self.FRAME_DURATION_MS
            /
            1000
        )


        try:

            with sd.InputStream(

                samplerate=
                self._input_sample_rate,

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
                        self._prepare_frame(
                            data,
                            self._input_sample_rate,
                        )
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
                "La captura de audio se interrumpio inesperadamente: "
                f"{exc}"
            ) from exc


    def _loopback_chunks(self):
        """Capture system audio, optionally mixed with microphone audio."""

        frame_size = int(
            self._config.sample_rate
            *
            self.FRAME_DURATION_MS
            /
            1000
        )
        system_block_size = int(
            self._system_sample_rate
            *
            self.FRAME_DURATION_MS
            /
            1000
        )
        mic_block_size = int(
            self._input_sample_rate
            *
            self.FRAME_DURATION_MS
            /
            1000
        )

        system_queue: queue.Queue[bytes] = queue.Queue(maxsize=80)
        mic_queue: queue.Queue[bytes] = queue.Queue(maxsize=80)

        def put_latest(target_queue: queue.Queue[bytes], frame: bytes) -> None:
            try:
                target_queue.put_nowait(frame)
            except queue.Full:
                try:
                    target_queue.get_nowait()
                except queue.Empty:
                    pass
                target_queue.put_nowait(frame)

        def system_callback(in_data, frame_count, time_info, status):
            put_latest(
                system_queue,
                self._prepare_pcm_frame(
                    in_data,
                    system_channels,
                    self._system_sample_rate,
                ),
            )
            return (None, pyaudio.paContinue)

        def mic_callback(indata, frames, time_info, status) -> None:
            if status:
                print(f"[Audio] Microfono: {status}")
            put_latest(
                mic_queue,
                self._prepare_frame(
                    indata,
                    self._input_sample_rate,
                ),
            )

        try:
            audio = pyaudio.PyAudio()
            system_info = self._system_device_info()
            system_device = int(system_info["index"])
            system_channels = max(
                1,
                int(
                    system_info.get("maxInputChannels", 2)
                ),
            )

            system_stream = audio.open(
                format=pyaudio.paInt16,
                channels=system_channels,
                rate=self._system_sample_rate,
                input=True,
                input_device_index=system_device,
                frames_per_buffer=system_block_size,
                stream_callback=system_callback,
            )

            mic_stream = None
            if self._config.source == "both":
                mic_stream = sd.InputStream(
                        samplerate=self._input_sample_rate,
                        channels=self._config.channels,
                        dtype="int16",
                        device=self._config.device,
                        blocksize=mic_block_size,
                        callback=mic_callback,
                )

            try:
                if mic_stream is not None:
                    with mic_stream:
                        yield from self._consume_loopback_queues(
                            system_queue,
                            mic_queue,
                            frame_size,
                        )
                else:
                    yield from self._consume_loopback_queues(
                        system_queue,
                        None,
                        frame_size,
                    )
            finally:
                system_stream.stop_stream()
                system_stream.close()
                audio.terminate()

        except KeyboardInterrupt:
            raise
        except Exception as exc:
            raise MicrophoneError(
                "La captura de audio del sistema se interrumpio inesperadamente: "
                f"{exc}"
            ) from exc

    def _consume_loopback_queues(
        self,
        system_queue: queue.Queue[bytes],
        mic_queue: queue.Queue[bytes] | None,
        frame_size: int,
    ):
        """Read loopback frames, mix if needed, and emit speech segments."""

        zero_frame = np.zeros(frame_size, dtype=np.int16).tobytes()

        while True:
            try:
                system_frame = system_queue.get(timeout=1.0)
            except queue.Empty:
                system_frame = zero_frame

            if mic_queue is not None:
                try:
                    mic_frame = mic_queue.get_nowait()
                except queue.Empty:
                    mic_frame = zero_frame
                frame = self._mix_frames(system_frame, mic_frame)
            else:
                frame = system_frame

            speech = self._vad.is_speech(
                frame,
                self._config.sample_rate,
            )

            segment = self._segment_builder.add_frame(
                frame,
                speech,
            )

            if segment:
                yield AudioChunk(
                    pcm=segment,
                    sample_rate=self._config.sample_rate,
                    channels=self._config.channels,
                )

    def _mix_frames(
        self,
        first: bytes,
        second: bytes,
    ) -> bytes:
        """Mix two mono int16 frames with clipping protection."""

        first_samples = np.frombuffer(first, dtype=np.int16).astype(np.int32)
        second_samples = np.frombuffer(second, dtype=np.int16).astype(np.int32)
        length = max(len(first_samples), len(second_samples))
        if len(first_samples) < length:
            first_samples = np.pad(first_samples, (0, length - len(first_samples)))
        if len(second_samples) < length:
            second_samples = np.pad(second_samples, (0, length - len(second_samples)))
        mixed = np.clip(
            first_samples + second_samples,
            -32768,
            32767,
        )
        return mixed.astype(np.int16).tobytes()

    def _prepare_pcm_frame(
        self,
        data: bytes,
        channels: int,
        input_sample_rate: int,
    ) -> bytes:
        """Convert raw int16 PCM bytes into mono 16 kHz PCM."""

        samples = np.frombuffer(data, dtype=np.int16)
        if channels > 1 and samples.size >= channels:
            samples = samples.reshape(-1, channels).mean(axis=1)
        return self._resample_samples(
            samples.astype(np.float32),
            input_sample_rate,
        )


    def _prepare_frame(
        self,
        data: np.ndarray,
        input_sample_rate: int,
    ) -> bytes:
        """Convert native device audio into mono 16 kHz PCM."""

        samples = data.astype(np.float32)

        if samples.ndim > 1:
            samples = samples.mean(axis=1)

        return self._resample_samples(
            samples,
            input_sample_rate,
        )

    def _resample_samples(
        self,
        samples: np.ndarray,
        input_sample_rate: int,
    ) -> bytes:
        """Resample mono float samples into configured int16 PCM."""

        if input_sample_rate != self._config.sample_rate:
            target_length = int(
                len(samples)
                *
                self._config.sample_rate
                /
                input_sample_rate
            )

            if target_length <= 0:
                return b""

            source_positions = np.linspace(
                0,
                len(samples) - 1,
                num=len(samples),
            )

            target_positions = np.linspace(
                0,
                len(samples) - 1,
                num=target_length,
            )

            samples = np.interp(
                target_positions,
                source_positions,
                samples,
            )

        samples = np.clip(
            samples,
            -32768,
            32767,
        )

        return samples.astype(np.int16).tobytes()
