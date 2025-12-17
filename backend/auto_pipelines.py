"""
Automatic Pipelines Management System
Manages scheduled automatic scrapers with persistent configuration
"""

import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict


@dataclass
class PipelineConfig:
    """Configuration for an automatic pipeline"""
    type: str
    name: str
    description: str
    enabled: bool
    interval_hours: float
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    runs_count: int = 0
    is_running: bool = False  # Track if currently executing


class AutoPipelinesManager:
    """Manages automatic pipelines with scheduling"""

    CONFIG_FILE = Path(__file__).parent / "auto_pipelines_config.json"

    DEFAULT_PIPELINES = {
        "full": PipelineConfig(
            type="full",
            name="Pipeline Automática Completa",
            description="Recolhe novos IDs, conteúdos e imagens automaticamente",
            enabled=False,
            interval_hours=8.0  # A cada 8 horas
        ),
        "prices": PipelineConfig(
            type="prices",
            name="Pipeline X-Critical - Preços (< 5 min)",
            description="Verifica alterações de preços a cada 5 SEGUNDOS para eventos terminando em menos de 5 minutos",
            enabled=False,
            interval_hours=5/3600  # A cada 5 segundos
        ),
        "prices_urgent": PipelineConfig(
            type="prices_urgent",
            name="Pipeline X-Urgent - Preços (< 1 hora)",
            description="Verifica alterações de preços a cada 1 MINUTO para eventos terminando em menos de 1 hora",
            enabled=False,
            interval_hours=1/60  # A cada 1 minuto
        ),
        "prices_soon": PipelineConfig(
            type="prices_soon",
            name="Pipeline X-Soon - Preços (< 24 horas)",
            description="Verifica alterações de preços a cada 10 MINUTOS para eventos terminando em menos de 24 horas",
            enabled=False,
            interval_hours=10/60  # A cada 10 minutos
        ),
        "info": PipelineConfig(
            type="info",
            name="Pipeline Y - Verificação de Informações",
            description="Verifica preços e datas de TODOS os eventos a cada 2 horas",
            enabled=False,
            interval_hours=2.0  # A cada 2 horas
        )
    }

    def __init__(self):
        self.pipelines: Dict[str, PipelineConfig] = {}
        self.job_ids: Dict[str, str] = {}  # pipeline_type -> scheduler_job_id

        # Cache for critical events (< 6 min) - refreshed every 5 minutes
        self._critical_events_cache = []
        self._cache_last_refresh = None
        self._cache_refresh_interval = timedelta(minutes=5)

        # Cache for urgent events (< 1.5 hours) - refreshed every 10 minutes
        self._urgent_events_cache = []
        self._urgent_cache_last_refresh = None
        self._urgent_cache_refresh_interval = timedelta(minutes=10)

        # Cache for soon events (< 25 hours) - refreshed every 30 minutes
        self._soon_events_cache = []
        self._soon_cache_last_refresh = None
        self._soon_cache_refresh_interval = timedelta(minutes=30)

        self._load_config()

    def _load_config(self):
        """Load configuration from file or create default"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)

                # Convert dict to PipelineConfig objects
                for key, value in data.items():
                    self.pipelines[key] = PipelineConfig(**value)

                print(f"📂 Auto-pipelines config loaded: {len(self.pipelines)} pipelines")
            except Exception as e:
                print(f"⚠️ Error loading auto-pipelines config: {e}")
                self._create_default_config()
        else:
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration"""
        self.pipelines = {k: v for k, v in self.DEFAULT_PIPELINES.items()}
        self._save_config()
        print(f"✨ Created default auto-pipelines config")

    def _save_config(self):
        """Save configuration to file"""
        try:
            data = {k: asdict(v) for k, v in self.pipelines.items()}

            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"💾 Auto-pipelines config saved")
        except Exception as e:
            print(f"⚠️ Error saving auto-pipelines config: {e}")

    async def refresh_critical_events_cache(self):
        """Refresh cache of events ending in < 6 minutes (called every 5 minutes)"""
        from database import get_db

        try:
            # Get all events from database
            async with get_db() as db:
                events, total = await db.list_events(limit=1000)

            if not events:
                self._critical_events_cache = []
                self._cache_last_refresh = datetime.now()
                return

            # Filter events ending in LESS THAN 6 MINUTES (360 seconds)
            # This catches events that just got reset to 5:00
            now = datetime.now()
            critical_events = []

            for event in events:
                if event.dataFim:
                    time_until_end = event.dataFim - now
                    seconds_until_end = time_until_end.total_seconds()

                    # Cache events ending in < 6 minutes (1-minute buffer)
                    if 0 < seconds_until_end <= 360:
                        critical_events.append(event)

            self._critical_events_cache = critical_events
            self._cache_last_refresh = datetime.now()

            if critical_events:
                print(f"🔄 Critical events cache refreshed: {len(critical_events)} events (< 6 min)")

        except Exception as e:
            print(f"⚠️ Error refreshing critical events cache: {e}")

    async def refresh_urgent_events_cache(self):
        """Refresh cache of events ending in < 1.5 hours (called every 10 minutes)"""
        from database import get_db

        try:
            async with get_db() as db:
                events, total = await db.list_events(limit=1000)

            if not events:
                self._urgent_events_cache = []
                self._urgent_cache_last_refresh = datetime.now()
                return

            # Filter events ending in LESS THAN 1.5 HOURS (5400 seconds)
            now = datetime.now()
            urgent_events = []

            for event in events:
                if event.dataFim:
                    time_until_end = event.dataFim - now
                    seconds_until_end = time_until_end.total_seconds()

                    # Cache events ending in < 1.5 hours (30-min buffer)
                    if 0 < seconds_until_end <= 5400:
                        urgent_events.append(event)

            self._urgent_events_cache = urgent_events
            self._urgent_cache_last_refresh = datetime.now()

            if urgent_events:
                print(f"🟠 Urgent events cache refreshed: {len(urgent_events)} events (< 1.5h)")

        except Exception as e:
            print(f"⚠️ Error refreshing urgent events cache: {e}")

    async def refresh_soon_events_cache(self):
        """Refresh cache of events ending in < 25 hours (called every 30 minutes)"""
        from database import get_db

        try:
            async with get_db() as db:
                events, total = await db.list_events(limit=1000)

            if not events:
                self._soon_events_cache = []
                self._soon_cache_last_refresh = datetime.now()
                return

            # Filter events ending in LESS THAN 25 HOURS (90000 seconds)
            now = datetime.now()
            soon_events = []

            for event in events:
                if event.dataFim:
                    time_until_end = event.dataFim - now
                    seconds_until_end = time_until_end.total_seconds()

                    # Cache events ending in < 25 hours (1-hour buffer)
                    if 0 < seconds_until_end <= 90000:
                        soon_events.append(event)

            self._soon_events_cache = soon_events
            self._soon_cache_last_refresh = datetime.now()

            if soon_events:
                print(f"🟡 Soon events cache refreshed: {len(soon_events)} events (< 25h)")

        except Exception as e:
            print(f"⚠️ Error refreshing soon events cache: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get status of all pipelines"""
        return {
            "pipelines": {k: asdict(v) for k, v in self.pipelines.items()},
            "total": len(self.pipelines),
            "enabled": sum(1 for p in self.pipelines.values() if p.enabled)
        }

    async def toggle_pipeline(self, pipeline_type: str, enabled: bool, scheduler=None) -> Dict[str, Any]:
        """Enable or disable a pipeline"""
        if pipeline_type not in self.pipelines:
            raise ValueError(f"Pipeline type '{pipeline_type}' not found")

        pipeline = self.pipelines[pipeline_type]
        was_enabled = pipeline.enabled
        pipeline.enabled = enabled

        # Calculate next run if enabling
        if enabled:
            now = datetime.now()
            next_run = now + timedelta(hours=pipeline.interval_hours)
            pipeline.next_run = next_run.strftime("%Y-%m-%d %H:%M:%S")

            # Schedule job if scheduler provided
            if scheduler and pipeline_type not in self.job_ids:
                await self._schedule_pipeline(pipeline_type, scheduler)
        else:
            pipeline.next_run = None

            # Remove scheduled job if exists
            if scheduler and pipeline_type in self.job_ids:
                await self._unschedule_pipeline(pipeline_type, scheduler)

        self._save_config()

        status = "ativada" if enabled else "desativada"
        message = f"Pipeline {pipeline.name} {status}"

        if enabled:
            message += f" • Próxima execução: {pipeline.next_run}"

        return {
            "success": True,
            "message": message,
            "pipeline": asdict(pipeline),
            "next_run": pipeline.next_run if enabled else None,
            "was_enabled": was_enabled
        }

    async def _schedule_pipeline(self, pipeline_type: str, scheduler):
        """Schedule a pipeline to run automatically"""
        pipeline = self.pipelines[pipeline_type]

        # Define the job function
        job_id = f"auto_pipeline_{pipeline_type}"

        # Import here to avoid circular imports
        from apscheduler.triggers.interval import IntervalTrigger

        # Create trigger for interval
        trigger = IntervalTrigger(hours=pipeline.interval_hours)

        # Get the task function based on type
        task_func = self._get_pipeline_task(pipeline_type)

        # Add job to scheduler
        scheduler.add_job(
            task_func,
            trigger=trigger,
            id=job_id,
            name=pipeline.name,
            replace_existing=True
        )

        self.job_ids[pipeline_type] = job_id
        print(f"📅 Scheduled {pipeline.name} every {pipeline.interval_hours}h")

    async def _unschedule_pipeline(self, pipeline_type: str, scheduler):
        """Remove pipeline from scheduler"""
        if pipeline_type in self.job_ids:
            job_id = self.job_ids[pipeline_type]
            try:
                scheduler.remove_job(job_id)
                print(f"🗑️ Unscheduled pipeline: {job_id}")
            except Exception as e:
                print(f"⚠️ Error unscheduling {job_id}: {e}")
            finally:
                del self.job_ids[pipeline_type]

    def _get_pipeline_task(self, pipeline_type: str) -> Callable:
        """Get the async task function for a pipeline type"""

        async def run_full_pipeline():
            """Pipeline Automática: IDs + Content + Images"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager

            # Mark as running
            self.pipelines['full'].is_running = True
            self._save_config()

            print(f"🤖 Running Full Auto-Pipeline...")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                # Stage 1: Get new IDs
                ids = await scraper.scrape_ids_only(tipo=None, max_pages=5)
                print(f"  📊 Stage 1: {len(ids)} IDs found")

                # Save to DB
                async with get_db() as db:
                    for item in ids:
                        # Check if already exists
                        existing = await db.get_event(item['reference'])
                        if not existing:
                            from models import EventData, EventDetails, ValoresLeilao

                            event = EventData(
                                reference=item['reference'],
                                tipoEvento=item.get('tipo', 'imovel'),
                                valores=item.get('valores', ValoresLeilao()),
                                detalhes=EventDetails(
                                    tipo=item.get('tipo', 'N/A'),
                                    subtipo='N/A'
                                ),
                                descricao=None,
                                observacoes=None,
                                imagens=[]
                            )

                            await db.save_event(event)
                            await cache_manager.set(event.reference, event)

                # Stage 2 & 3: Get content and images for new events
                new_refs = [item['reference'] for item in ids[:10]]  # Limit to 10 per run
                if new_refs:
                    print(f"  📋 Stage 2: Scraping {len(new_refs)} events...")
                    events = await scraper.scrape_details_by_ids(new_refs)

                    print(f"  🖼️ Stage 3: Scraping images for {len(new_refs)} events...")
                    images_map = await scraper.scrape_images_by_ids(new_refs)

                    # Update DB with images
                    async with get_db() as db:
                        for ref, images in images_map.items():
                            event = await db.get_event(ref)
                            if event:
                                event.imagens = images
                                await db.save_event(event)
                                await cache_manager.set(ref, event)

                print(f"✅ Full Auto-Pipeline completed: {len(ids)} total, {len(new_refs)} processed")

                # Update last run and next run
                pipeline = self.pipelines['full']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                # Calculate next run time
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()

            finally:
                await scraper.close()
                await cache_manager.close()
                # Mark as not running
                self.pipelines['full'].is_running = False
                self._save_config()

        async def run_prices_pipeline():
            """Pipeline X-Critical: Price verification every 5 SECONDS for events < 5 minutes
            OTIMIZADO: Usa SELECT direto da BD + scrape_volatile_only + UPDATE parcial
            """
            from scraper import EventScraper
            from database import get_db

            # Mark as running
            self.pipelines['prices'].is_running = True

            try:
                # 1. SELECT: Query otimizada - eventos que terminam em < 5 min (300s)
                async with get_db() as db:
                    events = await db.get_events_ending_within(300)

                if not events:
                    print(f"🔴 Pipeline X-Critical: No events ending in < 5 min")
                    # Update pipeline stats
                    pipeline = self.pipelines['prices']
                    now = datetime.now()
                    pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                    pipeline.runs_count += 1
                    next_run_time = now + timedelta(hours=pipeline.interval_hours)
                    pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    return

                print(f"🔴 Pipeline X-Critical: {len(events)} events (< 5 min)")

                # 2. SCRAPE: Scrape otimizado - só valores voláteis
                scraper = EventScraper()
                try:
                    refs = [e.reference for e in events]
                    volatile_data = await scraper.scrape_volatile_only(refs)
                finally:
                    await scraper.close()

                # 3. UPDATE: Compara e atualiza apenas campos alterados
                updates = []
                updated_count = 0
                time_extended_count = 0
                events_to_deactivate = []  # Eventos terminados/vendidos
                ended_updates = []  # Updates para eventos que vão ser desativados

                # Cria mapa de eventos antigos para comparação rápida
                old_events_map = {e.reference: e for e in events}

                for new_data in volatile_data:
                    ref = new_data.get("reference")
                    if not ref:
                        continue

                    old_event = old_events_map.get(ref)

                    # Se scrape falhou (evento removido/vendido), marcar para desativar
                    if "error" in new_data:
                        events_to_deactivate.append(ref)
                        print(f"  🔒 {ref}: Marcando inativo (scrape falhou)")
                        continue

                    # Se evento terminou ou foi cancelado (detetado pelo scraper)
                    if new_data.get("ended"):
                        reason = new_data.get("reason", "desconhecido")
                        new_price = new_data.get("lance_atual")
                        new_end = new_data.get("data_fim")

                        # Prepara update para valores finais antes de desativar
                        update_data = {"reference": ref}

                        # Atualiza lance_atual se obtivemos um valor válido
                        if new_price is not None and new_price > 0:
                            old_price = old_event.valores.lanceAtual if old_event else 0
                            update_data["lance_atual"] = new_price
                            print(f"  🔒 {ref}: {reason} | lance: {old_price}€ → {new_price}€")
                        else:
                            print(f"  🔒 {ref}: {reason}")

                        # Atualiza data_fim se obtivemos uma (só para "terminado")
                        if new_end is not None:
                            update_data["data_fim"] = new_end

                        if len(update_data) > 1:  # Tem mais que só reference
                            ended_updates.append(update_data)

                        events_to_deactivate.append(ref)
                        continue

                    if not old_event:
                        continue

                    old_price = old_event.valores.lanceAtual or 0
                    new_price = new_data.get("lance_atual")
                    old_end = old_event.dataFim
                    new_end = new_data.get("data_fim")

                    # Verifica se evento já terminou (data_fim no passado)
                    now = datetime.now()
                    if new_end and new_end < now:
                        events_to_deactivate.append(ref)
                        print(f"  🔒 {ref}: Marcando inativo (data_fim expirada)")
                        continue

                    # VALIDAÇÃO: Só atualiza lance_atual se valor válido
                    # Não trocar de valor > 0 para 0 (bug de scraping)
                    price_valid = (
                        new_price is not None and
                        (new_price > 0 or old_price == 0)  # Só aceita 0 se já era 0
                    )
                    price_changed = price_valid and old_price != new_price

                    time_extended = (new_end and old_end and new_end > old_end)

                    if price_changed or time_extended:
                        # Calcula tempo restante
                        seconds_left = (old_end - now).total_seconds() if old_end else 0
                        minutes = int(seconds_left / 60)
                        secs = int(seconds_left % 60)

                        msg_parts = []
                        if price_changed:
                            msg_parts.append(f"{old_price}€ → {new_price}€")
                        if time_extended:
                            time_diff = (new_end - old_end).total_seconds()
                            msg_parts.append(f"timer reset (+{int(time_diff/60)}min)")
                            time_extended_count += 1

                        print(f"  💰 {ref}: {' | '.join(msg_parts)} ({minutes}m{secs}s)")

                        updates.append({
                            "reference": ref,
                            "lance_atual": new_price if price_changed else None,
                            "data_fim": new_end if time_extended else None
                        })
                        updated_count += 1

                # Batch UPDATE na BD
                async with get_db() as db:
                    # Atualiza valores finais de eventos que vão ser desativados
                    if ended_updates:
                        await db.bulk_update_volatile_fields(ended_updates)

                    # Atualiza eventos ativos
                    if updates:
                        await db.bulk_update_volatile_fields(updates)

                    # Marca eventos como inativos
                    if events_to_deactivate:
                        deactivated = await db.bulk_mark_events_inactive(events_to_deactivate)
                        print(f"  🔒 {deactivated} eventos marcados como inativos")

                if updated_count > 0 or events_to_deactivate:
                    print(f"  ✅ {updated_count} updated, {time_extended_count} timer resets, {len(events_to_deactivate)} inativos")

                # Update pipeline stats
                pipeline = self.pipelines['prices']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()

            finally:
                self.pipelines['prices'].is_running = False

        async def run_info_pipeline():
            """Pipeline Y: Quick info verification and update for ALL events"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager

            # Mark as running
            self.pipelines['info'].is_running = True
            self._save_config()

            print(f"🔄 Pipeline Y-Info: Starting verification...")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                # Get all events from database
                async with get_db() as db:
                    events, total = await db.list_events(limit=1000)

                if not events:
                    print(f"  ℹ️ Pipeline Y-Info: No events in database, skipping")
                    # Update pipeline stats even when no events
                    pipeline = self.pipelines['info']
                    now = datetime.now()
                    pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                    pipeline.runs_count += 1
                    next_run_time = now + timedelta(hours=pipeline.interval_hours)
                    pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    return

                # Check ALL events (not sampling)
                print(f"  📊 Checking {len(events)} events...")

                updated_count = 0
                errors_count = 0

                for event in events:
                    try:
                        # Re-scrape event details
                        new_events = await scraper.scrape_details_by_ids([event.reference])

                        if new_events and len(new_events) > 0:
                            new_event = new_events[0]
                            changed_fields = []

                            # Compare valores (prices) - ONLY
                            if event.valores.valorBase != new_event.valores.valorBase:
                                changed_fields.append(f"valorBase: {event.valores.valorBase}€ → {new_event.valores.valorBase}€")
                            if event.valores.valorAbertura != new_event.valores.valorAbertura:
                                changed_fields.append(f"valorAbertura: {event.valores.valorAbertura}€ → {new_event.valores.valorAbertura}€")
                            if event.valores.valorMinimo != new_event.valores.valorMinimo:
                                changed_fields.append(f"valorMinimo: {event.valores.valorMinimo}€ → {new_event.valores.valorMinimo}€")
                            if event.valores.lanceAtual != new_event.valores.lanceAtual:
                                changed_fields.append(f"lanceAtual: {event.valores.lanceAtual}€ → {new_event.valores.lanceAtual}€")

                            # Compare dates - ONLY
                            if event.dataInicio != new_event.dataInicio:
                                changed_fields.append(f"dataInicio changed")
                            if event.dataFim != new_event.dataFim:
                                changed_fields.append(f"dataFim changed")

                            # If changes detected, update event
                            if changed_fields:
                                print(f"    🔄 {event.reference}: {len(changed_fields)} changes detected")
                                for field in changed_fields:  # Show all changes
                                    print(f"       • {field}")

                                # Update event with new data
                                async with get_db() as db:
                                    await db.save_event(new_event)
                                    await cache_manager.set(event.reference, new_event)

                                updated_count += 1
                            # Silent when no changes (avoid spam)

                    except Exception as e:
                        print(f"    ⚠️ Error checking {event.reference}: {e}")
                        errors_count += 1

                print(f"  ✅ Info verification complete: {updated_count} events updated, {errors_count} errors")

                # Update pipeline stats and next run
                pipeline = self.pipelines['info']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                # Calculate next run time
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()

            finally:
                await scraper.close()
                await cache_manager.close()
                # Mark as not running
                self.pipelines['info'].is_running = False
                self._save_config()

        async def run_prices_urgent_pipeline():
            """Pipeline X-Urgent: Price verification every 1 MINUTE for events < 1 hour
            OTIMIZADO: Usa SELECT direto da BD + scrape_volatile_only + UPDATE parcial
            """
            from scraper import EventScraper
            from database import get_db

            # Mark as running
            self.pipelines['prices_urgent'].is_running = True

            try:
                # 1. SELECT: Query otimizada - eventos que terminam em < 1h (3600s)
                async with get_db() as db:
                    events = await db.get_events_ending_within(3600)

                if not events:
                    print(f"🟠 Pipeline X-Urgent: No events ending in < 1h")
                    pipeline = self.pipelines['prices_urgent']
                    now = datetime.now()
                    pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                    pipeline.runs_count += 1
                    next_run_time = now + timedelta(hours=pipeline.interval_hours)
                    pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    return

                print(f"🟠 Pipeline X-Urgent: {len(events)} events (< 1h)")

                # 2. SCRAPE: Scrape otimizado - só valores voláteis
                scraper = EventScraper()
                try:
                    refs = [e.reference for e in events]
                    volatile_data = await scraper.scrape_volatile_only(refs)
                finally:
                    await scraper.close()

                # 3. UPDATE: Compara e atualiza apenas campos alterados
                updates = []
                updated_count = 0
                time_extended_count = 0
                old_events_map = {e.reference: e for e in events}

                for new_data in volatile_data:
                    ref = new_data.get("reference")
                    if not ref or "error" in new_data:
                        continue

                    old_event = old_events_map.get(ref)
                    if not old_event:
                        continue

                    old_price = old_event.valores.lanceAtual or 0
                    new_price = new_data.get("lance_atual") or 0
                    old_end = old_event.dataFim
                    new_end = new_data.get("data_fim")

                    price_changed = old_price != new_price
                    time_extended = (new_end and old_end and new_end > old_end)

                    if price_changed or time_extended:
                        now = datetime.now()
                        seconds_left = (old_end - now).total_seconds() if old_end else 0
                        minutes = int(seconds_left / 60)

                        msg_parts = []
                        if price_changed:
                            msg_parts.append(f"{old_price}€ → {new_price}€")
                        if time_extended:
                            time_diff = (new_end - old_end).total_seconds()
                            msg_parts.append(f"timer reset (+{int(time_diff/60)}min)")
                            time_extended_count += 1

                        print(f"  🟠 {ref}: {' | '.join(msg_parts)} ({minutes}min)")

                        updates.append({
                            "reference": ref,
                            "lance_atual": new_price if price_changed else None,
                            "data_fim": new_end if time_extended else None
                        })
                        updated_count += 1

                if updates:
                    async with get_db() as db:
                        await db.bulk_update_volatile_fields(updates)
                    print(f"  ✅ {updated_count} updated, {time_extended_count} timer resets")

                pipeline = self.pipelines['prices_urgent']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()

            finally:
                self.pipelines['prices_urgent'].is_running = False

        async def run_prices_soon_pipeline():
            """Pipeline X-Soon: Price verification every 10 MINUTES for events < 24 hours
            OTIMIZADO: Usa SELECT direto da BD + scrape_volatile_only + UPDATE parcial
            """
            from scraper import EventScraper
            from database import get_db

            # Mark as running
            self.pipelines['prices_soon'].is_running = True

            try:
                # 1. SELECT: Query otimizada - eventos que terminam em < 24h (86400s)
                async with get_db() as db:
                    events = await db.get_events_ending_within(86400)

                if not events:
                    print(f"🟡 Pipeline X-Soon: No events ending in < 24h")
                    pipeline = self.pipelines['prices_soon']
                    now = datetime.now()
                    pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                    pipeline.runs_count += 1
                    next_run_time = now + timedelta(hours=pipeline.interval_hours)
                    pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    return

                print(f"🟡 Pipeline X-Soon: {len(events)} events (< 24h)")

                # 2. SCRAPE: Scrape otimizado - só valores voláteis
                scraper = EventScraper()
                try:
                    refs = [e.reference for e in events]
                    volatile_data = await scraper.scrape_volatile_only(refs)
                finally:
                    await scraper.close()

                # 3. UPDATE: Compara e atualiza apenas campos alterados
                updates = []
                updated_count = 0
                time_extended_count = 0
                old_events_map = {e.reference: e for e in events}

                for new_data in volatile_data:
                    ref = new_data.get("reference")
                    if not ref or "error" in new_data:
                        continue

                    old_event = old_events_map.get(ref)
                    if not old_event:
                        continue

                    old_price = old_event.valores.lanceAtual or 0
                    new_price = new_data.get("lance_atual") or 0
                    old_end = old_event.dataFim
                    new_end = new_data.get("data_fim")

                    price_changed = old_price != new_price
                    time_extended = (new_end and old_end and new_end > old_end)

                    if price_changed or time_extended:
                        now = datetime.now()
                        seconds_left = (old_end - now).total_seconds() if old_end else 0
                        hours = int(seconds_left / 3600)
                        minutes = int((seconds_left % 3600) / 60)

                        msg_parts = []
                        if price_changed:
                            msg_parts.append(f"{old_price}€ → {new_price}€")
                        if time_extended:
                            time_diff = (new_end - old_end).total_seconds()
                            msg_parts.append(f"timer reset (+{int(time_diff/60)}min)")
                            time_extended_count += 1

                        print(f"  🟡 {ref}: {' | '.join(msg_parts)} ({hours}h{minutes}m)")

                        updates.append({
                            "reference": ref,
                            "lance_atual": new_price if price_changed else None,
                            "data_fim": new_end if time_extended else None
                        })
                        updated_count += 1

                if updates:
                    async with get_db() as db:
                        await db.bulk_update_volatile_fields(updates)
                    print(f"  ✅ {updated_count} updated, {time_extended_count} timer resets")

                pipeline = self.pipelines['prices_soon']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()

            finally:
                self.pipelines['prices_soon'].is_running = False

        # Return the appropriate function
        tasks = {
            "full": run_full_pipeline,
            "prices": run_prices_pipeline,
            "prices_urgent": run_prices_urgent_pipeline,
            "prices_soon": run_prices_soon_pipeline,
            "info": run_info_pipeline
        }

        return tasks.get(pipeline_type, lambda: None)


# Global singleton
_auto_pipelines_manager = None


def get_auto_pipelines_manager() -> AutoPipelinesManager:
    """Get or create global auto pipelines manager instance"""
    global _auto_pipelines_manager
    if _auto_pipelines_manager is None:
        _auto_pipelines_manager = AutoPipelinesManager()
    return _auto_pipelines_manager
