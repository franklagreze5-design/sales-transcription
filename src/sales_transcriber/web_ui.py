"""Local web dashboard for the sales transcription MVP."""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
import unicodedata
import webbrowser
from dataclasses import asdict, replace
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sales_transcriber.audio.capture import AudioChunk, MicrophoneError, MicrophoneRecorder
from sales_transcriber.config import AppConfig, load_config
from sales_transcriber.crm.connectors import get_crm_connector
from sales_transcriber.intelligence.conversation_state import ConversationState
from sales_transcriber.intelligence.llm_analyzer import LLMConversationAnalyzer
from sales_transcriber.intelligence.recommendation_engine import RecommendationEngine
from sales_transcriber.intelligence.speaker_detection import SpeakerDetector
from sales_transcriber.intelligence.state_manager import ConversationStateManager
from sales_transcriber.stt.factory import create_transcriber
from sales_transcriber.stt.openai_client import TranscriptionServiceError
from sales_transcriber.storage import CustomerStore
from sales_transcriber.transcription_buffer import TranscriptionBuffer


if getattr(sys, "frozen", False):
    STATIC_DIR = (
        Path(sys._MEIPASS)  # type: ignore[attr-defined]
        / "sales_transcriber"
        / "web_static"
    )
else:
    STATIC_DIR = Path(__file__).with_name("web_static")


