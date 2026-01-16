"""
AI Pipeline Manager
Processes auction events with Ollama to generate tips and analysis.
Focuses on properties (imoveis) and vehicles (veiculos) only.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func, or_, and_

from database import (
    get_db, EventDB, EventAiTipDB, AiPipelineStateDB
)
from services.ollama_service import get_ollama_service, OllamaService


class AiPipelineManager:
    """
    Manages the AI analysis pipeline for auction events.

    Features:
    - Processes events ordered by ending date (soonest first)
    - Only processes Imoveis (tipo_id=1) and Veiculos (tipo_id=2)
    - Tracks progress in database
    - Can be started/stopped
    """

    def __init__(self):
        self.is_running = False
        self._stop_requested = False
        self._task: Optional[asyncio.Task] = None
        self.ollama: Optional[OllamaService] = None

    async def _init_pipeline_state(self):
        """Initialize pipeline state in database if not exists"""
        async with get_db() as db:
            query = select(AiPipelineStateDB).where(
                AiPipelineStateDB.pipeline_name == "ai_tips"
            )
            result = await db.session.execute(query)
            state = result.scalar_one_or_none()

            if not state:
                state = AiPipelineStateDB(
                    pipeline_name="ai_tips",
                    is_running=False,
                    total_processed=0,
                    total_failed=0,
                    total_pending=0
                )
                db.session.add(state)
                await db.session.commit()

    async def _update_state(self, **kwargs):
        """Update pipeline state in database"""
        async with get_db() as db:
            query = select(AiPipelineStateDB).where(
                AiPipelineStateDB.pipeline_name == "ai_tips"
            )
            result = await db.session.execute(query)
            state = result.scalar_one_or_none()

            if state:
                for key, value in kwargs.items():
                    if hasattr(state, key):
                        setattr(state, key, value)
                state.updated_at = datetime.utcnow()
                await db.session.commit()

    async def _get_next_event(self) -> Optional[dict]:
        """
        Get the next event to process.
        Priority:
        1. Events ending soonest (data_fim ASC)
        2. Only active events (not terminated/cancelled)
        3. Only Imoveis (tipo_id=1) or Veiculos (tipo_id=2)
        4. Not already processed or failed
        """
        async with get_db() as db:
            # Get events that don't have a tip yet or have a pending tip
            subquery = select(EventAiTipDB.reference).where(
                EventAiTipDB.status.in_(["completed", "processing"])
            )

            query = (
                select(EventDB)
                .where(
                    and_(
                        EventDB.tipo_id.in_([1, 2]),  # Only Imoveis and Veiculos
                        EventDB.terminado == False,
                        EventDB.cancelado == False,
                        EventDB.reference.not_in(subquery)
                    )
                )
                .order_by(EventDB.data_fim.asc())  # Ending soonest first
                .limit(1)
            )

            result = await db.session.execute(query)
            event = result.scalar_one_or_none()

            if event:
                return {
                    "reference": event.reference,
                    "titulo": event.titulo,
                    "tipo_id": event.tipo_id,
                    "tipo": event.tipo,
                    "subtipo": event.subtipo,
                    "tipologia": event.tipologia,
                    "distrito": event.distrito,
                    "concelho": event.concelho,
                    "freguesia": event.freguesia,
                    "valor_base": float(event.valor_base) if event.valor_base else 0,
                    "valor_abertura": float(event.valor_abertura) if event.valor_abertura else 0,
                    "lance_atual": float(event.lance_atual) if event.lance_atual else 0,
                    "area_total": event.area_total,
                    "area_privativa": event.area_privativa,
                    "matricula": event.matricula,
                    "descricao": event.descricao,
                    "observacoes": event.observacoes,
                    "data_fim": event.data_fim,
                }
            return None

    async def _create_or_get_tip(self, event: dict) -> EventAiTipDB:
        """Create or get existing tip entry for event"""
        async with get_db() as db:
            query = select(EventAiTipDB).where(
                EventAiTipDB.reference == event["reference"]
            )
            result = await db.session.execute(query)
            tip = result.scalar_one_or_none()

            if not tip:
                tip = EventAiTipDB(
                    reference=event["reference"],
                    event_titulo=event.get("titulo"),
                    event_tipo=event.get("tipo"),
                    event_subtipo=event.get("subtipo"),
                    event_distrito=event.get("distrito"),
                    event_valor_base=event.get("valor_base"),
                    status="pending"
                )
                db.session.add(tip)
                await db.session.commit()
                await db.session.refresh(tip)

            return tip

    async def _process_event(self, event: dict) -> bool:
        """
        Process a single event with AI analysis.
        Returns True if successful, False otherwise.
        """
        reference = event["reference"]
        print(f"[AI Pipeline] Processing event: {reference}")

        async with get_db() as db:
            # Get or create tip entry
            query = select(EventAiTipDB).where(EventAiTipDB.reference == reference)
            result = await db.session.execute(query)
            tip = result.scalar_one_or_none()

            if not tip:
                tip = EventAiTipDB(
                    reference=reference,
                    event_titulo=event.get("titulo"),
                    event_tipo=event.get("tipo"),
                    event_subtipo=event.get("subtipo"),
                    event_distrito=event.get("distrito"),
                    event_valor_base=event.get("valor_base"),
                    status="processing"
                )
                db.session.add(tip)
            else:
                tip.status = "processing"

            await db.session.commit()

            # Update pipeline state
            await self._update_state(
                current_reference=reference,
                current_event_titulo=event.get("titulo")
            )

            try:
                # Run AI analysis
                ai_result = await self.ollama.analyze_event(event)

                # Update tip with results
                tip.tip_summary = ai_result.summary
                tip.tip_analysis = ai_result.analysis
                tip.tip_pros = json.dumps(ai_result.pros)
                tip.tip_cons = json.dumps(ai_result.cons)
                tip.tip_recommendation = ai_result.recommendation
                tip.tip_confidence = ai_result.confidence
                tip.tokens_used = ai_result.tokens_used
                tip.processing_time_ms = ai_result.processing_time_ms
                tip.model_used = ai_result.model_used
                tip.status = "completed"
                tip.processed_at = datetime.utcnow()
                tip.error_message = None

                await db.session.commit()

                print(f"[AI Pipeline] Completed: {reference} ({ai_result.recommendation}, confidence: {ai_result.confidence:.2f})")
                return True

            except Exception as e:
                error_msg = str(e)[:500]
                print(f"[AI Pipeline] Failed: {reference} - {error_msg}")

                tip.status = "failed"
                tip.error_message = error_msg
                tip.updated_at = datetime.utcnow()
                await db.session.commit()

                return False

    async def _run_pipeline(self):
        """Main pipeline loop"""
        print("[AI Pipeline] Starting...")

        await self._init_pipeline_state()
        await self._update_state(
            is_running=True,
            last_started_at=datetime.utcnow(),
            last_error=None
        )

        self.ollama = get_ollama_service()

        # Check Ollama health
        health = await self.ollama.check_health()
        if not health.get("healthy"):
            error = health.get("error", "Unknown error")
            print(f"[AI Pipeline] Ollama not healthy: {error}")
            await self._update_state(
                is_running=False,
                last_error=f"Ollama not available: {error}"
            )
            self.is_running = False
            return

        processed = 0
        failed = 0

        while not self._stop_requested:
            try:
                # Get next event to process
                event = await self._get_next_event()

                if not event:
                    print("[AI Pipeline] No more events to process. Waiting 60s...")
                    await asyncio.sleep(60)
                    continue

                # Process the event
                success = await self._process_event(event)

                if success:
                    processed += 1
                else:
                    failed += 1

                # Update stats
                await self._update_state(
                    total_processed=processed,
                    total_failed=failed
                )

                # Small delay between requests to avoid overwhelming Ollama
                await asyncio.sleep(2)

            except asyncio.CancelledError:
                print("[AI Pipeline] Cancelled")
                break
            except Exception as e:
                print(f"[AI Pipeline] Error: {e}")
                await self._update_state(last_error=str(e)[:500])
                await asyncio.sleep(30)  # Wait before retrying

        # Cleanup
        await self._update_state(
            is_running=False,
            current_reference=None,
            current_event_titulo=None,
            last_completed_at=datetime.utcnow()
        )

        print(f"[AI Pipeline] Stopped. Processed: {processed}, Failed: {failed}")
        self.is_running = False

    async def start(self):
        """Start the AI pipeline"""
        if self.is_running:
            print("[AI Pipeline] Already running")
            return

        self.is_running = True
        self._stop_requested = False
        self._task = asyncio.create_task(self._run_pipeline())

    async def stop(self):
        """Stop the AI pipeline"""
        if not self.is_running:
            return

        print("[AI Pipeline] Stop requested...")
        self._stop_requested = True

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self._update_state(
            is_running=False,
            current_reference=None,
            current_event_titulo=None
        )

        self.is_running = False
        print("[AI Pipeline] Stopped")

    def get_status(self) -> dict:
        """Get current pipeline status"""
        return {
            "is_running": self.is_running,
            "stop_requested": self._stop_requested
        }


# Singleton instance
_ai_pipeline_manager: Optional[AiPipelineManager] = None


def get_ai_pipeline_manager() -> AiPipelineManager:
    """Get or create the AI pipeline manager singleton"""
    global _ai_pipeline_manager
    if _ai_pipeline_manager is None:
        _ai_pipeline_manager = AiPipelineManager()
    return _ai_pipeline_manager
