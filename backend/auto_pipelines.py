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
            name="Pipeline de Verificação de Preços",
            description="Verifica alterações de preços, eventos próximos de terminar com mais frequência",
            enabled=False,
            interval_hours=0.5  # A cada 30 minutos
        ),
        "info": PipelineConfig(
            type="info",
            name="Pipeline de Verificação de Informações",
            description="Verificação rápida de informações e atualização se necessário",
            enabled=False,
            interval_hours=2.0  # A cada 2 horas
        )
    }

    def __init__(self):
        self.pipelines: Dict[str, PipelineConfig] = {}
        self.job_ids: Dict[str, str] = {}  # pipeline_type -> scheduler_job_id
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

                # Update last run
                pipeline = self.pipelines['full']
                pipeline.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                self._save_config()

            finally:
                await scraper.close()
                await cache_manager.close()

        async def run_prices_pipeline():
            """Pipeline X: Price verification for events ending soon"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager

            print(f"💰 Running Prices Auto-Pipeline...")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                # Get all events from database
                async with get_db() as db:
                    events = await db.list_events(limit=1000)

                if not events:
                    print(f"  ℹ️ No events in database")
                    return

                # Filter events ending within 7 days
                now = datetime.now()
                ending_soon = []

                for event in events:
                    if event.dataFim:
                        time_until_end = event.dataFim - now
                        days_until_end = time_until_end.total_seconds() / (24 * 3600)

                        if days_until_end > 0 and days_until_end <= 7:
                            ending_soon.append({
                                'event': event,
                                'days_until_end': days_until_end,
                                'hours_until_end': time_until_end.total_seconds() / 3600
                            })

                # Sort by time until end (most urgent first)
                ending_soon.sort(key=lambda x: x['days_until_end'])

                print(f"  📊 Found {len(ending_soon)} events ending within 7 days")

                if not ending_soon:
                    print(f"  ℹ️ No events ending soon")
                    return

                # Limit to first 20 events to avoid overload
                to_check = ending_soon[:20]
                print(f"  🔍 Checking prices for {len(to_check)} events...")

                updated_count = 0
                for item in to_check:
                    event = item['event']
                    hours = item['hours_until_end']

                    try:
                        # Re-scrape event details to get current price
                        new_events = await scraper.scrape_details_by_ids([event.reference])

                        if new_events and len(new_events) > 0:
                            new_event = new_events[0]
                            old_price = event.valores.lanceAtual or 0
                            new_price = new_event.valores.lanceAtual or 0

                            # Check if price changed
                            if old_price != new_price:
                                print(f"    💰 {event.reference}: {old_price}€ → {new_price}€ ({hours:.1f}h remaining)")

                                # Update event in database
                                event.valores = new_event.valores
                                event.dataFim = new_event.dataFim  # Also update end date (may change with bids)

                                async with get_db() as db:
                                    await db.save_event(event)
                                    await cache_manager.set(event.reference, event)

                                updated_count += 1
                            else:
                                print(f"    ✓ {event.reference}: {old_price}€ (unchanged, {hours:.1f}h remaining)")

                    except Exception as e:
                        print(f"    ⚠️ Error checking {event.reference}: {e}")

                print(f"  ✅ Price check complete: {updated_count} events updated")

                # Update pipeline stats
                pipeline = self.pipelines['prices']
                pipeline.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                self._save_config()

            finally:
                await scraper.close()
                await cache_manager.close()

        async def run_info_pipeline():
            """Pipeline Y: Quick info verification and update"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager
            import random

            print(f"🔄 Running Info Auto-Pipeline...")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                # Get all events from database
                async with get_db() as db:
                    events = await db.list_events(limit=1000)

                if not events:
                    print(f"  ℹ️ No events in database")
                    return

                # Sample 30 random events for quick check (to avoid overload)
                sample_size = min(30, len(events))
                sampled_events = random.sample(events, sample_size)

                print(f"  📊 Checking {sample_size} events (sampled from {len(events)} total)...")

                updated_count = 0
                errors_count = 0

                for event in sampled_events:
                    try:
                        # Re-scrape event details
                        new_events = await scraper.scrape_details_by_ids([event.reference])

                        if new_events and len(new_events) > 0:
                            new_event = new_events[0]
                            changed_fields = []

                            # Compare valores (prices)
                            if event.valores.valorBase != new_event.valores.valorBase:
                                changed_fields.append(f"valorBase: {event.valores.valorBase}€ → {new_event.valores.valorBase}€")
                            if event.valores.valorAbertura != new_event.valores.valorAbertura:
                                changed_fields.append(f"valorAbertura: {event.valores.valorAbertura}€ → {new_event.valores.valorAbertura}€")
                            if event.valores.valorMinimo != new_event.valores.valorMinimo:
                                changed_fields.append(f"valorMinimo: {event.valores.valorMinimo}€ → {new_event.valores.valorMinimo}€")
                            if event.valores.lanceAtual != new_event.valores.lanceAtual:
                                changed_fields.append(f"lanceAtual: {event.valores.lanceAtual}€ → {new_event.valores.lanceAtual}€")

                            # Compare dates
                            if event.dataInicio != new_event.dataInicio:
                                changed_fields.append(f"dataInicio changed")
                            if event.dataFim != new_event.dataFim:
                                changed_fields.append(f"dataFim changed")

                            # Compare detalhes (for móveis)
                            if event.tipoEvento == 'movel':
                                if event.detalhes.matricula != new_event.detalhes.matricula:
                                    changed_fields.append(f"matrícula: {event.detalhes.matricula} → {new_event.detalhes.matricula}")
                                if event.detalhes.marca != new_event.detalhes.marca:
                                    changed_fields.append(f"marca changed")

                            # Compare detalhes (for imóveis)
                            if event.tipoEvento == 'imovel':
                                if event.detalhes.tipologia != new_event.detalhes.tipologia:
                                    changed_fields.append(f"tipologia: {event.detalhes.tipologia} → {new_event.detalhes.tipologia}")
                                if event.detalhes.areaPrivativa != new_event.detalhes.areaPrivativa:
                                    changed_fields.append(f"área: {event.detalhes.areaPrivativa}m² → {new_event.detalhes.areaPrivativa}m²")

                            # If changes detected, update event
                            if changed_fields:
                                print(f"    🔄 {event.reference}: {len(changed_fields)} changes detected")
                                for field in changed_fields[:3]:  # Show first 3 changes
                                    print(f"       • {field}")

                                # Update event with new data
                                async with get_db() as db:
                                    await db.save_event(new_event)
                                    await cache_manager.set(event.reference, new_event)

                                updated_count += 1
                            else:
                                print(f"    ✓ {event.reference}: no changes")

                    except Exception as e:
                        print(f"    ⚠️ Error checking {event.reference}: {e}")
                        errors_count += 1

                print(f"  ✅ Info verification complete: {updated_count} events updated, {errors_count} errors")

                # Update pipeline stats
                pipeline = self.pipelines['info']
                pipeline.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                self._save_config()

            finally:
                await scraper.close()
                await cache_manager.close()

        # Return the appropriate function
        tasks = {
            "full": run_full_pipeline,
            "prices": run_prices_pipeline,
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
