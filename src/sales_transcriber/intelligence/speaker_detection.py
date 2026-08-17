"""speaker_detection.py"""

from dataclasses import dataclass


@dataclass
class SpeakerSegment:
    speaker: str
    text: str


class SpeakerDetector:
    """
    Heurística inicial de separación de hablantes.

    Objetivo:
    - Identificar CLIENTE vs VENDEDOR.
    - Mantener contexto conversacional.
    - Fácil reemplazo futuro por Pyannote.
    """

    CLIENT_KEYWORDS = [
        "nos interesa",
        "me interesa",
        "presupuesto",
        "proveedores",
        "comparando",
        "evaluando",
        "demo",
        "demostración",
        "propuesta",
        "queremos",
        "necesitamos",
    ]

    SELLER_KEYWORDS = [
        "te explico",
        "nuestra solución",
        "nuestro producto",
        "nosotros ofrecemos",
        "podemos ayudar",
        "la plataforma",
        "el sistema",
    ]

    QUESTION_WORDS = [
        "qué",
        "cómo",
        "cuándo",
        "por qué",
        "cuál",
    ]

    def detect(
        self,
        transcript: str,
    ) -> SpeakerSegment:

        text = transcript.lower()

        #
        # Cliente
        #

        for keyword in self.CLIENT_KEYWORDS:

            if keyword in text:

                return SpeakerSegment(
                    speaker="Cliente",
                    text=transcript,
                )

        #
        # Vendedor
        #

        for keyword in self.SELLER_KEYWORDS:

            if keyword in text:

                return SpeakerSegment(
                    speaker="Vendedor",
                    text=transcript,
                )

        #
        # Preguntas suelen venir del vendedor
        #

        if "?" in transcript:

            return SpeakerSegment(
                speaker="Vendedor",
                text=transcript,
            )

        #
        # Fallback
        #

        return SpeakerSegment(
            speaker="Cliente probable",
            text=transcript,
        )
