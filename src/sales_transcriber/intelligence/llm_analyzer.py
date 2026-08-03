from __future__ import annotations

import json

import ollama

from sales_transcriber.intelligence.models import (
    ConversationInsight,
)


class LLMConversationAnalyzer:
    """
    Analizador comercial usando LLM local (Ollama).

    Reemplaza reglas manuales por comprensión
    contextual de la conversación.
    """

    def __init__(
        self,
        model: str = "qwen3:8b",
    ) -> None:

        self._model = model



    def analyze(
        self,
        transcript: str,
    ) -> ConversationInsight:


        prompt = f"""
Eres un analista experto en ventas B2B.

Analiza la conversación comercial.

Tu respuesta debe ser EXCLUSIVAMENTE JSON válido.
No agregues explicaciones.
No uses markdown.
No escribas texto antes o después del JSON.

IMPORTANTE:

Usa solamente estos valores permitidos.

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
- pricing
- objection
- closing


sentiment:
- positive
- neutral
- negative


Reglas:

- "Estamos buscando una solución"
  significa discovery o evaluation.

- "Evaluar alternativas", "evaluar opciones",
  "comparar proveedores"
  NO es una objeción.

- Solo detecta objections si el cliente expresa:
  precio alto, falta de presupuesto,
  problema con proveedor actual,
  rechazo o duda explícita.

- buying_signal debe ser true cuando:
  existe una necesidad clara,
  están evaluando soluciones,
  piden demo,
  piden propuesta,
  quieren avanzar.

- No inventes presupuesto.
- No inventes competencia.
- No inventes próximos pasos.


Devuelve exactamente esta estructura:

{{
  "intent": "",
  "sales_stage": "",
  "buying_signal": false,
  "objections": [],
  "summary": "",
  "primary_objection": null,
  "sentiment": "neutral",
  "next_step": null
}}


Conversación:

{transcript}
"""


        response = ollama.chat(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            think=False,
            options={
                "temperature":0,
                "num_predict":120,
            },
        )

        print("\n========== RESPONSE ==========")
        print(type(response))
        print(response)

        print("==============================\n")

        content = (
            response["message"]["content"]
            .strip())
        #
        # Limpieza por si devuelve markdown
        #

        if content.startswith(
            "```json"
        ):

            content = (
                content
                .replace(
                    "```json",
                    ""
                )
                .replace(
                    "```",
                    ""
                )
                .strip()
            )


        elif content.startswith(
            "```"
        ):

            content = (
                content
                .replace(
                    "```",
                    ""
                )
                .strip()
            )



        try:

            data = json.loads(
                content
            )


        except json.JSONDecodeError:


            #
            # Fallback seguro
            #

            return ConversationInsight(

                intent="unknown",

                objections=[],

                primary_objection=None,

                sentiment="neutral",

                summary=transcript[:350],

                buying_signal=False,

                next_step=None,

                sales_stage="discovery",
            )



        return ConversationInsight(

            intent=data.get(
                "intent",
                "unknown",
            ),


            objections=data.get(
                "objections",
                [],
            ),


            primary_objection=data.get(
                "primary_objection"
            ),


            sentiment=data.get(
                "sentiment",
                "neutral",
            ),


            summary=data.get(
                "summary",
                transcript[:350],
            ),


            buying_signal=data.get(
                "buying_signal",
                False,
            ),


            next_step=data.get(
                "next_step"
            ),


            sales_stage=data.get(
                "sales_stage",
                "discovery",
            ),

        )