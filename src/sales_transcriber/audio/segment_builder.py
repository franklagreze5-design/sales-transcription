from __future__ import annotations


class SpeechSegmentBuilder:
    """
    Acumula frames de voz y genera segmentos naturales.

    Optimizado para conversaciones comerciales:
    - tolera pausas normales al hablar
    - evita fragmentar frases
    - limita segmentos demasiado largos
    """

    FRAME_DURATION_SECONDS = 0.03


    def __init__(
        self,
        silence_frames_to_stop: int = 45,
        sample_rate: int = 16000,
        max_segment_seconds: float = 15.0,
        overlap_seconds: float = 0.4,
        min_segment_seconds: float = 2.0,
    ) -> None:


        self._frames: list[bytes] = []

        self._silence_count = 0

        self._silence_limit = (
            silence_frames_to_stop
        )


        self._sample_rate = sample_rate


        self._max_segment_seconds = (
            max_segment_seconds
        )


        self._overlap_frames = int(
            overlap_seconds /
            self.FRAME_DURATION_SECONDS
        )


        self._min_segment_seconds = (
            min_segment_seconds
        )



    def add_frame(
        self,
        frame: bytes,
        is_speech: bool,
    ) -> bytes | None:


        if is_speech:

            self._frames.append(frame)

            self._silence_count = 0


            duration = (
                self._segment_duration()
            )


            if duration >= self._max_segment_seconds:

                return self._flush(
                    keep_overlap=True
                )


            return None



        #
        # Detectamos silencio
        #

        if self._frames:

            self._silence_count += 1


            #
            # Esperamos más antes de cortar
            #
            if (
                self._silence_count
                >=
                self._silence_limit
            ):

                return self._flush(
                    keep_overlap=False
                )



        return None



    def _segment_duration(self) -> float:


        total_samples = sum(
            len(frame) // 2
            for frame in self._frames
        )


        return (
            total_samples /
            self._sample_rate
        )



    def _flush(
        self,
        keep_overlap: bool,
    ) -> bytes | None:


        duration = (
            self._segment_duration()
        )


        if duration < self._min_segment_seconds:

            self._frames.clear()

            self._silence_count = 0

            return None



        segment = b"".join(
            self._frames
        )



        #
        # Conservamos contexto inicial
        # para no perder continuidad
        #

        if (
            keep_overlap
            and
            self._overlap_frames > 0
            and
            len(self._frames)
            >
            self._overlap_frames
        ):

            self._frames = (
                self._frames[
                    -self._overlap_frames:
                ]
            )

        else:

            self._frames.clear()



        self._silence_count = 0


        return segment
