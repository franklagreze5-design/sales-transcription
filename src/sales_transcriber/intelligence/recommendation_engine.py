"""recommendation_engine.py"""

from sales_transcriber.intelligence.models import (
    ConversationInsight,
)

from sales_transcriber.intelligence.conversation_state import (
    ConversationState,
)



class RecommendationEngine:


    def generate(
        self,
        insight: ConversationInsight,
        state: ConversationState | None = None,
    ) -> str:


        #
        # Propuesta
        #

        if insight.next_step == "proposal":

            return (
                "Cliente solicita propuesta. "
                "Confirma alcance, necesidades "
                "y próximos pasos."
            )



        #
        # Demo
        #

        if insight.next_step == "demo":

            return (
                "Cliente solicitó una demo. "
                "Agenda fecha, participantes "
                "y objetivo."
            )



        #
        # Competencia + presupuesto
        #

        if (
            "competitor" in insight.objections
            and "budget" in insight.objections
        ):

            return (
                "Cliente evaluando alternativas "
                "y presupuesto. "
                "No competir solo por precio. "
                "Diferencia valor y demuestra ROI."
            )



        #
        # Competencia
        #

        if "competitor" in insight.objections:

            return (
                "Cliente evaluando alternativas. "
                "Descubre criterios de decisión "
                "y diferenciadores."
            )



        #
        # Presupuesto
        #

        if "budget" in insight.objections:

            return (
                "Cliente preocupado por presupuesto. "
                "Explora impacto económico y "
                "conecta solución con ROI."
            )



        #
        # Estado acumulado
        #

        if state:

            if state.proposal_requested:

                return (
                    "Seguimiento recomendado: "
                    "preparar propuesta y validar "
                    "criterios de decisión."
                )


            if state.risk_level == "high":

                return (
                    "Oportunidad con riesgo alto. "
                    "Validar competencia, presupuesto "
                    "y valor diferencial."
                )



        #
        # General
        #

        return (
            "Continúa descubriendo necesidades "
            "del cliente."
        )