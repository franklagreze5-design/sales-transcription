from sales_transcriber.intelligence.conversation_state import (
    ConversationState,
)


class OpportunityScoring:
    """
    Calcula oportunidad comercial.

    Filosofía:
    - Tener dolor no significa comprar.
    - Discovery temprano mantiene score bajo.
    - Evaluación aumenta moderadamente.
    - Demo/propuesta son señales fuertes.

    0   = oportunidad fría
    100 = oportunidad muy caliente
    """



    def calculate(
        self,
        insight,
        state: ConversationState,
    ) -> int:


        #
        # Base
        #
        # Una conversación existe,
        # pero todavía no sabemos si hay oportunidad.
        #

        score = 15



        #
        # Dolor detectado
        #
        # Problema real, pero aún discovery.
        #

        if state.pain_detected:

            score += 15



        #
        # Cliente evaluando soluciones
        #

        if (
            insight.intent == "evaluation"
            or
            state.evaluation_started
        ):

            score += 15



        #
        # Interés explícito
        #

        if insight.intent == "interest":

            score += 25



        #
        # Sentimiento positivo
        #

        if insight.sentiment == "positive":

            score += 5



        #
        # Buying signal real
        #

        if insight.buying_signal:

            score += 20



        #
        # Próximos pasos
        #

        if insight.next_step == "demo":

            score += 25



        if insight.next_step == "proposal":

            score += 40



        #
        # Estado acumulado
        #

        if state.demo_requested:

            score += 10



        if state.proposal_requested:

            score += 15



        if state.pricing_discussed:

            score += 5



        #
        # Penalizaciones
        #

        if "budget" in state.objections:

            score -= 15



        if "competitor" in state.objections:

            score -= 5



        #
        # Reglas mínimas inteligentes
        #

        #
        # Cliente con problema identificado
        # pero sin intención comercial
        #

        if (
            state.pain_detected
            and
            not state.buying_signal_detected
            and
            not state.demo_requested
            and
            not state.proposal_requested
        ):

            score = min(
                score,
                35
            )



        #
        # Cliente evaluando alternativas
        #

        if (
            state.evaluation_started
            and
            not state.buying_signal_detected
        ):

            score = max(
                score,
                40
            )



        #
        # Demo significa oportunidad real
        #

        if state.demo_requested:

            score = max(
                score,
                70
            )



        #
        # Propuesta significa oportunidad avanzada
        #

        if state.proposal_requested:

            score = max(
                score,
                85
            )



        #
        # Límites
        #

        score = max(
            0,
            min(
                score,
                100
            )
        )


        return score