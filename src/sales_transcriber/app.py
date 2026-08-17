"""app.py: Application orchestration for the transcription MVP."""

from __future__ import annotations

import queue
import threading
import time


from sales_transcriber.audio.capture import (
    MicrophoneError,
    MicrophoneRecorder,
)


from sales_transcriber.config import (
    AppConfig,
)


from sales_transcriber.console import (
    ConsoleTranscriptWriter,
)


from sales_transcriber.stt.factory import (
    create_transcriber,
)


from sales_transcriber.stt.openai_client import (
    TranscriptionServiceError,
)


from sales_transcriber.transcription_buffer import (
    TranscriptionBuffer,
)


from sales_transcriber.intelligence.llm_analyzer import (
    LLMConversationAnalyzer,
)


from sales_transcriber.intelligence.recommendation_engine import (
    RecommendationEngine,
)


from sales_transcriber.intelligence.conversation_state import (
    ConversationState,
)


from sales_transcriber.intelligence.state_manager import (
    ConversationStateManager,
)



class TranscriptionApp:
    """Wire together audio capture, transcription and intelligence."""


    def __init__(
        self,
        config: AppConfig,
    ) -> None:


        self._config = config


        self._recorder = MicrophoneRecorder(
            config.audio
        )


        self._transcriber = create_transcriber(
            config.transcription
        )


        self._console = ConsoleTranscriptWriter()


        self._audio_queue = queue.Queue()


        self._stop_event = threading.Event()



        #
        # Intelligence
        #

        self._buffer = TranscriptionBuffer()


        self._analyzer = LLMConversationAnalyzer(
            provider=config.llm.provider,
            model=config.llm.model,
            api_key=config.llm.api_key,
            ollama_model=config.llm.ollama_model,
        )


        self._recommendation_engine = (
            RecommendationEngine()
        )



        #
        # Conversation memory
        #
        # Se conserva para acumular contexto entre
        # segmentos (pain points, objeciones, etc).
        # El score y el riesgo por segmento ahora
        # vienen directamente del LLM (insight).
        #

        self._conversation_state = ConversationState()


        self._state_manager = (
            ConversationStateManager()
        )



        #
        # Avoid repeated recommendations
        #

        self._last_recommendation: str | None = None





    def _update_intelligence(
        self,
        insight,
    ) -> None:
        """
        Update conversation memory using the latest insight.

        El opportunity_score y risk_level ya no se calculan aquí:
        vienen directamente del LLM en `insight`.
        """


        self._state_manager.update(
            self._conversation_state,
            insight,
        )





    def _print_analysis(
        self,
        title: str,
        recommendation: str | None,
        coach: str | None,
        insight,
    ) -> None:


        print(
            "\n===================="
        )


        print(title)



        print(
            f"Intent: {insight.intent}"
        )


        print(
            f"Sentiment: {insight.sentiment}"
        )


        print(
            f"Objections: {insight.objections}"
        )


        print(
            f"Primary Objection: "
            f"{insight.primary_objection}"
        )


        print(
            f"Buying Signal: "
            f"{insight.buying_signal}"
        )


        print(
            f"Next Step: "
            f"{insight.next_step}"
        )


        print(
            f"Sales Stage: "
            f"{insight.sales_stage}"
        )


        print(
            f"Opportunity Score: "
            f"{insight.opportunity_score}/100"
        )


        print(
            f"Risk Level: "
            f"{insight.risk_level}"
        )


        if insight.pain_points:

            print(
                f"Pain Points: {insight.pain_points}"
            )


        if insight.business_goals:

            print(
                f"Business Goals: {insight.business_goals}"
            )


        if insight.competitors:

            print(
                f"Competitors: {insight.competitors}"
            )


        if insight.budget_status:

            print(
                f"Budget Status: {insight.budget_status}"
            )


        if insight.timeline:

            print(
                f"Timeline: {insight.timeline}"
            )


        if insight.decision_maker:

            print(
                f"Decision Maker: {insight.decision_maker}"
            )


        print(
            f"Summary: "
            f"{insight.summary}"
        )



        if (
            recommendation
            and recommendation
            != self._last_recommendation
        ):


            print(
                f"Recommendation: "
                f"{recommendation}"
            )


            self._last_recommendation = (
                recommendation
            )



        if coach:


            print(
                "\n[COACH]"
            )


            print(
                coach
            )



        print(
            "====================\n"
        )







    def _run_analysis(
        self,
    ) -> None:


        if self._buffer.size() < 5:

            return



        transcript = (
            self._buffer.get_text()
        )


        try:
            insight = (
                self._analyzer.analyze(
                    transcript
                )
            )
        except Exception as exc:
            print(
                f"[LLM ERROR] {exc}"
            )
            return


        #
        # Update intelligence
        #

        self._update_intelligence(
            insight
        )



        recommendation = (
            self._recommendation_engine.generate(
                insight,
                self._conversation_state,
            )
        )



        coach = (
            "\n".join(insight.coach_advice)
            if insight.coach_advice
            else None
        )



        self._print_analysis(
            title="[ANALYZER]",
            recommendation=recommendation,
            coach=coach,
            insight=insight,
        )


        self._buffer.clear()







    def _transcription_worker(
        self,
    ) -> None:


        while not self._stop_event.is_set():


            try:

                chunk = (
                    self._audio_queue.get(
                        timeout=0.5
                    )
                )


            except queue.Empty:

                continue



            try:


                start = time.time()



                transcript = (
                    self._transcriber.transcribe(
                        chunk,
                        self._console.write_delta,
                    )
                )



                elapsed = (
                    time.time()
                    -
                    start
                )



                print(
                    f"[DEBUG] Tiempo Whisper: "
                    f"{elapsed:.2f}s"
                )



                self._console.end_segment()



                if transcript:


                    self._buffer.add(
                        transcript
                    )


                    print(
                        f"[DEBUG BUFFER] "
                        f"{self._buffer.size()} "
                        f"mensajes"
                    )



                    if self._buffer.size() >= 5:

                        self._run_analysis()



            except TranscriptionServiceError as exc:


                self._console.error(
                    str(exc)
                )



            finally:

                self._audio_queue.task_done()







    def run(
        self,
    ) -> None:


        self._console.start()



        worker = threading.Thread(
            target=self._transcription_worker,
            daemon=True,
        )


        worker.start()



        try:


            for chunk in self._recorder.chunks():


                if (
                    chunk.rms
                    <
                    self._config.audio.min_rms
                ):


                    if self._config.transcription.debug:


                        print(
                            "[Audio] Silencio omitido. "
                            f"RMS={chunk.rms:.1f}"
                        )


                    continue



                self._audio_queue.put(
                    chunk
                )



                if self._config.transcription.debug:


                    print(
                        "[DEBUG] Audio en cola: "
                        f"{self._audio_queue.qsize()}"
                    )





        except KeyboardInterrupt:


            self._stop_event.set()



            if self._buffer.size() > 0:


                transcript = (
                    self._buffer.get_text()
                )


                try:
                    insight = (
                        self._analyzer.analyze(
                            transcript
                        )
                    )
                except KeyboardInterrupt:
                    print(
                        "\n[INFO] Análisis final "
                        "cancelado por el usuario."
                    )

                    self._console.end_segment()

                    print(
                        "\nTranscripción detenida "
                        "por el usuario."
                    )

                    return
                except Exception as exc:
                    print(
                        f"[LLM ERROR] {exc}"
                    )
                    self._console.end_segment()

                    print(
                        "\nTranscripción detenida "
                        "por el usuario."
                    )

                    return

                self._update_intelligence(
                    insight
                )



                recommendation = (
                    self._recommendation_engine.generate(
                        insight,
                        self._conversation_state,
                    )
                )



                coach = (
                    "\n".join(insight.coach_advice)
                    if insight.coach_advice
                    else None
                )



                self._print_analysis(
                    title="[ANALYZER FINAL]",
                    recommendation=recommendation,
                    coach=coach,
                    insight=insight,
                )



            self._console.end_segment()



            print(
                "\nTranscripción detenida "
                "por el usuario."
            )





        except MicrophoneError as exc:


            self._stop_event.set()


            self._console.error(
                str(exc)
            )
