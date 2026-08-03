from dataclasses import dataclass, field



@dataclass
class ConversationState:
    """
    Memoria acumulada de la conversación comercial.

    Guarda contexto entre múltiples segmentos
    de una misma conversación.
    """



    #
    # Necesidad / dolor detectado
    #

    pain_detected: bool = False

    pain_topics: list[str] = field(
        default_factory=list
    )



    #
    # Etapas de conversación
    #

    pricing_discussed: bool = False

    implementation_discussed: bool = False

    evaluation_started: bool = False



    #
    # Objeciones acumuladas
    #

    objection_detected: bool = False

    objections: list[str] = field(
        default_factory=list
    )



    #
    # Acciones comerciales
    #

    demo_requested: bool = False

    proposal_requested: bool = False



    #
    # Señales comerciales
    #

    buying_signal_detected: bool = False



    #
    # Pipeline
    #

    sales_stage: str = "discovery"



    #
    # Scoring
    #

    opportunity_score: int = 0



    #
    # Riesgo
    #

    risk_level: str = "low"



    #
    # Métricas
    #

    analyzed_segments: int = 0



    def update_from_insight(
        self,
        insight,
    ) -> None:
        """
        Actualiza memoria usando un insight comercial.
        """

        self.analyzed_segments += 1



        #
        # Detectar dolor
        #

        if insight.intent == "discovery":

            self.pain_detected = True



        #
        # Evaluación comercial
        #

        if insight.intent == "evaluation":

            self.evaluation_started = True



        #
        # Pricing
        #

        if insight.intent == "pricing":

            self.pricing_discussed = True



        #
        # Implementación
        #

        if insight.intent == "implementation":

            self.implementation_discussed = True



        #
        # Objeciones
        #

        if insight.objections:

            self.objection_detected = True


            for objection in insight.objections:

                if objection not in self.objections:

                    self.objections.append(
                        objection
                    )



        #
        # Próximos pasos
        #

        if insight.next_step == "demo":

            self.demo_requested = True



        if insight.next_step == "proposal":

            self.proposal_requested = True



        #
        # Buying signal
        #

        if insight.buying_signal:

            self.buying_signal_detected = True



        #
        # Actualizar pipeline
        #

        self._update_sales_stage()



        #
        # Actualizar riesgo
        #

        self._calculate_risk()



    def _update_sales_stage(self):
        """
        Determina etapa comercial actual.
        """


        if self.proposal_requested:

            self.sales_stage = "closing"

            return



        if self.demo_requested:

            self.sales_stage = "evaluation"

            return



        if self.evaluation_started:

            self.sales_stage = "evaluation"

            return



        if self.pain_detected:

            self.sales_stage = "discovery"

            return



        self.sales_stage = "discovery"



    def _calculate_risk(self):
        """
        Riesgo basado en contexto acumulado.
        """


        if (
            "budget" in self.objections
            and
            "competitor" in self.objections
        ):

            self.risk_level = "high"

            return



        if (
            "budget" in self.objections
            or
            "competitor" in self.objections
        ):

            self.risk_level = "medium"

            return



        self.risk_level = "low"