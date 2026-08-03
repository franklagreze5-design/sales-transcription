"""
llm_analyzer.py

Analizador comercial usando un LLM.
Convierte transcripciones en inteligencia comercial estructurada.
"""

from __future__ import annotations

import json

from openai import OpenAI

from sales_transcriber.intelligence.models import (
    ConversationInsight,
)


class LLMConversationAnalyzer:
    """
    Analizador comercial basado en IA.

    Responsabilidades:
    - Detectar intención comercial
    - Detectar etapa del pipeline
    - Detectar dolor/necesidad
    - Detectar objeciones reales
    - Evaluar oportunidad
    - Generar coaching comercial
    """


    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
    ) -> None:


        self.client = OpenAI(
            api_key=api_key
        )

        self.model = model



    def analyze(
        self,
        transcript: str,
    ) -> ConversationInsight:


        prompt = f"""
Eres un experto en ventas B2B consultivas.

Analiza esta conversación comercial:

---
{transcript}
---

Devuelve SOLO JSON válido.

No inventes información.
Si no existe evidencia, usa valores neutros.

Clasifica:

intent:
- discovery
- evaluation
- interest
- pricing
- implementation
- unknown


sales_stage:
- discovery
- evaluation
- presentation
- objection
- closing


sentiment:
- positive
- neutral
- negative


Formato obligatorio:

{{
 "intent": "",
 "sales_stage": "",
 "sentiment": "",
 "objections": [],
 "primary_objection": null,
 "buying_signal": false,
 "next_step": null,
 "summary": "",
 "coach": ""
}}


Reglas importantes:

- "Estamos buscando una solución" indica necesidad, no compra.
- "Estamos evaluando alternativas" indica evaluación, no competencia.
- Una objeción solo existe si el cliente expresa una barrera.
- No confundas problemas actuales con objeciones.
- No marques buying_signal salvo intención clara.
"""


        response = (
            self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={
                    "type": "json_object"
                },
                messages=[
                    {
                        "role": "system",
                        "content":
                        "Eres un analista senior de ventas B2B."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
            )
        )



        data = json.loads(
            response.choices[0]
            .message
            .content
        )



        return ConversationInsight(

            intent=data.get(
                "intent",
                "unknown"
            ),

            objections=data.get(
                "objections",
                []
            ),

            primary_objection=data.get(
                "primary_objection"
            ),

            sentiment=data.get(
                "sentiment",
                "neutral"
            ),

            summary=data.get(
                "summary",
                transcript[:350]
            ),

            buying_signal=data.get(
                "buying_signal",
                False
            ),

            next_step=data.get(
                "next_step"
            ),

            sales_stage=data.get(
                "sales_stage",
                "discovery"
            ),
        )