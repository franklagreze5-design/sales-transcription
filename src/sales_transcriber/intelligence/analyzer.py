from sales_transcriber.intelligence.models import (
    ConversationInsight,
)


from sales_transcriber.intelligence.intents import (

    PRICING_KEYWORDS,

    IMPLEMENTATION_KEYWORDS,

    INTEREST_KEYWORDS,

    PAIN_KEYWORDS,

    EVALUATION_KEYWORDS,

    BUDGET_OBJECTIONS,

    COMPETITOR_OBJECTIONS,

    BUYING_SIGNALS,

    NEXT_STEP_DEMO,

    NEXT_STEP_PROPOSAL,

    POSITIVE_WORDS,

    NEGATIVE_WORDS,

)



class ConversationAnalyzer:
    """
    Analiza una conversación comercial.

    Detecta:
    - intención
    - etapa comercial
    - objeciones
    - señales de compra
    - sentimiento
    """



    def analyze(
        self,
        transcript: str,
    ) -> ConversationInsight:


        text = transcript.lower()



        next_step = self._detect_next_step(
            text
        )



        intent = self._detect_intent(
            text,
            next_step,
        )



        objections = self._detect_objections(
            text
        )



        primary_objection = (
            self._detect_primary_objection(
                objections
            )
        )



        sentiment = self._detect_sentiment(
            text
        )



        buying_signal = (
            self._detect_buying_signal(
                text,
                next_step,
            )
        )



        sales_stage = (
            self._detect_sales_stage(
                intent,
                objections,
                buying_signal,
                next_step,
            )
        )



        return ConversationInsight(

            intent=intent,

            objections=objections,

            primary_objection=primary_objection,

            sentiment=sentiment,

            summary=transcript[:350],

            buying_signal=buying_signal,

            next_step=next_step,

            sales_stage=sales_stage,

        )




    def _detect_intent(
        self,
        text: str,
        next_step: str | None,
    ) -> str:



        #
        # Señal fuerte de avance
        #

        if next_step == "proposal":

            return "interest"



        #
        # Pricing
        #

        if any(
            keyword in text
            for keyword in PRICING_KEYWORDS
        ):

            return "pricing"




        #
        # Implementación
        #

        if any(
            keyword in text
            for keyword in IMPLEMENTATION_KEYWORDS
        ):

            return "implementation"




        #
        # Evaluación comercial
        #
        # Cliente comparando opciones.
        # NO es objeción.
        #

        if any(
            keyword in text
            for keyword in EVALUATION_KEYWORDS
        ):

            return "evaluation"




        #
        # Dolor / necesidad
        #

        if any(
            keyword in text
            for keyword in PAIN_KEYWORDS
        ):

            return "discovery"




        #
        # Interés explícito
        #

        if any(
            keyword in text
            for keyword in INTEREST_KEYWORDS
        ):

            return "interest"



        return "unknown"




    def _detect_objections(
        self,
        text: str,
    ) -> list[str]:


        objections = []



        #
        # Presupuesto
        #

        if any(
            keyword in text
            for keyword in BUDGET_OBJECTIONS
        ):

            objections.append(
                "budget"
            )




        #
        # Competencia real
        #

        if any(
            keyword in text
            for keyword in COMPETITOR_OBJECTIONS
        ):

            objections.append(
                "competitor"
            )



        return objections




    def _detect_primary_objection(
        self,
        objections: list[str],
    ) -> str | None:



        if "budget" in objections:

            return "budget"



        if "competitor" in objections:

            return "competitor"



        return None




    def _detect_sentiment(
        self,
        text: str,
    ) -> str:



        positive = sum(
            1
            for word in POSITIVE_WORDS
            if word in text
        )



        negative = sum(
            1
            for word in NEGATIVE_WORDS
            if word in text
        )



        if positive > negative:

            return "positive"



        if negative > positive:

            return "negative"



        return "neutral"




    def _detect_buying_signal(
        self,
        text: str,
        next_step: str | None,
    ) -> bool:



        if next_step in [
            "demo",
            "proposal",
        ]:

            return True



        return any(
            signal in text
            for signal in BUYING_SIGNALS
        )




    def _detect_next_step(
        self,
        text: str,
    ) -> str | None:



        if any(
            phrase in text
            for phrase in NEXT_STEP_PROPOSAL
        ):

            return "proposal"




        if any(
            phrase in text
            for phrase in NEXT_STEP_DEMO
        ):

            return "demo"



        return None




    def _detect_sales_stage(
        self,
        intent: str,
        objections: list[str],
        buying_signal: bool,
        next_step: str | None,
    ) -> str:



        if next_step:

            return "closing"



        #
        # Solo objeción real
        #

        if objections:

            return "objection"



        if buying_signal:

            return "evaluation"



        if intent == "pricing":

            return "pricing"



        if intent == "implementation":

            return "evaluation"



        if intent == "interest":

            return "presentation"



        if intent == "evaluation":

            return "evaluation"



        if intent == "discovery":

            return "discovery"



        return "discovery"