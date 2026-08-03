from sales_transcriber.intelligence.conversation_state import (
    ConversationState,
)

from sales_transcriber.intelligence.models import (
    ConversationInsight,
)


class ConversationStateManager:
    """
    Gestiona actualización del estado comercial.

    La lógica vive en ConversationState.
    Este componente solamente orquesta.
    """



    def update(
        self,
        state: ConversationState,
        insight: ConversationInsight,
    ) -> ConversationState:
        """
        Aplica un nuevo insight al estado acumulado.
        """


        state.update_from_insight(
            insight
        )


        return state