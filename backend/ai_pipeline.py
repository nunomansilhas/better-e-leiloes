"""
AI Pipeline Manager
Processes auction events with Ollama to generate tips and analysis.
Focuses on properties (imoveis) and vehicles (veiculos) only.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, or_, and_, update

from database import (
    get_db, EventDB, EventAiTipDB, AiPipelineStateDB
)
from services.ollama_service import get_ollama_service, OllamaService

# Configuration
PROCESSING_TIMEOUT_MINUTES = 10  # Tips stuck in 'processing' for longer than this will be reset


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

    async def _reset_stuck_processing_tips(self) -> int:
        """
        Reset tips that are stuck in 'processing' status.
        This can happen if the pipeline crashes or Ollama times out without proper cleanup.

        Returns:
            Number of tips reset
        """
        timeout_threshold = datetime.utcnow() - timedelta(minutes=PROCESSING_TIMEOUT_MINUTES)

        async with get_db() as db:
            # Find tips stuck in 'processing' for too long
            query = select(EventAiTipDB).where(
                and_(
                    EventAiTipDB.status == "processing",
                    or_(
                        EventAiTipDB.updated_at < timeout_threshold,
                        EventAiTipDB.updated_at.is_(None)
                    )
                )
            )
            result = await db.session.execute(query)
            stuck_tips = result.scalars().all()

            if stuck_tips:
                print(f"[AI Pipeline] Found {len(stuck_tips)} tips stuck in 'processing' status")
                for tip in stuck_tips:
                    print(f"[AI Pipeline] Resetting stuck tip: {tip.reference}")
                    tip.status = "pending"
                    tip.error_message = f"Reset from stuck 'processing' status at {datetime.utcnow().isoformat()}"
                    tip.updated_at = datetime.utcnow()

                await db.session.commit()
                print(f"[AI Pipeline] Reset {len(stuck_tips)} stuck tips to 'pending'")

            return len(stuck_tips)

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

            # IMPORTANT: Set updated_at when starting processing
            # This allows detection of stuck tips
            tip.updated_at = datetime.utcnow()
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
                tip.updated_at = datetime.utcnow()
                tip.error_message = None

                await db.session.commit()
                return True

            except Exception as e:
                error_msg = str(e)[:500]
                print(f"[AI Pipeline] Analysis error for {reference}: {error_msg}")

                tip.status = "failed"
                tip.error_message = error_msg
                tip.updated_at = datetime.utcnow()
                await db.session.commit()

                return False

    async def _run_pipeline(self):
        """Main pipeline loop"""
        print("[AI Pipeline] ====================================")
        print("[AI Pipeline] Starting AI Pipeline...")
        print("[AI Pipeline] ====================================")

        await self._init_pipeline_state()

        # Reset any stuck tips from previous runs
        stuck_count = await self._reset_stuck_processing_tips()
        if stuck_count > 0:
            print(f"[AI Pipeline] Recovered {stuck_count} stuck tips")

        await self._update_state(
            is_running=True,
            last_started_at=datetime.utcnow(),
            last_error=None
        )

        self.ollama = get_ollama_service()

        # Check Ollama health
        print("[AI Pipeline] Checking Ollama health...")
        health = await self.ollama.check_health()
        if not health.get("healthy"):
            error = health.get("error", "Unknown error")
            print(f"[AI Pipeline] ERROR: Ollama not healthy: {error}")
            print(f"[AI Pipeline] Tip: Make sure Ollama is running with 'ollama serve'")
            print(f"[AI Pipeline] Tip: Check if model is installed with 'ollama list'")
            await self._update_state(
                is_running=False,
                last_error=f"Ollama not available: {error}"
            )
            self.is_running = False
            return

        model_info = health.get("model", "unknown")
        model_available = health.get("model_available", False)
        print(f"[AI Pipeline] Ollama healthy - Model: {model_info}, Available: {model_available}")

        if not model_available:
            print(f"[AI Pipeline] WARNING: Model '{model_info}' not found!")
            print(f"[AI Pipeline] Tip: Install with 'ollama pull {model_info}'")
            await self._update_state(
                is_running=False,
                last_error=f"Model {model_info} not available. Run: ollama pull {model_info}"
            )
            self.is_running = False
            return

        processed = 0
        failed = 0

        print("[AI Pipeline] Entering main processing loop...")

        while not self._stop_requested:
            try:
                # Get next event to process
                event = await self._get_next_event()

                if not event:
                    print("[AI Pipeline] No more events to process. Waiting 60s...")
                    await asyncio.sleep(60)
                    continue

                ref = event.get("reference", "unknown")
                titulo = event.get("titulo", "")[:50]
                print(f"[AI Pipeline] Processing: {ref} - {titulo}...")

                # Process the event
                success = await self._process_event(event)

                if success:
                    processed += 1
                    print(f"[AI Pipeline] SUCCESS: {ref} (total processed: {processed})")
                else:
                    failed += 1
                    print(f"[AI Pipeline] FAILED: {ref} (total failed: {failed})")

                # Update stats
                await self._update_state(
                    total_processed=processed,
                    total_failed=failed
                )

                # Small delay between requests to avoid overwhelming Ollama
                await asyncio.sleep(2)

            except asyncio.CancelledError:
                print("[AI Pipeline] Received cancel signal")
                break
            except Exception as e:
                print(f"[AI Pipeline] ERROR in main loop: {e}")
                await self._update_state(last_error=str(e)[:500])
                await asyncio.sleep(30)  # Wait before retrying

        # Cleanup
        await self._update_state(
            is_running=False,
            current_reference=None,
            current_event_titulo=None,
            last_completed_at=datetime.utcnow()
        )

        print("[AI Pipeline] ====================================")
        print(f"[AI Pipeline] Pipeline stopped. Processed: {processed}, Failed: {failed}")
        print("[AI Pipeline] ====================================")
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
