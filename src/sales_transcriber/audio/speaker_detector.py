"""speaker_detector.py"""
from __future__ import annotations

import tempfile
import os

from speechbrain.inference.speaker import EncoderClassifier


class SpeakerDetector:
    """
    Speaker identification basada en embeddings.

    Mantiene una memoria de speakers detectados:
        SPEAKER_01
        SPEAKER_02
        SPEAKER_03
    """

    SIMILARITY_THRESHOLD = 0.75

    def __init__(self) -> None:

        self._classifier = (
            EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="models/speechbrain-speakers",
            )
        )

        self._speaker_embeddings = {}

        self._speaker_counter = 0

    def identify(self, chunk) -> str:

        wav_file = chunk.to_wav_file()

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as tmp:

            tmp.write(wav_file.read())

            temp_path = tmp.name

        try:

            embedding = (
                self._classifier.encode_file(
                    temp_path
                )
            )

            return self._match_speaker(
                embedding
            )

        finally:

            if os.path.exists(temp_path):

                os.remove(temp_path)

    def _match_speaker(
        self,
        embedding,
    ) -> str:

        best_speaker = None

        best_score = -1.0

        for speaker_id, stored_embedding in (
            self._speaker_embeddings.items()
        ):

            score = (
                self._cosine_similarity(
                    embedding,
                    stored_embedding,
                )
            )

            if score > best_score:

                best_score = score

                best_speaker = speaker_id

        if (
            best_speaker is not None
            and best_score >= self.SIMILARITY_THRESHOLD
        ):

            return best_speaker

        self._speaker_counter += 1

        new_speaker = (
            f"SPEAKER_{self._speaker_counter:02d}"
        )

        self._speaker_embeddings[
            new_speaker
        ] = embedding

        return new_speaker

    def _cosine_similarity(
        self,
        emb1,
        emb2,
    ) -> float:

        numerator = (
            emb1 @ emb2.T
        ).item()

        denominator = (
            emb1.norm()
            *
            emb2.norm()
        ).item()

        if denominator == 0:

            return 0.0

        return numerator / denominator