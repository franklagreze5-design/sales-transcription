"""Rule-based next-best-action engine."""

from sales_transcriber.intelligence.conversation_state import ConversationState
from sales_transcriber.intelligence.models import ConversationInsight


class RecommendationEngine:
    def generate(
        self,
        insight: ConversationInsight,
        state: ConversationState | None = None,
    ) -> str:
        if insight.next_step == "proposal":
            return (
                "Cliente solicita propuesta. "
                "Confirma alcance, necesidades y proximos pasos."
            )

        if insight.next_step == "demo":
            return (
                "Cliente solicito una demo. "
                "Agenda fecha, participantes y objetivo."
            )

        if "competitor" in insight.objections and "budget" in insight.objections:
            return (
                "Cliente evaluando alternativas y presupuesto. "
                "No competir solo por precio. Diferencia valor y demuestra ROI."
            )

        if "competitor" in insight.objections:
            return (
                "Cliente evaluando alternativas. "
                "Descubre criterios de decision y diferenciadores."
            )

        if "budget" in insight.objections:
            return (
                "Cliente preocupado por presupuesto. "
                "Explora impacto economico y conecta solucion con ROI."
            )

        if state:
            if state.proposal_requested:
                return (
                    "Seguimiento recomendado: "
                    "preparar propuesta y validar criterios de decision."
                )

            if state.risk_level == "high":
                return (
                    "Oportunidad con riesgo alto. "
                    "Validar competencia, presupuesto y valor diferencial."
                )

        return (
            "Pregunta que sistema usan hoy "
            "y donde se pierde la informacion comercial."
        )
