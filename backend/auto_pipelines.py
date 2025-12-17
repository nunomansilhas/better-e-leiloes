"""
Automatic Pipelines Management System - SIMPLIFIED
Uses SQL queries instead of complex caching
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
    interval_seconds: int  # Interval in seconds for precision
    threshold_minutes: int  # Time threshold for event filtering (e.g., 5, 60, 1440)
    last_run: Optional[str] = None
    runs_count: int = 0
    is_running: bool = False


class AutoPipelinesManager:
    """Manages automatic pipelines with scheduling - SIMPLIFIED"""

    CONFIG_FILE = Path(__file__).parent / "auto_pipelines_config.json"

    # Pipeline definitions with time thresholds
    DEFAULT_PIPELINES = {
        "full": PipelineConfig(
            type="full",
            name="Pipeline Automática",
            description="Recolhe novos IDs, conteúdos e imagens",
            enabled=False,
            interval_seconds=8 * 3600,  # 8 hours
            threshold_minutes=0  # N/A for full pipeline
        ),
        "prices": PipelineConfig(
            type="prices",
            name="Pipeline X-Critical",
            description="< 5 MIN • A cada 5 SEGUNDOS • Eventos < 5 minutos",
            enabled=False,
            interval_seconds=5,  # 5 seconds
            threshold_minutes=5
        ),
        "prices_urgent": PipelineConfig(
            type="prices_urgent",
            name="Pipeline X-Urgent",
            description="< 1 HORA • A cada 1 MINUTO • Eventos < 1 hora",
            enabled=False,
            interval_seconds=60,  # 1 minute
            threshold_minutes=60
        ),
        "prices_soon": PipelineConfig(
            type="prices_soon",
            name="Pipeline X-Soon",
            description="< 24H • A cada 10 MINUTOS • Eventos < 24 horas",
            enabled=False,
            interval_seconds=600,  # 10 minutes
            threshold_minutes=1440  # 24 hours
        ),
        "info": PipelineConfig(
            type="info",
            name="Pipeline Y - Info",
            description="Verifica preços e datas de TODOS os eventos",
            enabled=False,
            interval_seconds=2 * 3600,  # 2 hours
            threshold_minutes=0  # N/A - checks all events
        )
    }

    def __init__(self):
        self.pipelines: Dict[str, PipelineConfig] = {}
        self.job_ids: Dict[str, str] = {}
        self._scheduler = None  # Reference to scheduler for getting next_run
        self._load_config()

    def _load_config(self):
        """Load configuration from file or create default"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)

                for key, value in data.items():
                    # Handle migration from old config (interval_hours -> interval_seconds)
                    if 'interval_hours' in value:
                        value['interval_seconds'] = int(value['interval_hours'] * 3600)
                        del value['interval_hours']
                    if 'threshold_minutes' not in value:
                        value['threshold_minutes'] = self.DEFAULT_PIPELINES.get(key, PipelineConfig(
                            type=key, name="", description="", enabled=False,
                            interval_seconds=60, threshold_minutes=0
                        )).threshold_minutes
                    # Remove old cache-related fields if present
                    for old_field in ['next_run']:
                        value.pop(old_field, None)
                    self.pipelines[key] = PipelineConfig(**value)

                print(f"📂 Auto-pipelines config loaded: {len(self.pipelines)} pipelines")
            except Exception as e:
                print(f"⚠️ Error loading config, creating default: {e}")
                self._create_default_config()
        else:
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration"""
        self.pipelines = {k: PipelineConfig(**asdict(v)) for k, v in self.DEFAULT_PIPELINES.items()}
        self._save_config()
        print(f"✨ Created default auto-pipelines config")

    def _save_config(self):
        """Save configuration to file"""
        try:
            data = {k: asdict(v) for k, v in self.pipelines.items()}
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving config: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get status of all pipelines with next_run from scheduler"""
        pipelines_status = {}

        for key, pipeline in self.pipelines.items():
            status = asdict(pipeline)

            # Get next_run from scheduler if job exists
            if self._scheduler and key in self.job_ids:
                job = self._scheduler.get_job(self.job_ids[key])
                if job and job.next_run_time:
                    status['next_run'] = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    status['next_run'] = None
            else:
                status['next_run'] = None

            pipelines_status[key] = status

        return {
            "pipelines": pipelines_status,
            "total": len(self.pipelines),
            "enabled": sum(1 for p in self.pipelines.values() if p.enabled)
        }

    async def initialize_enabled_pipelines(self, scheduler) -> int:
        """Initialize and schedule all enabled pipelines at startup"""
        self._scheduler = scheduler
        scheduled_count = 0

        for pipeline_type, pipeline in self.pipelines.items():
            if pipeline.enabled:
                await self._schedule_pipeline(pipeline_type, scheduler)
                scheduled_count += 1
                print(f"🔄 Scheduled: {pipeline.name}")

        if scheduled_count > 0:
            print(f"✅ {scheduled_count} pipeline(s) scheduled at startup")

        return scheduled_count

    async def toggle_pipeline(self, pipeline_type: str, enabled: bool, scheduler=None) -> Dict[str, Any]:
        """Enable or disable a pipeline"""
        if pipeline_type not in self.pipelines:
            raise ValueError(f"Pipeline type '{pipeline_type}' not found")

        pipeline = self.pipelines[pipeline_type]
        was_enabled = pipeline.enabled
        pipeline.enabled = enabled

        if scheduler:
            self._scheduler = scheduler

        if enabled:
            if scheduler and pipeline_type not in self.job_ids:
                await self._schedule_pipeline(pipeline_type, scheduler)
        else:
            if scheduler and pipeline_type in self.job_ids:
                await self._unschedule_pipeline(pipeline_type, scheduler)

        self._save_config()

        # Get next_run from scheduler
        next_run = None
        if enabled and self._scheduler and pipeline_type in self.job_ids:
            job = self._scheduler.get_job(self.job_ids[pipeline_type])
            if job and job.next_run_time:
                next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")

        status = "ativada" if enabled else "desativada"
        message = f"Pipeline {pipeline.name} {status}"
        if next_run:
            message += f" • Próxima execução: {next_run}"

        return {
            "success": True,
            "message": message,
            "pipeline": asdict(pipeline),
            "next_run": next_run,
            "was_enabled": was_enabled
        }

    async def _schedule_pipeline(self, pipeline_type: str, scheduler):
        """Schedule a pipeline to run automatically"""
        pipeline = self.pipelines[pipeline_type]
        job_id = f"auto_pipeline_{pipeline_type}"

        from apscheduler.triggers.interval import IntervalTrigger

        trigger = IntervalTrigger(seconds=pipeline.interval_seconds)
        task_func = self._get_pipeline_task(pipeline_type)

        scheduler.add_job(
            task_func,
            trigger=trigger,
            id=job_id,
            name=pipeline.name,
            replace_existing=True
        )

        self.job_ids[pipeline_type] = job_id
        print(f"📅 Scheduled {pipeline.name} every {pipeline.interval_seconds}s")

    async def _unschedule_pipeline(self, pipeline_type: str, scheduler):
        """Remove pipeline from scheduler"""
        if pipeline_type in self.job_ids:
            job_id = self.job_ids[pipeline_type]
            try:
                scheduler.remove_job(job_id)
                print(f"🗑️ Unscheduled: {job_id}")
            except Exception as e:
                print(f"⚠️ Error unscheduling {job_id}: {e}")
            finally:
                del self.job_ids[pipeline_type]

    def _get_pipeline_task(self, pipeline_type: str) -> Callable:
        """Get the async task function for a pipeline type"""

        async def run_price_pipeline(threshold_minutes: int, pipeline_key: str, emoji: str):
            """Generic price pipeline - uses SQL query directly"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager

            pipeline = self.pipelines[pipeline_key]
            pipeline.is_running = True

            try:
                # Use SQL to get events ending within threshold
                async with get_db() as db:
                    events = await db.get_events_ending_within(minutes=threshold_minutes)

                if not events:
                    print(f"{emoji} {pipeline.name}: Sem eventos (< {threshold_minutes}min)")
                    return

                print(f"{emoji} {pipeline.name}: {len(events)} eventos encontrados")

                scraper = EventScraper()
                cache_manager = CacheManager()

                try:
                    updated_count = 0

                    for event in events:
                        try:
                            new_events = await scraper.scrape_details_by_ids([event.reference])

                            if new_events:
                                new_event = new_events[0]
                                old_price = event.valores.lanceAtual or 0
                                new_price = new_event.valores.lanceAtual or 0
                                old_end = event.dataFim
                                new_end = new_event.dataFim

                                price_changed = old_price != new_price
                                time_extended = new_end > old_end if (old_end and new_end) else False

                                if price_changed or time_extended:
                                    changes = []
                                    if price_changed:
                                        changes.append(f"{old_price}€→{new_price}€")
                                    if time_extended:
                                        changes.append("timer reset")

                                    print(f"  {emoji} {event.reference}: {', '.join(changes)}")

                                    async with get_db() as db:
                                        await db.save_event(new_event)
                                        await cache_manager.set(event.reference, new_event)

                                    updated_count += 1

                        except Exception as e:
                            print(f"  ⚠️ Erro {event.reference}: {e}")

                    if updated_count > 0:
                        print(f"  ✅ {updated_count} atualizados")

                finally:
                    await scraper.close()
                    await cache_manager.close()

            finally:
                pipeline.is_running = False
                pipeline.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                self._save_config()

        async def run_full_pipeline():
            """Full pipeline: IDs + Content + Images"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager

            pipeline = self.pipelines['full']
            pipeline.is_running = True

            print(f"🤖 {pipeline.name}: Iniciando...")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                # Stage 1: Get IDs
                ids = await scraper.scrape_ids_only(tipo=None, max_pages=5)
                print(f"  📊 {len(ids)} IDs encontrados")

                async with get_db() as db:
                    for item in ids:
                        existing = await db.get_event(item['reference'])
                        if not existing:
                            from models import EventData, EventDetails, ValoresLeilao

                            event = EventData(
                                reference=item['reference'],
                                tipoEvento=item.get('tipo', 'imovel'),
                                valores=item.get('valores', ValoresLeilao()),
                                detalhes=EventDetails(tipo=item.get('tipo', 'N/A'), subtipo='N/A'),
                                descricao=None,
                                observacoes=None,
                                imagens=[]
                            )
                            await db.save_event(event)
                            await cache_manager.set(event.reference, event)

                # Stage 2 & 3: Details and images for new events
                new_refs = [item['reference'] for item in ids[:10]]
                if new_refs:
                    print(f"  📋 Scraping {len(new_refs)} eventos...")
                    events = await scraper.scrape_details_by_ids(new_refs)

                    print(f"  🖼️ Scraping imagens...")
                    images_map = await scraper.scrape_images_by_ids(new_refs)

                    async with get_db() as db:
                        for ref, images in images_map.items():
                            event = await db.get_event(ref)
                            if event:
                                event.imagens = images
                                await db.save_event(event)
                                await cache_manager.set(ref, event)

                print(f"✅ {pipeline.name}: Completo!")

            finally:
                await scraper.close()
                await cache_manager.close()
                pipeline.is_running = False
                pipeline.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                self._save_config()

        async def run_info_pipeline():
            """Info pipeline: Check ALL events for price/date changes"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager

            pipeline = self.pipelines['info']
            pipeline.is_running = True

            print(f"🔄 {pipeline.name}: Iniciando...")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                async with get_db() as db:
                    events, total = await db.list_events(limit=1000)

                if not events:
                    print(f"  ℹ️ Sem eventos na BD")
                    return

                print(f"  📊 Verificando {len(events)} eventos...")
                updated_count = 0

                for event in events:
                    try:
                        new_events = await scraper.scrape_details_by_ids([event.reference])

                        if new_events:
                            new_event = new_events[0]
                            has_changes = (
                                event.valores.lanceAtual != new_event.valores.lanceAtual or
                                event.dataFim != new_event.dataFim
                            )

                            if has_changes:
                                print(f"    🔄 {event.reference}: atualizado")
                                async with get_db() as db:
                                    await db.save_event(new_event)
                                    await cache_manager.set(event.reference, new_event)
                                updated_count += 1

                    except Exception as e:
                        print(f"    ⚠️ Erro {event.reference}: {e}")

                print(f"  ✅ {updated_count} eventos atualizados")

            finally:
                await scraper.close()
                await cache_manager.close()
                pipeline.is_running = False
                pipeline.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                self._save_config()

        # Map pipeline types to functions
        tasks = {
            "full": run_full_pipeline,
            "prices": lambda: run_price_pipeline(5, "prices", "🔴"),
            "prices_urgent": lambda: run_price_pipeline(60, "prices_urgent", "🟠"),
            "prices_soon": lambda: run_price_pipeline(1440, "prices_soon", "🟡"),
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
