from __future__ import annotations

import json
import os
import unicodedata

try:
    import ollama
except Exception:  # pragma: no cover - optional dependency
    ollama = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None

from sales_transcriber.intelligence.models import (
    ConversationInsight,
)


class LLMConversationAnalyzer:
    """
    Analizador comercial usando LLM local (Ollama).

    El LLM es la única fuente de verdad:
    - intención / etapa / sentimiento / objeciones
    - opportunity_score y risk_level
    - extracción comercial estructurada
    - consejos de coach

    Reemplaza OpportunityScoring y SalesCoach (basados en reglas).
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        ollama_model: str | None = None,
    ) -> None:

        key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self._provider = (
            provider
            or os.getenv("LLM_PROVIDER")
            or ("openai" if key else "rules")
        ).strip().lower()
        self._model = model or os.getenv("LLM_MODEL") or "gpt-4.1-mini"
        self._api_key = key
        self._ollama_model = ollama_model or os.getenv("OLLAMA_MODEL") or "qwen3:1.7b"

    def analyze(
        self,
        transcript: str,
    ) -> ConversationInsight:

        prompt = f"""
Eres un analista experto en ventas B2B y sales coach.

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

risk_level:
- low
- medium
- high

Reglas de clasificación:

- "Estamos buscando una solución" significa discovery o evaluation.
- "Evaluar alternativas", "evaluar opciones", "comparar proveedores"
  NO es una objeción, es intent=evaluation.
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
- No inventes presupuesto, competencia ni próximos pasos que no
  estén explícitos o fuertemente implícitos en el texto.

Reglas de opportunity_score (0-100):

- Tener dolor NO significa que vayan a comprar. Discovery temprano
  sin más señales: score bajo (15-35).
- Evaluación activa de soluciones (sin buying signal fuerte): score
  moderado (~40-55).
- buying_signal=true sube el score considerablemente.
- next_step="demo" implica score alto (>=70).
- next_step="proposal" implica score muy alto (>=85).
- Objeciones de presupuesto o competencia bajan el score, pero no
  lo anulan si hay intención real de avanzar.

Reglas de risk_level:

- "high" si hay objeción de presupuesto Y de competencia a la vez.
- "medium" si hay una de las dos.
- "low" en cualquier otro caso.

Reglas de coach_advice (lista de 2 a 4 frases cortas, accionables,
en español, en orden de prioridad):

- Da instrucciones concretas que el vendedor pueda decir ahora.
- Evita frases genericas como "seguir descubriendo necesidades".
- Si falta informacion clave, sugiere una pregunta literal y dirigida.
- Usa el contexto del cliente si existe: rubro, tamaño de compañia,
  cantidad de personas en operaciones y fecha.
- Para discovery, pregunta por volumen, equipo involucrado, proceso
  actual, impacto economico, urgencia y criterios de decision.
- Ejemplos de buenas instrucciones:
  "Preguntale cuantas personas participan hoy en operaciones y quien
   aprueba cambios de proceso."
  "Valida cuantas oportunidades pierden al mes por falta de seguimiento."
  "Pregunta que sistema usan hoy y que dato no queda registrado."

- Si next_step="demo": confirmar fecha/participantes, definir
  objetivo de la reunión, evitar hablar de precio antes de validar
  valor.
- Si next_step="proposal": confirmar alcance y necesidades, alinear
  expectativas antes de enviar la oferta.
- Si hay objeción de competencia Y presupuesto: no competir solo
  por precio, descubrir criterios de decisión, diferenciar valor,
  conectar con ROI.
- Si hay buying_signal con objeciones: identificar la barrera
  específica y trabajarla sin perder el momentum.
- Si solo hay objeción de competencia: preguntar qué factores
  usará para decidir, identificar diferenciadores.
- Si solo hay objeción de presupuesto: explorar impacto económico,
  conectar con ROI, evaluar piloto o plan inicial.
- Si hay buying_signal sin objeciones: buscar compromiso concreto
  con fecha definida.
- Si intent="pricing": relacionar precio con valor y beneficios.
- Si nada de lo anterior aplica: seguir descubriendo necesidades.

Otros campos:

- pain_points: lista corta de problemas o dolores explícitos del
  cliente (puede ser []).
