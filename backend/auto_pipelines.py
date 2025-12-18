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
        self._scheduler = None  # Store scheduler reference for rescheduling

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

        # Store scheduler reference for rescheduling after job completion
        self._scheduler = scheduler

        # Define the job function
        job_id = f"auto_pipeline_{pipeline_type}"

        # Import here to avoid circular imports
        from apscheduler.triggers.date import DateTrigger

        # Schedule to run immediately (or in 1 second to avoid race conditions)
        from datetime import datetime, timedelta
        run_time = datetime.now() + timedelta(seconds=1)
        trigger = DateTrigger(run_date=run_time)

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

    def _reschedule_pipeline(self, pipeline_type: str):
        """Reschedule a pipeline to run after the configured interval"""
        if not self._scheduler or pipeline_type not in self.job_ids:
            return

        pipeline = self.pipelines.get(pipeline_type)
        if not pipeline or not pipeline.enabled:
            return

        from apscheduler.triggers.date import DateTrigger
        from datetime import datetime, timedelta

        job_id = self.job_ids[pipeline_type]
        task_func = self._get_pipeline_task(pipeline_type)

        # Schedule next run after interval_hours from NOW (after completion)
        next_run = datetime.now() + timedelta(hours=pipeline.interval_hours)

        try:
            # Remove old job and add new one with updated time
            try:
                self._scheduler.remove_job(job_id)
            except:
                pass

            self._scheduler.add_job(
                task_func,
                trigger=DateTrigger(run_date=next_run),
                id=job_id,
                name=pipeline.name,
                replace_existing=True
            )
            print(f"⏰ Next run of {pipeline.name} scheduled for {next_run.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"⚠️ Error rescheduling {pipeline.name}: {e}")

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
                # Reschedule next run after completion
                self._reschedule_pipeline('full')

        async def run_prices_pipeline():
            """Pipeline X: Price verification every 5 SECONDS for events < 5 minutes"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager

            # Mark as running
            self.pipelines['prices'].is_running = True

            # Check if cache needs refresh (every 5 minutes)
            now = datetime.now()
            needs_refresh = (
                self._cache_last_refresh is None or
                now - self._cache_last_refresh >= self._cache_refresh_interval
            )

            if needs_refresh:
                await self.refresh_critical_events_cache()

            # Use cached events list (no database query!)
            if not self._critical_events_cache:
                print(f"🔴 Pipeline X-Critical: No critical events in cache, skipping")
                # Update pipeline stats even when no events
                pipeline = self.pipelines['prices']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()
                return

            print(f"🔴 Pipeline X-Critical: Checking {len(self._critical_events_cache)} events (< 6 min cache)")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                # Process cached critical events
                critical_events = []
                now = datetime.now()

                for event in self._critical_events_cache:
                    if event.dataFim:
                        time_until_end = event.dataFim - now
                        seconds_until_end = time_until_end.total_seconds()

                        # Only scrape events < 5 minutes (300 seconds)
                        if 0 < seconds_until_end <= 300:
                            critical_events.append({
                                'event': event,
                                'seconds_until_end': seconds_until_end
                            })

                # Sort by urgency (most urgent first)
                critical_events.sort(key=lambda x: x['seconds_until_end'])

                if not critical_events:
                    print(f"  🔴 No events ending in < 5 min right now")
                    return

                print(f"  🚨 Scraping {len(critical_events)} events (< 5 min)")

                updated_count = 0
                time_extended_count = 0

                for item in critical_events:
                    event = item['event']
                    seconds = item['seconds_until_end']
                    minutes = int(seconds / 60)
                    secs = int(seconds % 60)

                    try:
                        # LIGHTWEIGHT: Only scrape price + end time (fast)
                        volatile_data = await scraper.scrape_volatile_by_ids([event.reference])

                        if volatile_data and len(volatile_data) > 0:
                            data = volatile_data[0]
                            old_price = event.valores.lanceAtual or 0
                            new_price = data['lanceAtual'] or 0
                            old_end = event.dataFim
                            new_end = data['dataFim']

                            # Check if price or time changed
                            price_changed = old_price != new_price
                            time_extended = new_end > old_end if (old_end and new_end) else False

                            if price_changed or time_extended:
                                msg_parts = []

                                if price_changed:
                                    msg_parts.append(f"{old_price}€ → {new_price}€")

                                if time_extended:
                                    old_end_str = old_end.strftime('%d/%m/%Y %H:%M:%S') if old_end else 'N/A'
                                    new_end_str = new_end.strftime('%d/%m/%Y %H:%M:%S') if new_end else 'N/A'
                                    msg_parts.append(f"timer reset to {new_end_str} from {old_end_str}")
                                    time_extended_count += 1

                                print(f"    💰 {event.reference}: {' | '.join(msg_parts)} ({minutes}m{secs}s remaining)")

                                # Update event in database with new price AND new end time
                                event.valores.lanceAtual = new_price
                                event.dataFim = new_end  # Update reset timer

                                async with get_db() as db:
                                    await db.save_event(event)
                                    await cache_manager.set(event.reference, event)

                                # Broadcast price update to SSE clients
                                from main import broadcast_price_update
                                await broadcast_price_update({
                                    "type": "price_update",
                                    "reference": event.reference,
                                    "old_price": old_price,
                                    "new_price": new_price,
                                    "old_end": old_end.isoformat() if old_end else None,
                                    "new_end": new_end.isoformat() if new_end else None,
                                    "time_extended": time_extended,
                                    "time_remaining": f"{minutes}m{secs}s",
                                    "timestamp": datetime.now().isoformat()
                                })

                                updated_count += 1

                    except Exception as e:
                        print(f"    ⚠️ Error checking {event.reference}: {e}")

                if updated_count > 0:
                    print(f"  ✅ {updated_count} events updated, {time_extended_count} timer resets")

                # Update pipeline stats and next run
                pipeline = self.pipelines['prices']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                # Calculate next run time (5 seconds from now)
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()

            finally:
                await scraper.close()
                await cache_manager.close()
                # Mark as not running
                self.pipelines['prices'].is_running = False
                # Reschedule next run after completion
                self._reschedule_pipeline('prices')

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
                # Reschedule next run after completion
                self._reschedule_pipeline('info')

        async def run_prices_urgent_pipeline():
            """Pipeline X-Urgent: Price verification every 1 MINUTE for events < 1 hour"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager

            # Mark as running
            self.pipelines['prices_urgent'].is_running = True

            # Check if cache needs refresh (every 10 minutes)
            now = datetime.now()
            needs_refresh = (
                self._urgent_cache_last_refresh is None or
                now - self._urgent_cache_last_refresh >= self._urgent_cache_refresh_interval
            )

            if needs_refresh:
                await self.refresh_urgent_events_cache()

            # Use cached events list
            if not self._urgent_events_cache:
                print(f"🟠 Pipeline X-Urgent: No urgent events in cache, skipping")
                # Update pipeline stats even when no events
                pipeline = self.pipelines['prices_urgent']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()
                return

            print(f"🟠 Pipeline X-Urgent: Checking {len(self._urgent_events_cache)} events (< 1.5h cache)")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                # Process cached urgent events
                urgent_events = []
                now = datetime.now()

                for event in self._urgent_events_cache:
                    if event.dataFim:
                        time_until_end = event.dataFim - now
                        seconds_until_end = time_until_end.total_seconds()

                        # Only scrape events < 1 hour (3600 seconds)
                        if 0 < seconds_until_end <= 3600:
                            urgent_events.append({
                                'event': event,
                                'seconds_until_end': seconds_until_end
                            })

                # Sort by urgency
                urgent_events.sort(key=lambda x: x['seconds_until_end'])

                if not urgent_events:
                    print(f"  🟠 No events ending in < 1h right now")
                    return

                print(f"  🟠 Scraping {len(urgent_events)} events (< 1h)")

                updated_count = 0
                time_extended_count = 0

                for item in urgent_events:
                    event = item['event']
                    seconds = item['seconds_until_end']
                    minutes = int(seconds / 60)
                    secs = int(seconds % 60)

                    try:
                        # LIGHTWEIGHT: Only scrape price + end time (fast)
                        volatile_data = await scraper.scrape_volatile_by_ids([event.reference])

                        if volatile_data and len(volatile_data) > 0:
                            data = volatile_data[0]
                            old_price = event.valores.lanceAtual or 0
                            new_price = data['lanceAtual'] or 0
                            old_end = event.dataFim
                            new_end = data['dataFim']

                            price_changed = old_price != new_price
                            time_extended = new_end > old_end if (old_end and new_end) else False

                            if price_changed or time_extended:
                                msg_parts = []
                                if price_changed:
                                    msg_parts.append(f"{old_price}€ → {new_price}€")
                                if time_extended:
                                    old_end_str = old_end.strftime('%d/%m/%Y %H:%M:%S') if old_end else 'N/A'
                                    new_end_str = new_end.strftime('%d/%m/%Y %H:%M:%S') if new_end else 'N/A'
                                    msg_parts.append(f"timer reset to {new_end_str} from {old_end_str}")
                                    time_extended_count += 1

                                print(f"    🟠 {event.reference}: {' | '.join(msg_parts)} ({minutes}m{secs}s remaining)")

                                event.valores.lanceAtual = new_price
                                event.dataFim = new_end

                                async with get_db() as db:
                                    await db.save_event(event)
                                    await cache_manager.set(event.reference, event)

                                # Broadcast price update to SSE clients
                                from main import broadcast_price_update
                                await broadcast_price_update({
                                    "type": "price_update",
                                    "reference": event.reference,
                                    "old_price": old_price,
                                    "new_price": new_price,
                                    "old_end": old_end.isoformat() if old_end else None,
                                    "new_end": new_end.isoformat() if new_end else None,
                                    "time_extended": time_extended,
                                    "time_remaining": f"{minutes}m{secs}s",
                                    "timestamp": datetime.now().isoformat()
                                })

                                updated_count += 1

                    except Exception as e:
                        print(f"    ⚠️ Error checking {event.reference}: {e}")

                if updated_count > 0:
                    print(f"  ✅ {updated_count} events updated, {time_extended_count} timer resets")

                # Update pipeline stats
                pipeline = self.pipelines['prices_urgent']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()

            finally:
                await scraper.close()
                await cache_manager.close()
                self.pipelines['prices_urgent'].is_running = False
                # Reschedule next run after completion
                self._reschedule_pipeline('prices_urgent')

        async def run_prices_soon_pipeline():
            """Pipeline X-Soon: Price verification every 10 MINUTES for events < 24 hours"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager

            # Mark as running
            self.pipelines['prices_soon'].is_running = True

            # Check if cache needs refresh (every 30 minutes)
            now = datetime.now()
            needs_refresh = (
                self._soon_cache_last_refresh is None or
                now - self._soon_cache_last_refresh >= self._soon_cache_refresh_interval
            )

            if needs_refresh:
                await self.refresh_soon_events_cache()

            # Use cached events list
            if not self._soon_events_cache:
                print(f"🟡 Pipeline X-Soon: No soon events in cache, skipping")
                # Update pipeline stats even when no events
                pipeline = self.pipelines['prices_soon']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()
                return

            print(f"🟡 Pipeline X-Soon: Checking {len(self._soon_events_cache)} events (< 25h cache)")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                # Process cached soon events
                soon_events = []
                now = datetime.now()

                for event in self._soon_events_cache:
                    if event.dataFim:
                        time_until_end = event.dataFim - now
                        seconds_until_end = time_until_end.total_seconds()

                        # Only scrape events < 24 hours (86400 seconds)
                        if 0 < seconds_until_end <= 86400:
                            soon_events.append({
                                'event': event,
                                'seconds_until_end': seconds_until_end
                            })

                # Sort by urgency
                soon_events.sort(key=lambda x: x['seconds_until_end'])

                if not soon_events:
                    print(f"  🟡 No events ending in < 24h right now")
                    return

                print(f"  🟡 Scraping {len(soon_events)} events (< 24h)")

                updated_count = 0
                time_extended_count = 0

                for item in soon_events:
                    event = item['event']
                    seconds = item['seconds_until_end']
                    hours = int(seconds / 3600)
                    minutes = int((seconds % 3600) / 60)
                    secs = int(seconds % 60)

                    try:
                        # LIGHTWEIGHT: Only scrape price + end time (fast)
                        volatile_data = await scraper.scrape_volatile_by_ids([event.reference])

                        if volatile_data and len(volatile_data) > 0:
                            data = volatile_data[0]
                            old_price = event.valores.lanceAtual or 0
                            new_price = data['lanceAtual'] or 0
                            old_end = event.dataFim
                            new_end = data['dataFim']

                            price_changed = old_price != new_price
                            time_extended = new_end > old_end if (old_end and new_end) else False

                            if price_changed or time_extended:
                                msg_parts = []
                                if price_changed:
                                    msg_parts.append(f"{old_price}€ → {new_price}€")
                                if time_extended:
                                    old_end_str = old_end.strftime('%d/%m/%Y %H:%M:%S') if old_end else 'N/A'
                                    new_end_str = new_end.strftime('%d/%m/%Y %H:%M:%S') if new_end else 'N/A'
                                    msg_parts.append(f"timer reset to {new_end_str} from {old_end_str}")
                                    time_extended_count += 1

                                print(f"    🟡 {event.reference}: {' | '.join(msg_parts)} ({hours}h{minutes}m{secs}s remaining)")

                                event.valores.lanceAtual = new_price
                                event.dataFim = new_end

                                async with get_db() as db:
                                    await db.save_event(event)
                                    await cache_manager.set(event.reference, event)

                                # Broadcast price update to SSE clients
                                from main import broadcast_price_update
                                await broadcast_price_update({
                                    "type": "price_update",
                                    "reference": event.reference,
                                    "old_price": old_price,
                                    "new_price": new_price,
                                    "old_end": old_end.isoformat() if old_end else None,
                                    "new_end": new_end.isoformat() if new_end else None,
                                    "time_extended": time_extended,
                                    "time_remaining": f"{hours}h{minutes}m{secs}s",
                                    "timestamp": datetime.now().isoformat()
                                })

                                updated_count += 1

                    except Exception as e:
                        print(f"    ⚠️ Error checking {event.reference}: {e}")

                if updated_count > 0:
                    print(f"  ✅ {updated_count} events updated, {time_extended_count} timer resets")

                # Update pipeline stats
                pipeline = self.pipelines['prices_soon']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                next_run_time = now + timedelta(hours=pipeline.interval_hours)
                pipeline.next_run = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()

            finally:
                await scraper.close()
                await cache_manager.close()
                self.pipelines['prices_soon'].is_running = False
                # Reschedule next run after completion
                self._reschedule_pipeline('prices_soon')

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
