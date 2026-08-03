"""
sales_coach.py
"""

from __future__ import annotations

from sales_transcriber.intelligence.models import (
    ConversationInsight,
)


class SalesCoach:


    def coach(
        self,
        insight: ConversationInsight,
        transcript: str,
    ) -> str:


        #
        # PRIORIDAD 1
        # Demo
        #

        if insight.next_step == "demo":

            return (
                "El cliente está listo para avanzar.\n"
                "Confirma fecha y participantes de la demo.\n"
                "Define objetivo principal de la reunión.\n"
                "Evita volver a discutir precio antes de validar valor."
            )


        #
        # PRIORIDAD 2
        # Propuesta
        #

        if insight.next_step == "proposal":

            return (
                "El cliente solicita propuesta.\n"
                "Confirma alcance y necesidades.\n"
                "Alinea expectativas antes de enviar oferta."
            )


        #
        # PRIORIDAD 3
        # Competencia + presupuesto
        #

        if (
            "competitor" in insight.objections
            and "budget" in insight.objections
        ):

            return (
                "Cliente evaluando alternativas y presupuesto.\n"
                "No competir solo por precio.\n"
                "Descubre criterios de decisión.\n"
                "Diferencia valor frente a competidores.\n"
                "Conecta la solución con ROI."
            )


        #
        # PRIORIDAD 4
        # Compra con barrera
        #

        if (
            insight.buying_signal
            and insight.objections
        ):

            return (
                "Existe intención de compra, pero hay una barrera.\n"
                "Identifica qué necesita resolver el cliente para avanzar.\n"
                "Trabaja la objeción sin perder el momentum comercial."
            )


        #
        # PRIORIDAD 5
        # Competencia
        #

        if "competitor" in insight.objections:

            return (
                "Cliente evaluando otras alternativas.\n"
                "Pregunta qué factores usará para decidir.\n"
                "Identifica diferenciadores frente a competidores."
            )


        #
        # PRIORIDAD 6
        # Presupuesto
        #

        if "budget" in insight.objections:

            return (
                "Cliente preocupado por presupuesto.\n"
                "Explora impacto económico actual.\n"
                "Conecta solución con retorno de inversión.\n"
                "Evalúa piloto o plan inicial."
            )


        #
        # PRIORIDAD 7
        # Compra
        #

        if insight.buying_signal:

            return (
                "El cliente muestra intención de compra.\n"
                "Busca compromiso concreto.\n"
                "Propón siguiente paso con fecha definida."
            )


        #
        # PRIORIDAD 8
        # Precio
        #

        if insight.intent == "pricing":

            return (
                "Cliente consultando precios.\n"
                "Relaciona precio con valor y beneficios."
            )


        return (
            "Continúa descubriendo necesidades del cliente."
        )