- business_goals: lista corta de objetivos de negocio que el
  cliente menciona (puede ser []).
- competitors: nombres de competidores mencionados explícitamente
  (puede ser []).
- budget_status: "approved", "limited", "unknown" o null si no se
  menciona.
- timeline: descripción corta del plazo mencionado (ej.
  "next_months") o null si no se menciona.
- decision_maker: rol o nombre del decisor si se menciona,
  null si no.

Devuelve exactamente esta estructura:

{{
  "intent": "",
  "sales_stage": "",
  "buying_signal": false,
  "objections": [],
  "summary": "",
  "primary_objection": null,
  "sentiment": "neutral",
  "next_step": null,
  "opportunity_score": 15,
  "risk_level": "low",
  "pain_points": [],
  "business_goals": [],
  "competitors": [],
  "budget_status": null,
  "timeline": null,
  "decision_maker": null,
  "coach_advice": []
}}

Conversación:

{transcript}
"""

        content = self._completion_content(prompt)
        if not content:
            return self._rule_based_analyze(transcript)

        #
        # Limpieza por si devuelve markdown
        #

        if content.startswith("```json"):

            content = (
                content
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        elif content.startswith("```"):

            content = (
                content
                .replace("```", "")
                .strip()
            )

        try:

            data = json.loads(content)

        except json.JSONDecodeError:

            #
            # Fallback seguro
            #

            return self._rule_based_analyze(transcript)

        insight = ConversationInsight(

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

            opportunity_score=data.get(
                "opportunity_score",
                0,
            ),

            risk_level=data.get(
                "risk_level",
                "low",
            ),

            pain_points=data.get(
                "pain_points",
                [],
            ),

            business_goals=data.get(
                "business_goals",
                [],
            ),

            competitors=data.get(
                "competitors",
                [],
            ),

            budget_status=data.get(
                "budget_status"
            ),

            timeline=data.get(
                "timeline"
            ),

            decision_maker=data.get(
                "decision_maker"
            ),

            coach_advice=data.get(
                "coach_advice",
                [],
            ),
        )

        return self._apply_signal_overrides(
            transcript,
            insight,
        )

    def _completion_content(self, prompt: str) -> str | None:
        if self._provider == "openai":
            return self._openai_completion(prompt)
        if self._provider == "ollama":
            return self._ollama_completion(prompt)
        return None

    def _openai_completion(self, prompt: str) -> str | None:
        if not self._api_key or OpenAI is None:
            return None
        try:
            client = OpenAI(api_key=self._api_key)
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un sales coach B2B. Responde solo JSON "
                            "valido, sin markdown ni explicaciones."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            return None

    def _ollama_completion(self, prompt: str) -> str | None:
        if ollama is None:
            return None
        try:
            response = ollama.chat(
                model=self._ollama_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                think=False,
                options={
                    "temperature": 0,
                    "num_predict": 500,
                },
            )
            return response["message"]["content"].strip()
        except Exception:
            return None

    def _apply_signal_overrides(
        self,
        transcript: str,
        insight: ConversationInsight,
    ) -> ConversationInsight:
        """Keep critical sales signals from being under-scored."""

        text = self._normalize_text(transcript)

        demo_signal = any(
            phrase in text
            for phrase in {
                "agendar una demo",
                "agendar demo",
                "demo la proxima",
                "hacer una demo",
                "programar una demo",
                "quiero una demo",
                "queremos una demo",
                "agendar una reunion",
                "agendaramos una reunion",
                "agendaramos una reunion un demo",
                "reunion para comprender",
                "comprender como funciona la solucion",
            }
        )

        plan_interest_signal = any(
            phrase in text
            for phrase in {
                "me interesa el plan",
                "me interesa este plan",
                "me interesa la solucion",
                "dentro de nuestro presupuesto",
                "solucion estaba dentro de nuestro presupuesto",
            }
        )

        proposal_signal = any(
            phrase in text
            for phrase in {
                "propuesta comercial",
                "recibir una propuesta",
                "enviar una propuesta",
            }
        )

        budget_signal = any(
            phrase in text
            for phrase in {
                "tenemos presupuesto",
                "presupuesto definido",
                "hay presupuesto",
                "dentro de nuestro presupuesto",
            }
        )

        budget_objection_signal = any(
            phrase in text
            for phrase in {
                "muy caro",
                "caro para mi",
                "precio alto",
                "comparando costos",
                "costos entre proveedores",
            }
        )

        if demo_signal or plan_interest_signal:
            insight.buying_signal = True
            insight.next_step = "demo"
            insight.sales_stage = "closing"
            insight.intent = "interest"
            insight.opportunity_score = max(
                insight.opportunity_score,
                80,
            )
            if not insight.coach_advice:
                insight.coach_advice = [
                    "Confirma fecha, participantes y objetivo concreto de la demo.",
                    "Alinea criterios de exito antes de hablar de precio.",
                ]

        if proposal_signal:
            insight.buying_signal = True
            insight.next_step = "proposal"
            insight.sales_stage = "closing"
            insight.intent = "pricing"
            insight.opportunity_score = max(
                insight.opportunity_score,
                85,
            )

        if budget_signal:
            if not insight.budget_status or insight.budget_status == "unknown":
                insight.budget_status = "approved"
            insight.opportunity_score = max(
                insight.opportunity_score,
                65,
            )

        if budget_objection_signal:
            if "budget" not in insight.objections:
                insight.objections.append("budget")
            insight.primary_objection = insight.primary_objection or "budget"
            if insight.risk_level == "low":
                insight.risk_level = "medium"

        if insight.buying_signal:
            insight.opportunity_score = max(
                insight.opportunity_score,
                60,
            )

        if (
            insight.timeline
            and str(insight.timeline).count("-") == 2
            and "fecha reunion" in text
        ):
            insight.timeline = None

        return insight

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", text)
        normalized = "".join(
            char
            for char in normalized
            if unicodedata.category(char) != "Mn"
        )
        cleaned = "".join(
            char.lower() if char.isalnum() else " "
            for char in normalized
        )
        return " ".join(cleaned.split())

    def _rule_based_analyze(self, transcript: str) -> ConversationInsight:
        """Lightweight local coach for PCs without Ollama."""

        text = self._normalize_text(transcript)

        demo_signal = any(
            phrase in text
            for phrase in {
                "agendar una demo",
                "agendar demo",
                "agendar una reunion",
                "agendaramos una reunion",
                "comprender como funciona la solucion",
                "hacer una demo",
                "programar una demo",
                "quiero una demo",
                "queremos una demo",
            }
        )
        proposal_signal = any(
            phrase in text
            for phrase in {
                "propuesta comercial",
                "recibir una propuesta",
                "enviar una propuesta",
            }
        )
        pricing_signal = any(
            phrase in text
            for phrase in {
                "precio",
                "precios",
                "costo",
                "costos",
                "plan",
                "presupuesto",
            }
        )
        budget_signal = any(
            phrase in text
            for phrase in {
                "tenemos presupuesto",
                "presupuesto definido",
                "dentro de nuestro presupuesto",
                "hay presupuesto",
            }
        )
        budget_objection = any(
            phrase in text
            for phrase in {
                "muy caro",
                "caro para mi",
                "precio alto",
                "comparando costos",
                "costos entre proveedores",
            }
        )
        competitor_signal = any(
            phrase in text
            for phrase in {
                "proveedores",
                "alternativas",
                "competencia",
                "competidor",
                "salesforce",
            }
        )
        pain_signal = any(
            phrase in text
            for phrase in {
                "problema",
                "problemas",
                "perdido",
                "perdemos",
                "pierden",
                "seguimiento",
                "manual",
                "sobrepasados",
                "no queda registrado",
                "no lo tenemos centralizado",
            }
        )
        buying_signal = demo_signal or proposal_signal or "me interesa" in text

        next_step = None
        if proposal_signal:
            next_step = "proposal"
        if demo_signal:
            next_step = "demo"

        intent = "discovery"
        sales_stage = "discovery"
        score = 25
        if pain_signal:
            score = 40
        if competitor_signal or pricing_signal:
            intent = "evaluation"
            sales_stage = "evaluation"
            score = max(score, 55)
        if buying_signal:
            intent = "interest"
            sales_stage = "closing"
            score = max(score, 75)
        if next_step == "demo":
            score = max(score, 80)
        if next_step == "proposal":
            intent = "pricing"
            score = max(score, 85)

        objections = []
        if budget_objection:
            objections.append("budget")
        if competitor_signal and "comparando" in text:
            objections.append("competitor")

        risk_level = "low"
        if "budget" in objections or "competitor" in objections:
            risk_level = "medium"
        if "budget" in objections and "competitor" in objections:
            risk_level = "high"

        pain_points = []
        if "seguimiento" in text:
            pain_points.append("falta de seguimiento comercial")
        if any(word in text for word in ["perdido", "pierden", "perdemos"]):
            pain_points.append("perdida de clientes u oportunidades")
        if "manual" in text or "centralizado" in text:
            pain_points.append("proceso manual o informacion no centralizada")
        if "sobrepasados" in text:
            pain_points.append("equipo comercial sobrepasado")

        business_goals = []
        if "retencion" in text:
            business_goals.append("mejorar retencion de clientes")
        if "visibilidad" in text or "pipeline" in text:
            business_goals.append("mejorar visibilidad del pipeline")
        if "demo" in text or "reunion" in text:
            business_goals.append("validar la solucion en una demo")

        budget_status = "approved" if budget_signal else "unknown"
        if budget_objection and not budget_signal:
            budget_status = "limited"

        timeline = None
        if "proxima semana" in text or "otra semana" in text:
            timeline = "next_week"
        elif "proximos meses" in text or "trimestre" in text:
            timeline = "next_months"

        summary_parts = []
        if pain_points:
            summary_parts.append(
                "Cliente presenta dolores comerciales: "
                + ", ".join(pain_points[:3])
                + "."
            )
        if pricing_signal:
            summary_parts.append("Pregunta por precios, planes o presupuesto.")
        if demo_signal:
            summary_parts.append("Solicita avanzar a una demo o reunion de validacion.")
        summary = " ".join(summary_parts) or transcript[:350]

        coach_advice = self._rule_based_coach(
            next_step=next_step,
            budget_objection=budget_objection,
            pricing_signal=pricing_signal,
            pain_signal=pain_signal,
            buying_signal=buying_signal,
        )

        insight = ConversationInsight(
            intent=intent,
            objections=objections,
            primary_objection=objections[0] if objections else None,
            sentiment="positive" if buying_signal else "neutral",
            summary=summary,
            buying_signal=buying_signal,
            next_step=next_step,
            sales_stage=sales_stage,
            opportunity_score=score,
            risk_level=risk_level,
            pain_points=pain_points,
            business_goals=business_goals,
            competitors=[],
            budget_status=budget_status,
            timeline=timeline,
            decision_maker=None,
            coach_advice=coach_advice,
        )
        return self._apply_signal_overrides(transcript, insight)

    def _rule_based_coach(
        self,
        next_step: str | None,
        budget_objection: bool,
        pricing_signal: bool,
        pain_signal: bool,
        buying_signal: bool,
    ) -> list[str]:
        if next_step == "demo":
            return [
                "Confirma fecha, participantes y objetivo concreto de la demo.",
                "Pregunta que criterio usaran para decidir despues de la demo.",
                "Alinea expectativas antes de hablar de precio final.",
            ]
        if next_step == "proposal":
            return [
                "Confirma alcance, necesidades y fecha de envio de la propuesta.",
                "Valida quien aprueba la propuesta y que criterios usara.",
            ]
        if budget_objection:
            return [
                "Pregunta cuanto les cuesta hoy perder oportunidades por falta de seguimiento.",
                "Conecta el precio con ROI antes de ofrecer descuento.",
            ]
        if pricing_signal:
            return [
                "Pregunta que volumen de reuniones o clientes debe cubrir el plan.",
                "Valida presupuesto disponible y urgencia de implementacion.",
            ]
        if pain_signal:
            return [
                "Valida cuantas oportunidades pierden al mes por falta de seguimiento.",
                "Pregunta que sistema usan hoy y que dato no queda registrado.",
            ]
        if buying_signal:
            return [
                "Busca un compromiso concreto con fecha definida.",
            ]
        return [
            "Pregunta por volumen de clientes, equipo involucrado y proceso actual.",
        ]