class EventBus:
    """Fan out JSON events to connected browser clients."""

    def __init__(self) -> None:
        self._clients: list[queue.Queue[dict]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[dict]:
        client_queue: queue.Queue[dict] = queue.Queue()
        with self._lock:
            self._clients.append(client_queue)
        return client_queue

    def unsubscribe(self, client_queue: queue.Queue[dict]) -> None:
        with self._lock:
            if client_queue in self._clients:
                self._clients.remove(client_queue)

    def publish(self, event_type: str, payload: dict | None = None) -> None:
        event = {
            "type": event_type,
            "payload": payload or {},
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self._lock:
            clients = list(self._clients)
        for client_queue in clients:
            client_queue.put(event)


class NullTranscriptWriter:
    """Collect deltas through a callback without console output."""

    def __init__(self, on_delta) -> None:
        self._on_delta = on_delta

    def write_delta(self, text: str) -> None:
        self._on_delta(text)


class WebTranscriptionSession:
    """Run capture, transcription and intelligence for the dashboard."""

    def __init__(self, config: AppConfig, events: EventBus) -> None:
        self._config = config
        self._events = events
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._audio_queue: queue.Queue[AudioChunk] = queue.Queue()
        self._capture_thread: threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None
        self._running = False
        self._analysis_running = False
        self._analysis_pending = False
        self._customer_name = "Cliente sin nombre"
        self._customer_context = {
            "seller_name": "",
            "industry": "",
            "company_size": "",
            "operations_people": "",
            "meeting_date": datetime.now().date().isoformat(),
        }
        self._current_meeting_id: int | None = None
        self._audio_source = config.audio.source

        self._recorder = MicrophoneRecorder(config.audio)
        self._transcriber = create_transcriber(config.transcription)
        self._buffer = TranscriptionBuffer()
        self._analyzer = LLMConversationAnalyzer(
            provider=config.llm.provider,
            model=config.llm.model,
            api_key=config.llm.api_key,
            ollama_model=config.llm.ollama_model,
        )
        self._recommendation_engine = RecommendationEngine()
        self._speaker_detector = SpeakerDetector()
        self._conversation_state = ConversationState()
        self._state_manager = ConversationStateManager()
        self._store = CustomerStore()
        self._last_recommendation: str | None = None
        self._shown_coach_topics: set[str] = set()
        self._shown_coach_texts: set[str] = set()
        self._shown_coach_stages: set[str] = set()
        self._highest_coach_stage_rank = 0

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @staticmethod
    def _clean_customer_name(name: str | None) -> str:
        cleaned = str(name or "").strip()
        return "" if cleaned.lower() == "cliente sin nombre" else cleaned

    def has_customer_name(self) -> bool:
        with self._lock:
            return bool(self._clean_customer_name(self._customer_name))

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return False
            if not self._clean_customer_name(self._customer_name):
                raise ValueError("Selecciona un cliente existente o crea un cliente nuevo antes de iniciar.")
            self._store.save_profile(self._customer_name, self._customer_context)
            self._current_meeting_id = self._store.create_meeting(
                self._customer_name,
                self._customer_context,
            )
            self._recorder = MicrophoneRecorder(
                replace(
                    self._config.audio,
                    source=self._audio_source,
                )
            )
            self._buffer.clear()
            self._conversation_state = ConversationState()
            self._last_recommendation = None
            self._shown_coach_topics.clear()
            self._shown_coach_texts.clear()
            self._shown_coach_stages.clear()
            self._highest_coach_stage_rank = 0
            self._stop_event.clear()
            self._running = True

        self._events.publish(
            "status",
            {
                "running": True,
                "message": "Captura iniciada",
                "meeting_id": self._current_meeting_id,
            },
        )
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._capture_thread.start()
        self._worker_thread.start()
        return True

    def stop(self) -> bool:
        with self._lock:
            if not self._running:
                return False
            self._running = False
            self._stop_event.set()

        self._events.publish("status", {"running": False, "message": "Captura detenida"})
        if self._current_meeting_id is not None:
            self._store.finish_meeting(self._current_meeting_id)
        if self._buffer.size() > 0:
            self._schedule_analysis(True)
        return True

    def snapshot(self) -> dict:
        return {
            "running": self.running,
            "queue_size": self._audio_queue.qsize(),
            "customer_name": self._customer_name,
            "customer_context": self._customer_context,
            "current_meeting_id": self._current_meeting_id,
            "audio_source": self._audio_source,
            "config": {
                "provider": self._config.transcription.provider,
                "llm_provider": self._config.llm.provider,
                "llm_model": self._config.llm.model,
                "whisper_model": self._config.transcription.whisper_model,
                "language": self._config.transcription.language,
                "sample_rate": self._config.audio.sample_rate,
                "max_segment_seconds": self._config.audio.max_segment_seconds,
                "overlap_seconds": self._config.audio.overlap_seconds,
                "min_rms": self._config.audio.min_rms,
                "vad_silence_frames": self._config.audio.silence_frames_to_stop,
                "audio_source": self._audio_source,
            },
            "customers": self._customers_payload(),
            "meetings": self._meetings_payload(self._customer_name),
        }

    def set_customer_name(self, name: str) -> str:
        cleaned = self._clean_customer_name(name)
        if not cleaned:
            raise ValueError("Ingresa o selecciona un cliente antes de guardar.")
        with self._lock:
            self._customer_name = cleaned
            profile = self._store.get_profile(self._customer_name)
            if profile:
                self._customer_context.update(
                    {
                        "seller_name": profile.seller_name,
                        "industry": profile.industry,
                        "company_size": profile.company_size,
                        "operations_people": profile.operations_people,
                        "meeting_date": profile.meeting_date,
                    }
                )
        self._events.publish("customer", {"name": self._customer_name})
        self._events.publish("customer_context", self._customer_context)
        return self._customer_name

    def set_customer_context(self, data: dict) -> dict:
        allowed_fields = {
            "seller_name",
            "industry",
            "company_size",
            "operations_people",
            "meeting_date",
        }
        with self._lock:
            for key in allowed_fields:
                if key in data:
                    self._customer_context[key] = str(data.get(key, "")).strip()
            context = dict(self._customer_context)
            if self._clean_customer_name(self._customer_name):
                self._store.save_profile(self._customer_name, context)
        self._events.publish("customer_context", context)
        return context

    def set_audio_source(self, source: str) -> str:
        allowed = {"microphone", "system", "both"}
        normalized = source.strip().lower()
        if normalized not in allowed:
            normalized = "microphone"
        with self._lock:
            if self._running:
                return self._audio_source
            self._audio_source = normalized
        self._events.publish("audio_source", {"source": self._audio_source})
        return self._audio_source

    def customers(self) -> list[dict]:
        return self._customers_payload()

    def customer_history(self, customer_name: str | None = None) -> dict:
        name = customer_name or self._customer_name
        return {
            "customer_name": name,
            "meetings": self._meetings_payload(name),
        }

    def customers_csv(self) -> str:
        lines = [
            "customer_name,seller_name,industry,company_size,operations_people,meeting_count,opportunity_score,risk_level,sales_stage,budget_status,timeline,next_step,updated_at,summary"
        ]
        profile_by_name = {
            profile.customer_name: profile
            for profile in self._store.list_profiles()
        }
        for customer in self._store.list_customers():
            profile = profile_by_name.get(customer.customer_name)
            values = [
                customer.customer_name,
                profile.seller_name if profile else "",
                profile.industry if profile else "",
                profile.company_size if profile else "",
                profile.operations_people if profile else "",
                str(len(self._store.list_meetings(customer.customer_name, limit=200))),
                str(customer.opportunity_score),
                customer.risk_level,
                customer.sales_stage,
                customer.budget_status or "",
                customer.timeline or "",
                customer.next_step or "",
                customer.updated_at,
                customer.summary,
            ]
            escaped = [
                '"' + value.replace('"', '""') + '"'
                for value in values
            ]
            lines.append(",".join(escaped))
        return "\n".join(lines)

    def transcripts_csv(self, customer_name: str | None = None) -> str:
        lines = [
            "meeting_id,customer_name,speaker,created_at,elapsed,rms,queue_size,text"
        ]
        for segment in self._store.list_segments(customer_name=customer_name):
            values = [
                str(segment.meeting_id),
                segment.customer_name,
                segment.speaker or "",
                segment.created_at,
                "" if segment.elapsed is None else str(segment.elapsed),
                "" if segment.rms is None else str(segment.rms),
                "" if segment.queue_size is None else str(segment.queue_size),
                segment.text,
            ]
            escaped = ['"' + value.replace('"', '""') + '"' for value in values]
            lines.append(",".join(escaped))
        return "\n".join(lines)

    def meeting_json_payload(
        self,
        customer_name: str | None = None,
        meeting_id: int | None = None,
    ) -> dict:
        return self._store.meeting_export_payload(
            customer_name=customer_name or self._customer_name,
            meeting_id=meeting_id,
        )

    def sync_crm(
        self,
        customer_name: str | None = None,
        meeting_id: int | None = None,
        connector_name: str | None = None,
    ) -> dict:
        name = customer_name or self._customer_name
        payload = self.meeting_json_payload(name, meeting_id)
        connector = get_crm_connector(connector_name)
        result = connector.append_meeting_insight(payload)
        event = self._store.append_crm_event(
            customer_name=name,
            meeting_id=meeting_id,
            connector=result.connector,
            payload={**payload, "connector_result": result.payload},
            status=result.status,
        )
        return {
            "ok": True,
            "event": asdict(event),
            "connector": result.connector,
            "status": result.status,
            "message": result.message,
        }

    def _customers_payload(self) -> list[dict]:
        summaries = {
            customer.customer_name: asdict(customer)
            for customer in self._store.list_customers()
        }
        profiles = {
            profile.customer_name: asdict(profile)
            for profile in self._store.list_profiles()
        }
        names = list(dict.fromkeys([*profiles.keys(), *summaries.keys()]))
        payload = []
        for name in names:
            row = {
                "customer_name": name,
                "seller_name": "",
                "industry": "",
                "company_size": "",
                "operations_people": "",
                "meeting_date": "",
                "opportunity_score": 0,
                "risk_level": "--",
                "sales_stage": "--",
                "sentiment": "--",
                "buying_signal": False,
                "budget_status": "",
                "timeline": "",
                "next_step": "",
                "summary": "--",
                "pain_points": [],
                "business_goals": [],
                "updated_at": "",
            }
            row.update(profiles.get(name, {}))
            row.update(summaries.get(name, {}))
            row["meeting_count"] = len(self._store.list_meetings(name, limit=200))
            payload.append(row)
        return payload

    def _meetings_payload(self, customer_name: str | None = None) -> list[dict]:
        return [
            asdict(meeting)
            for meeting in self._store.list_meetings(customer_name=customer_name)
        ]

    def _capture_loop(self) -> None:
        try:
            for chunk in self._recorder.chunks():
                if self._stop_event.is_set():
                    break

                if chunk.rms < self._config.audio.min_rms:
                    self._events.publish(
                        "audio_skipped",
                        {"rms": round(chunk.rms, 1), "reason": "low_rms"},
                    )
                    continue

                self._audio_queue.put(chunk)
                self._events.publish(
                    "queue",
                    {"size": self._audio_queue.qsize(), "rms": round(chunk.rms, 1)},
                )
        except MicrophoneError as exc:
            self._events.publish("error", {"message": str(exc)})
            self.stop()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set() or not self._audio_queue.empty():
            try:
                chunk = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            started_at = time.time()
            deltas: list[str] = []

            def on_delta(text: str) -> None:
                deltas.append(text)
                self._events.publish("transcript_delta", {"text": text})

            try:
                transcript = self._transcriber.transcribe(
                    chunk,
                    NullTranscriptWriter(on_delta).write_delta,
                )
                elapsed = time.time() - started_at

                if transcript:
                    speaker_segment = self._speaker_detector.detect(transcript)
                    meeting_id = self._current_meeting_id
                    if meeting_id is not None:
                        self._store.save_segment(
                            meeting_id=meeting_id,
                            customer_name=self._customer_name,
                            speaker=speaker_segment.speaker,
                            text=transcript,
                            elapsed=round(elapsed, 2),
                            rms=round(chunk.rms, 1),
                            queue_size=self._audio_queue.qsize(),
                        )
                    self._events.publish(
                        "transcript_segment",
                        {
                            "text": transcript,
                            "speaker": speaker_segment.speaker,
                            "elapsed": round(elapsed, 2),
                            "rms": round(chunk.rms, 1),
                            "queue_size": self._audio_queue.qsize(),
                            "meeting_id": meeting_id,
                        },
                    )
                    self._events.publish(
                        "speaker_segment",
                        {
                            "speaker": speaker_segment.speaker,
                            "text": speaker_segment.text,
                        },
                    )
                    self._buffer.add(transcript)
                    self._events.publish("buffer", {"size": self._buffer.size()})
                    self._schedule_analysis(False)

            except TranscriptionServiceError as exc:
                self._events.publish("error", {"message": str(exc)})
            except Exception as exc:
                self._events.publish("error", {"message": f"Error inesperado: {exc}"})
            finally:
                self._audio_queue.task_done()

    def _schedule_analysis(self, final: bool) -> None:
        with self._lock:
            if self._analysis_running:
                self._analysis_pending = True
                return
            self._analysis_running = True
            self._analysis_pending = False

        threading.Thread(
            target=self._run_analysis,
            args=(final,),
            daemon=True,
        ).start()

    def _run_analysis(self, final: bool) -> None:
        try:
            transcript = self._analysis_text()
            if not transcript:
                return

            self._events.publish(
                "analysis_status",
                {"message": "Analizando conversaciÃ³n"},
            )

            insight = self._analyzer.analyze(transcript)
            self._state_manager.update(self._conversation_state, insight)
            customer_summary = self._store.save_insight(
                self._customer_name,
                insight,
            )
            if self._current_meeting_id is not None:
                self._store.finish_meeting(self._current_meeting_id, insight)
            recommendation = self._recommendation_engine.generate(
                insight,
                self._conversation_state,
            )
            recommendation = self._filter_recommendation(recommendation, insight)
            coach_advice = self._filter_coach_advice(insight.coach_advice, insight)
            insight_payload = asdict(insight)
            insight_payload["coach_advice"] = coach_advice

            self._events.publish(
                "analysis",
                {
                    "final": final,
                    "insight": insight_payload,
                    "customer": asdict(customer_summary),
                    "customers": self._customers_payload(),
                    "meetings": self._meetings_payload(self._customer_name),
                    "recommendation": recommendation,
                },
            )
        except Exception as exc:
            self._events.publish(
                "error",
                {
                    "message": (
                        "LLM error: no se pudo completar el analisis Cloud AI. "
                        "Revisa OPENAI_API_KEY en .env o usa fallback local por reglas."
                    ),
                    "detail": str(exc),
                },
            )
        finally:
            should_rerun = False
            with self._lock:
                self._analysis_running = False
                if self._analysis_pending:
                    self._analysis_pending = False
                    should_rerun = True

            if should_rerun:
                self._schedule_analysis(False)

    def _analysis_text(self) -> str:
        context = dict(self._customer_context)
        context_lines = [
            "Contexto del cliente:",
            f"- Cliente: {self._customer_name}",
            f"- Vendedor: {context.get('seller_name') or 'no informado'}",
            f"- Rubro: {context.get('industry') or 'no informado'}",
            f"- TamaÃ±o compaÃ±Ã­a: {context.get('company_size') or 'no informado'}",
            f"- Personas en operaciones: {context.get('operations_people') or 'no informado'}",
            f"- Fecha reuniÃ³n: {context.get('meeting_date') or 'no informado'}",
            "",
            "ConversaciÃ³n:",
            self._buffer.get_text(),
        ]
        return "\n".join(context_lines)

    def _filter_recommendation(self, recommendation: str | None, insight: object) -> str | None:
        if not recommendation:
            return None
        if recommendation == self._last_recommendation:
            return None
        if not self._remember_coach_item(recommendation, insight):
            return None
        self._last_recommendation = recommendation
        return recommendation

    def _filter_coach_advice(self, advice: list[str], insight: object) -> list[str]:
        filtered: list[str] = []
        for item in advice:
            if self._remember_coach_item(item, insight):
                filtered.append(item)
        return filtered[:3]

    def _remember_coach_item(self, text: str, insight: object) -> bool:
        normalized = self._normalize_coach_text(text)
        if not normalized:
            return False
        if self._is_generic_coach_text(normalized):
            return False
        topic = self._coach_topic(normalized)
        key = topic or normalized
        stage = self._coach_stage(topic, normalized, insight)
        rank = self._coach_stage_rank(stage)
        if normalized in self._shown_coach_texts:
            return False
        if key in self._shown_coach_topics:
            return False
        if stage in self._shown_coach_stages:
            return False
        if rank and rank < self._highest_coach_stage_rank:
            return False
        self._shown_coach_texts.add(normalized)
        self._shown_coach_topics.add(key)
        if stage:
            self._shown_coach_stages.add(stage)
        if rank > self._highest_coach_stage_rank:
            self._highest_coach_stage_rank = rank
        return True

    def _normalize_coach_text(self, text: str) -> str:
        text = unicodedata.normalize("NFD", text)
        text = "".join(
            char for char in text
            if unicodedata.category(char) != "Mn"
        )
        cleaned = "".join(
            char.lower() if char.isalnum() else " "
            for char in text
        )
        return " ".join(cleaned.split())

    def _coach_topic(self, normalized: str) -> str:
        topic_keywords = {
            "current_system": [
                "sistema usan",
                "herramienta usan",
                "salesforce",
                "crm usan",
                "dato no queda registrado",
            ],
            "operations_scope": [
                "cuantas personas",
                "cuantos vendedores",
                "operaciones",
                "participan",
            ],
            "decision_process": [
                "quien aprueba",
                "criterios de decision",
                "decision",
                "aprobacion",
            ],
            "proposal": [
                "propuesta",
                "alcance",
                "necesidades",
                "oferta",
            ],
            "demo": [
                "demo",
                "demostracion",
                "participantes",
                "objetivo de la reunion",
                "piloto",
                "prueba",
            ],
            "budget": [
                "presupuesto",
                "costos",
                "precio",
                "pricing",
                "plan inicial",
                "planes",
            ],
            "roi": [
                "roi",
                "impacto economico",
                "valor",
                "beneficios",
                "impacto",
                "urgencia",
            ],
            "pain": [
                "dolor detectado",
                "falta de seguimiento",
                "pierden",
                "perdida",
                "perdemos",
                "sobrepasados",
                "manual",
                "centralizada",
            ],
            "buying_signal": [
                "senal de compra",
                "compromiso concreto",
                "me interesa",
                "podemos avanzar",
            ],
            "timeline": [
                "fecha",
                "plazo",
                "trimestre",
                "proximos meses",
                "next week",
            ],
            "competition": [
                "competencia",
                "competidor",
                "proveedores",
                "alternativas",
            ],
            "discovery": [
                "descubriendo necesidades",
                "profundiza",
                "dolor",
                "urgencia",
            ],
        }
        for topic, keywords in topic_keywords.items():
            if any(keyword in normalized for keyword in keywords):
                return topic
        return ""

    def _is_generic_coach_text(self, normalized: str) -> bool:
        generic_phrases = [
            "continua descubriendo necesidades del cliente",
            "seguir descubriendo necesidades",
            "analizando senales comerciales",
        ]
        return any(phrase in normalized for phrase in generic_phrases)

    def _coach_stage(self, topic: str, normalized: str, insight: object) -> str:
        next_step = getattr(insight, "next_step", "")
        intent = getattr(insight, "intent", "")
        buying_signal = bool(getattr(insight, "buying_signal", False))

        if topic in {"demo", "proposal", "buying_signal"}:
            return "closing"
        if buying_signal and next_step in {"demo", "proposal"}:
            return "closing"
        if topic in {"budget", "roi"} or intent == "pricing":
            return "pricing"
        if topic == "pain" or "dolor" in normalized or "impacto" in normalized:
            return "pain"
        if topic in {
            "current_system",
            "operations_scope",
            "decision_process",
            "timeline",
            "competition",
            "discovery",
        }:
            return "discovery"
        return ""

    def _coach_stage_rank(self, stage: str) -> int:
        return {
            "discovery": 1,
            "pain": 2,
            "pricing": 3,
            "closing": 4,
        }.get(stage, 0)


class DashboardServer:
    """Small local HTTP server for the dashboard."""

    def __init__(self, host: str, port: int, config: AppConfig) -> None:
        self.events = EventBus()
        self.session = WebTranscriptionSession(config, self.events)
        self.server = ThreadingHTTPServer(
            (host, port),
            self._make_handler(),
        )

    def serve_forever(self) -> None:
        self.server.serve_forever()

    def _make_handler(self):
        dashboard = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed_url = urlparse(self.path)
                path = parsed_url.path
                query = parse_qs(parsed_url.query)
                if path == "/":
                    self._serve_static("index.html", "text/html; charset=utf-8")
                elif path == "/styles.css":
                    self._serve_static("styles.css", "text/css; charset=utf-8")
                elif path == "/app.js":
                    self._serve_static("app.js", "application/javascript; charset=utf-8")
                elif path == "/events":
                    self._serve_events()
                elif path == "/api/status":
                    self._send_json(dashboard.session.snapshot())
                elif path == "/api/customers":
                    self._send_json({"customers": dashboard.session.customers()})
                elif path == "/api/customer-history":
                    customer = (query.get("customer") or [None])[0]
                    self._send_json(dashboard.session.customer_history(customer))
                elif path == "/api/export-crm":
                    self._send_csv(dashboard.session.customers_csv())
                elif path == "/api/export-transcripts":
                    customer = (query.get("customer") or [None])[0]
                    self._send_csv(
                        dashboard.session.transcripts_csv(customer),
                        "sales-intel-transcripts.csv",
                    )
                elif path == "/api/export-meeting-json":
                    customer = (query.get("customer") or [None])[0]
                    meeting_id_value = (query.get("meeting_id") or [None])[0]
                    meeting_id = int(meeting_id_value) if meeting_id_value else None
                    self._send_download_json(
                        dashboard.session.meeting_json_payload(customer, meeting_id),
                        "sales-coach-crm-payload.json",
                    )
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                path = urlparse(self.path).path
                if path == "/api/start":
                    try:
                        started = dashboard.session.start()
                    except ValueError as exc:
                        self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
                        return
                    self._send_json({"ok": True, "started": started})
                elif path == "/api/stop":
                    stopped = dashboard.session.stop()
                    self._send_json({"ok": True, "stopped": stopped})
                elif path == "/api/customer":
                    body = self.rfile.read(
                        int(self.headers.get("Content-Length", "0"))
                    )
                    data = json.loads(body.decode("utf-8") or "{}")
                    try:
                        name = dashboard.session.set_customer_name(
                            data.get("name", "")
                        )
                    except ValueError as exc:
                        self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
                        return
                    self._send_json(
                        {
                            "ok": True,
                            "name": name,
                            "context": dashboard.session._customer_context,
                            "customers": dashboard.session.customers(),
                            "meetings": dashboard.session.customer_history(name)["meetings"],
                        }
                    )
                elif path == "/api/customer-context":
                    body = self.rfile.read(
                        int(self.headers.get("Content-Length", "0"))
                    )
                    data = json.loads(body.decode("utf-8") or "{}")
                    context = dashboard.session.set_customer_context(data)
                    self._send_json({"ok": True, "context": context})
                elif path == "/api/save-profile":
                    body = self.rfile.read(
                        int(self.headers.get("Content-Length", "0"))
                    )
                    data = json.loads(body.decode("utf-8") or "{}")
                    try:
                        if "name" in data:
                            dashboard.session.set_customer_name(data.get("name", ""))
                        context = dashboard.session.set_customer_context(data)
                    except ValueError as exc:
                        self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
                        return
                    self._send_json(
                        {
                            "ok": True,
                            "context": context,
                            "customers": dashboard.session.customers(),
                        }
                    )
                elif path == "/api/audio-source":
                    body = self.rfile.read(
                        int(self.headers.get("Content-Length", "0"))
                    )
                    data = json.loads(body.decode("utf-8") or "{}")
                    source = dashboard.session.set_audio_source(
                        data.get("source", "microphone")
                    )
                    self._send_json({"ok": True, "source": source})
                elif path == "/api/sync-crm":
                    body = self.rfile.read(
                        int(self.headers.get("Content-Length", "0"))
                    )
                    data = json.loads(body.decode("utf-8") or "{}")
                    meeting_id_value = data.get("meeting_id")
                    meeting_id = int(meeting_id_value) if meeting_id_value else None
                    self._send_json(
                        dashboard.session.sync_crm(
                            customer_name=data.get("customer"),
                            meeting_id=meeting_id,
                            connector_name=data.get("connector"),
                        )
                    )
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)

            def log_message(self, format: str, *args) -> None:
                return

            def _serve_static(self, filename: str, content_type: str) -> None:
                path = STATIC_DIR / filename
                data = path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _serve_events(self) -> None:
                client_queue = dashboard.events.subscribe()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                dashboard.events.publish("snapshot", dashboard.session.snapshot())

                try:
                    while True:
                        try:
                            event = client_queue.get(timeout=15)
                        except queue.Empty:
                            event = {"type": "ping", "payload": {}, "created_at": ""}
                        data = json.dumps(event, ensure_ascii=False)
                        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    dashboard.events.unsubscribe(client_queue)

            def _send_json(self, payload: dict) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _send_error_json(self, message: str, status: HTTPStatus) -> None:
                data = json.dumps({"ok": False, "error": message}, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _send_download_json(
                self,
                payload: dict,
                filename: str,
            ) -> None:
                data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"',
                )
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _send_csv(
                self,
                payload: str,
                filename: str = "sales-intel-crm.csv",
            ) -> None:
                data = payload.encode("utf-8-sig")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"',
                )
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        return Handler


def main() -> None:
    config = load_config()
    host = "127.0.0.1"
    port = 8765
    server = DashboardServer(host, port, config)
    url = f"http://{host}:{port}"
    print(f"Sales Intel Transcriber UI disponible en {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    server.serve_forever()


if __name__ == "__main__":
    main()



