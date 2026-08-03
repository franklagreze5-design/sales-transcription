"""diarization.py"""
from pyannote.audio import Pipeline


class SpeakerDiarizer:

    def __init__(
        self,
        hf_token: str,
    ):

        self._pipeline = (
            Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token,
            )
        )

    def diarize(
        self,
        audio_file: str,
    ):

        diarization = (
            self._pipeline(audio_file)
        )

        segments = []

        for turn, _, speaker in diarization.itertracks(
            yield_label=True
        ):

            segments.append(
                {
                    "speaker": speaker,
                    "start": turn.start,
                    "end": turn.end,
                }
            )

        return segments