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

# Price history tracking
from price_history import record_price_change


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
        "xmonitor": PipelineConfig(
            type="xmonitor",
            name="X-Monitor",
            description="Monitoriza eventos nas próximas 24h - atualiza lance_atual e data_fim",
            enabled=False,
            interval_hours=5/3600  # Base interval: 5 seconds for critical events
        ),
        "ysync": PipelineConfig(
            type="ysync",
            name="Y-Sync",
            description="Sincronização completa: todos os IDs + marca terminados",
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
            # Get upcoming events (next 1 hour, ordered by end time)
            async with get_db() as db:
                events = await db.get_upcoming_events(hours=1)

            if not events:
                self._critical_events_cache = []
                self._cache_last_refresh = datetime.now()
                print(f"🔴 Critical cache: No upcoming events in next 1h")
                return

            # Filter events ending in LESS THAN 6 MINUTES (360 seconds)
            now = datetime.now()
            critical_events = []

            print(f"🔍 Critical cache: {len(events)} upcoming events (< 1h)")

            for event in events:
                if event.data_fim:
                    time_until_end = event.data_fim - now
                    seconds_until_end = time_until_end.total_seconds()

                    print(f"    {event.reference}: {int(seconds_until_end)}s")

                    # Cache events ending in < 6 minutes (1-minute buffer)
                    if 0 < seconds_until_end <= 360:
                        critical_events.append(event)

            self._critical_events_cache = critical_events
            self._cache_last_refresh = datetime.now()

            if critical_events:
                print(f"🔴 Critical cache: {len(critical_events)} events (< 6 min)")

        except Exception as e:
            print(f"⚠️ Error refreshing critical events cache: {e}")

    async def refresh_urgent_events_cache(self):
        """Refresh cache of events ending in < 1.5 hours (called every 10 minutes)"""
        from database import get_db

        try:
            # Get upcoming events (next 2 hours, ordered by end time)
            async with get_db() as db:
                events = await db.get_upcoming_events(hours=2)

            # Filter events ending in < 1.5 hours
            now = datetime.now()
            urgent_events = []

            for event in events:
                if event.data_fim:
                    time_until_end = event.data_fim - now
                    seconds_until_end = time_until_end.total_seconds()
                    if 0 < seconds_until_end <= 5400:
                        urgent_events.append(event)

            self._urgent_events_cache = urgent_events
            self._urgent_cache_last_refresh = datetime.now()

            if urgent_events:
                print(f"🟠 Urgent cache: {len(urgent_events)} events (< 1.5h)")

        except Exception as e:
            print(f"⚠️ Error refreshing urgent events cache: {e}")

    async def refresh_soon_events_cache(self):
        """Refresh cache of events ending in < 25 hours (called every 30 minutes)"""
        from database import get_db

        try:
            # Get upcoming events (next 25 hours, ordered by end time)
            async with get_db() as db:
                events = await db.get_upcoming_events(hours=25)

            self._soon_events_cache = events
            self._soon_cache_last_refresh = datetime.now()

            if events:
                print(f"🟡 Soon cache: {len(events)} events (< 25h)")

        except Exception as e:
            print(f"⚠️ Error refreshing soon events cache: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get status of all pipelines"""
        # Calculate X-Monitor stats from cached events
        critical_count = len(self._critical_events_cache) if self._critical_events_cache else 0
        urgent_count = len(self._urgent_events_cache) if self._urgent_events_cache else 0
        soon_count = len(self._soon_events_cache) if self._soon_events_cache else 0

        return {
            "pipelines": {k: asdict(v) for k, v in self.pipelines.items()},
            "total": len(self.pipelines),
            "enabled": sum(1 for p in self.pipelines.values() if p.enabled),
            "xmonitor_stats": {
                "total": critical_count + urgent_count + soon_count,
                "critical": critical_count,
                "urgent": urgent_count,
                "soon": soon_count
            }
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

        # Update pipeline.next_run for API/UI display
        pipeline.next_run = next_run.strftime("%Y-%m-%d %H:%M:%S")
        self._save_config()

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

    def _reschedule_xmonitor(self, interval_seconds: int):
        """Reschedule X-Monitor with adaptive interval in seconds"""
        if not self._scheduler or 'xmonitor' not in self.job_ids:
            return

        pipeline = self.pipelines.get('xmonitor')
        if not pipeline or not pipeline.enabled:
            return

        from apscheduler.triggers.date import DateTrigger
        from datetime import datetime, timedelta

        job_id = self.job_ids['xmonitor']
        task_func = self._get_pipeline_task('xmonitor')

        # Schedule next run after interval_seconds
        next_run = datetime.now() + timedelta(seconds=interval_seconds)

        # Update pipeline.next_run for API/UI display
        pipeline.next_run = next_run.strftime("%Y-%m-%d %H:%M:%S")
        self._save_config()

        try:
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
            interval_str = f"{interval_seconds}s" if interval_seconds < 60 else f"{interval_seconds // 60}m"
            print(f"⏰ X-Monitor: próxima execução em {interval_str} ({next_run.strftime('%H:%M:%S')})")
        except Exception as e:
            print(f"⚠️ Error rescheduling X-Monitor: {e}")

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

        async def run_prices_pipeline():
            """Pipeline X: Price verification every 5 SECONDS for events < 5 minutes"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager
            from pipeline_state import get_pipeline_state

            # Skip if main pipeline is running
            main_pipeline = get_pipeline_state()
            if main_pipeline.is_active:
                print(f"⏸️ Auto-pipeline 'prices' skipped - main pipeline is running")
                return

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
                    if event.data_fim:
                        time_until_end = event.data_fim - now
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
                        # Use API for fast volatile data (price + end time)
                        volatile_data = await scraper.scrape_volatile_via_api([event.reference])

                        if volatile_data and len(volatile_data) > 0:
                            data = volatile_data[0]
                            old_price = event.lance_atual
                            new_price = data['lanceAtual']
                            old_end = event.data_fim
                            new_end = data['dataFim']

                            # Debug: show comparison
                            print(f"    🔎 {event.reference}: DB={old_price} vs Scraped={new_price}")

                            # Check if price changed (only if we got a valid new price)
                            price_changed = False
                            if new_price is not None:
                                # Update if: DB is None OR values are different
                                if old_price is None or old_price != new_price:
                                    price_changed = True

                            # Check if time was extended
                            time_extended = new_end > old_end if (old_end and new_end) else False

                            if price_changed or time_extended:
                                msg_parts = []

                                if price_changed:
                                    msg_parts.append(f"{old_price or 0}€ → {new_price}€")

                                if time_extended:
                                    old_end_str = old_end.strftime('%d/%m/%Y %H:%M:%S') if old_end else 'N/A'
                                    new_end_str = new_end.strftime('%d/%m/%Y %H:%M:%S') if new_end else 'N/A'
                                    msg_parts.append(f"timer reset to {new_end_str} from {old_end_str}")
                                    time_extended_count += 1

                                print(f"    💰 {event.reference}: {' | '.join(msg_parts)} ({minutes}m{secs}s remaining)")

                                # Update event in database - only update price if we got a valid one
                                if price_changed and new_price is not None:
                                    event.lance_atual = new_price
                                    # Record to price history JSON
                                    await record_price_change(event.reference, new_price, old_price)
                                if time_extended and new_end is not None:
                                    event.data_fim = new_end

                                async with get_db() as db:
                                    await db.save_event(event)
                                    await cache_manager.set(event.reference, event)

                                    # Process price change notifications (Tier 1)
                                    if price_changed and old_price is not None:
                                        from notification_engine import get_notification_engine
                                        notification_engine = get_notification_engine()
                                        await notification_engine.process_price_change(
                                            event, old_price, new_price, db
                                        )

                                # Broadcast price update to SSE clients
                                from main import broadcast_price_update
                                await broadcast_price_update({
                                    "type": "price_update",
                                    "reference": event.reference,
                                    "old_price": old_price or 0,
                                    "new_price": new_price or 0,
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
            from pipeline_state import get_pipeline_state

            # Skip if main pipeline is running
            main_pipeline = get_pipeline_state()
            if main_pipeline.is_active:
                print(f"⏸️ Auto-pipeline 'info' skipped - main pipeline is running")
                return

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
                        # Re-scrape event details via API (FAST!)
                        new_events = await scraper.scrape_details_via_api([event.reference])

                        if new_events and len(new_events) > 0:
                            new_event = new_events[0]
                            changed_fields = []

                            # Compare values (prices)
                            if event.valor_base != new_event.valor_base:
                                changed_fields.append(f"valor_base: {event.valor_base}€ → {new_event.valor_base}€")
                            if event.valor_abertura != new_event.valor_abertura:
                                changed_fields.append(f"valor_abertura: {event.valor_abertura}€ → {new_event.valor_abertura}€")
                            if event.valor_minimo != new_event.valor_minimo:
                                changed_fields.append(f"valor_minimo: {event.valor_minimo}€ → {new_event.valor_minimo}€")
                            if event.lance_atual != new_event.lance_atual:
                                changed_fields.append(f"lance_atual: {event.lance_atual}€ → {new_event.lance_atual}€")

                            # Compare dates
                            if event.data_inicio != new_event.data_inicio:
                                changed_fields.append(f"data_inicio changed")
                            if event.data_fim != new_event.data_fim:
                                changed_fields.append(f"data_fim changed")

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
            from pipeline_state import get_pipeline_state

            # Skip if main pipeline is running
            main_pipeline = get_pipeline_state()
            if main_pipeline.is_active:
                print(f"⏸️ Auto-pipeline 'prices_urgent' skipped - main pipeline is running")
                return

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
                    if event.data_fim:
                        time_until_end = event.data_fim - now
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
                        # Use API for fast volatile data (price + end time)
                        volatile_data = await scraper.scrape_volatile_via_api([event.reference])

                        if volatile_data and len(volatile_data) > 0:
                            data = volatile_data[0]
                            old_price = event.lance_atual
                            new_price = data['lanceAtual']
                            old_end = event.data_fim
                            new_end = data['dataFim']

                            # Debug: show comparison
                            print(f"    🔎 {event.reference}: DB={old_price} vs Scraped={new_price}")

                            # Check if price changed (only if we got a valid new price)
                            price_changed = False
                            if new_price is not None:
                                # Update if: DB is None OR values are different
                                if old_price is None or old_price != new_price:
                                    price_changed = True

                            time_extended = new_end > old_end if (old_end and new_end) else False

                            if price_changed or time_extended:
                                msg_parts = []
                                if price_changed:
                                    msg_parts.append(f"{old_price or 0}€ → {new_price}€")
                                if time_extended:
                                    old_end_str = old_end.strftime('%d/%m/%Y %H:%M:%S') if old_end else 'N/A'
                                    new_end_str = new_end.strftime('%d/%m/%Y %H:%M:%S') if new_end else 'N/A'
                                    msg_parts.append(f"timer reset to {new_end_str} from {old_end_str}")
                                    time_extended_count += 1

                                print(f"    🟠 {event.reference}: {' | '.join(msg_parts)} ({minutes}m{secs}s remaining)")

                                # Update event - only update price if we got a valid one
                                if price_changed and new_price is not None:
                                    event.lance_atual = new_price
                                    # Record to price history JSON
                                    await record_price_change(event.reference, new_price, old_price)
                                if time_extended and new_end is not None:
                                    event.data_fim = new_end

                                async with get_db() as db:
                                    await db.save_event(event)
                                    await cache_manager.set(event.reference, event)

                                    # Process price change notifications (Tier 2)
                                    if price_changed and old_price is not None:
                                        from notification_engine import get_notification_engine
                                        notification_engine = get_notification_engine()
                                        await notification_engine.process_price_change(
                                            event, old_price, new_price, db
                                        )

                                # Broadcast price update to SSE clients
                                from main import broadcast_price_update
                                await broadcast_price_update({
                                    "type": "price_update",
                                    "reference": event.reference,
                                    "old_price": old_price or 0,
                                    "new_price": new_price or 0,
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
            from pipeline_state import get_pipeline_state

            # Skip if main pipeline is running
            main_pipeline = get_pipeline_state()
            if main_pipeline.is_active:
                print(f"⏸️ Auto-pipeline 'prices_soon' skipped - main pipeline is running")
                return

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
                    if event.data_fim:
                        time_until_end = event.data_fim - now
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
                        # Use API for fast volatile data (price + end time)
                        volatile_data = await scraper.scrape_volatile_via_api([event.reference])

                        if volatile_data and len(volatile_data) > 0:
                            data = volatile_data[0]
                            old_price = event.lance_atual
                            new_price = data['lanceAtual']
                            old_end = event.data_fim
                            new_end = data['dataFim']

                            # Debug: show comparison
                            print(f"    🔎 {event.reference}: DB={old_price} vs Scraped={new_price}")

                            # Check if price changed (only if we got a valid new price)
                            price_changed = False
                            if new_price is not None:
                                # Update if: DB is None OR values are different
                                if old_price is None or old_price != new_price:
                                    price_changed = True

                            time_extended = new_end > old_end if (old_end and new_end) else False

                            if price_changed or time_extended:
                                msg_parts = []
                                if price_changed:
                                    msg_parts.append(f"{old_price or 0}€ → {new_price}€")
                                if time_extended:
                                    old_end_str = old_end.strftime('%d/%m/%Y %H:%M:%S') if old_end else 'N/A'
                                    new_end_str = new_end.strftime('%d/%m/%Y %H:%M:%S') if new_end else 'N/A'
                                    msg_parts.append(f"timer reset to {new_end_str} from {old_end_str}")
                                    time_extended_count += 1

                                print(f"    🟡 {event.reference}: {' | '.join(msg_parts)} ({hours}h{minutes}m{secs}s remaining)")

                                # Update event - only update price if we got a valid one
                                if price_changed and new_price is not None:
                                    event.lance_atual = new_price
                                    # Record to price history JSON
                                    await record_price_change(event.reference, new_price, old_price)
                                if time_extended and new_end is not None:
                                    event.data_fim = new_end

                                async with get_db() as db:
                                    await db.save_event(event)
                                    await cache_manager.set(event.reference, event)

                                    # Process price change notifications (Tier 3)
                                    if price_changed and old_price is not None:
                                        from notification_engine import get_notification_engine
                                        notification_engine = get_notification_engine()
                                        await notification_engine.process_price_change(
                                            event, old_price, new_price, db
                                        )

                                # Broadcast price update to SSE clients
                                from main import broadcast_price_update
                                await broadcast_price_update({
                                    "type": "price_update",
                                    "reference": event.reference,
                                    "old_price": old_price or 0,
                                    "new_price": new_price or 0,
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

        async def run_xmonitor_pipeline():
            """X-Monitor: Monitoriza eventos com intervalos adaptativos baseados na urgência"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager
            from pipeline_state import get_pipeline_state

            # Skip if main pipeline is running
            main_pipeline = get_pipeline_state()
            if main_pipeline.is_active:
                print(f"⏸️ X-Monitor skipped - main pipeline is running")
                return

            # Mark as running
            self.pipelines['xmonitor'].is_running = True

            # Refresh caches to get current events
            now = datetime.now()
            await self.refresh_critical_events_cache()
            await self.refresh_urgent_events_cache()
            await self.refresh_soon_events_cache()

            # Count events in each tier
            critical_events = []
            urgent_events = []
            soon_events = []

            for event in self._critical_events_cache or []:
                if event.data_fim:
                    seconds = (event.data_fim - now).total_seconds()
                    if 0 < seconds <= 300:
                        critical_events.append({'event': event, 'tier': 'critical', 'seconds': seconds})

            for event in self._urgent_events_cache or []:
                if event.data_fim:
                    seconds = (event.data_fim - now).total_seconds()
                    if 300 < seconds <= 3600:
                        urgent_events.append({'event': event, 'tier': 'urgent', 'seconds': seconds})

            for event in self._soon_events_cache or []:
                if event.data_fim:
                    seconds = (event.data_fim - now).total_seconds()
                    if 3600 < seconds <= 86400:
                        soon_events.append({'event': event, 'tier': 'soon', 'seconds': seconds})

            # Determine which tier to process and next interval
            # Priority: critical > urgent > soon
            if critical_events:
                events_to_process = critical_events
                next_interval_seconds = 5  # 5 seconds for critical
                tier_name = "🔴 Critical"
            elif urgent_events:
                events_to_process = urgent_events
                next_interval_seconds = 60  # 1 minute for urgent
                tier_name = "🟠 Urgent"
            elif soon_events:
                events_to_process = soon_events
                next_interval_seconds = 600  # 10 minutes for soon
                tier_name = "🟡 Soon"
            else:
                print(f"🔴 X-Monitor: Sem eventos nas próximas 24h")
                self.pipelines['xmonitor'].is_running = False
                # Reschedule to check again in 30 minutes
                self._reschedule_xmonitor(1800)
                return

            print(f"🔴 X-Monitor {tier_name}: {len(events_to_process)} eventos (total: 🔴{len(critical_events)} 🟠{len(urgent_events)} 🟡{len(soon_events)})")

            scraper = EventScraper()

            try:
                updated_count = 0

                for item in events_to_process:
                    event = item['event']
                    tier = item['tier']
                    seconds = item['seconds']

                    tier_emoji = {'critical': '🔴', 'urgent': '🟠', 'soon': '🟡'}[tier]

                    try:
                        volatile_data = await scraper.scrape_volatile_via_api([event.reference])

                        if volatile_data and len(volatile_data) > 0:
                            data = volatile_data[0]
                            old_price = event.lance_atual
                            new_price = data.get('lanceAtual') or data.get('lance_atual')
                            old_end = event.data_fim
                            new_end = data.get('dataFim') or data.get('data_fim')

                            price_changed = new_price is not None and old_price != new_price
                            time_extended = new_end and old_end and new_end > old_end

                            if price_changed or time_extended:
                                if price_changed:
                                    event.lance_atual = new_price
                                    # Record to price history JSON
                                    await record_price_change(event.reference, new_price, old_price)
                                if time_extended:
                                    event.data_fim = new_end

                                async with get_db() as db:
                                    await db.save_event(event)

                                    # Process price change notifications
                                    if price_changed and old_price is not None:
                                        from notification_engine import get_notification_engine
                                        notification_engine = get_notification_engine()
                                        await notification_engine.process_price_change(
                                            event, old_price, new_price, db
                                        )

                                    # Process ending_soon notifications
                                    if event.data_fim:
                                        from notification_engine import get_notification_engine
                                        notification_engine = get_notification_engine()
                                        remaining = (event.data_fim - datetime.now()).total_seconds() / 60
                                        if 0 < remaining <= 1440:  # Within 24 hours
                                            try:
                                                await notification_engine.process_ending_soon(
                                                    event, int(remaining), db
                                                )
                                            except Exception as e:
                                                pass  # Silent fail for ending_soon

                                # Record to history
                                from xmonitor_history import record_event_update
                                record_event_update(
                                    reference=event.reference,
                                    lance_atual=new_price,
                                    data_fim=new_end,
                                    old_lance=old_price,
                                    old_data_fim=old_end,
                                    tier=tier
                                )

                                mins = int(seconds / 60)
                                secs = int(seconds % 60)
                                print(f"    {tier_emoji} {event.reference}: {old_price or 0}€ → {new_price}€ ({mins}m{secs}s)")
                                updated_count += 1

                    except Exception as e:
                        print(f"    ⚠️ Error {event.reference}: {e}")

                if updated_count > 0:
                    print(f"  ✅ X-Monitor: {updated_count} eventos atualizados")

                # Update pipeline stats
                pipeline = self.pipelines['xmonitor']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                self._save_config()

            finally:
                await scraper.close()
                self.pipelines['xmonitor'].is_running = False
                # Reschedule with adaptive interval
                self._reschedule_xmonitor(next_interval_seconds)

        async def run_ysync_pipeline():
            """Y-Sync: Sincroniza novos IDs e marca eventos terminados"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager
            from pipeline_state import get_pipeline_state

            # Skip if main pipeline is running
            main_pipeline = get_pipeline_state()
            if main_pipeline.is_active:
                print(f"⏸️ Y-Sync skipped - main pipeline is running")
                return

            # Mark as running
            self.pipelines['ysync'].is_running = True
            self._save_config()

            print(f"🔄 Y-Sync: A iniciar sincronização completa...")

            scraper = EventScraper()
            cache_manager = CacheManager()

            try:
                new_ids_count = 0
                terminated_count = 0

                # Stage 1: Discover ALL IDs (full scan, no page limit)
                print(f"  🔍 Stage 1: A descobrir TODOS os IDs...")
                ids = await scraper.scrape_ids_only(tipo=None, max_pages=None)
                print(f"  📊 {len(ids)} IDs encontrados no site")

                # Find only NEW ids
                new_ids = []
                async with get_db() as db:
                    for item in ids:
                        existing = await db.get_event(item['reference'])
                        if not existing:
                            new_ids.append(item)

                if new_ids:
                    print(f"  🆕 {len(new_ids)} novos IDs, a obter dados via API...")
                    new_refs = [item['reference'] for item in new_ids]
                    events = await scraper.scrape_details_via_api(new_refs)

                    # Process notifications for new events
                    from notification_engine import process_new_events_batch
                    notifications_count = 0

                    async with get_db() as db:
                        for event in events:
                            await db.save_event(event)
                            await cache_manager.set(event.reference, event)
                            new_ids_count += 1

                        # Check notification rules for new events
                        notifications_count = await process_new_events_batch(events, db)

                    if notifications_count > 0:
                        print(f"  🔔 {notifications_count} notificações criadas para novos eventos")
                else:
                    print(f"  ✓ Nenhum ID novo encontrado")

                print(f"  📊 Stage 1 completo: {new_ids_count} novos eventos adicionados")

                # Stage 2: Check events that have passed their dataFim
                print(f"  🔄 Stage 2: A verificar eventos terminados...")
                now = datetime.now()

                async with get_db() as db:
                    # Get active events
                    events, total = await db.list_events(limit=500, cancelado=False)

                    candidates = []
                    for event in events:
                        if event.data_fim and event.data_fim < now:
                            candidates.append(event)

                    if candidates:
                        print(f"    📋 {len(candidates)} candidatos a terminado")

                        # OPTIMIZED: Batch API call instead of one-by-one
                        refs = [e.reference for e in candidates]
                        api_results = await scraper.scrape_volatile_via_api(refs)

                        # Create lookup map for quick access
                        api_map = {r['reference']: r for r in api_results}

                        # Import notification function
                        from notification_engine import create_event_ended_notification

                        for event in candidates:
                            try:
                                data = api_map.get(event.reference)

                                if data:
                                    new_end = data.get('dataFim')
                                    new_price = data.get('lanceAtual')
                                    old_price = event.lance_atual

                                    # Check for price change and record it
                                    if new_price is not None and old_price != new_price:
                                        await record_price_change(event.reference, new_price, old_price)
                                        print(f"    💰 Y-Sync: Preço alterado {event.reference}: {old_price} → {new_price}")

                                        # Process notification for price change
                                        from notification_engine import get_notification_engine
                                        notification_engine = get_notification_engine()
                                        await notification_engine.process_price_change(event, old_price, new_price, db)

                                        # Update price in DB
                                        await db.update_event_fields(event.reference, {'lance_atual': new_price})

                                        # Broadcast price update via SSE
                                        from main import broadcast_price_update
                                        await broadcast_price_update({
                                            "type": "price_update",
                                            "reference": event.reference,
                                            "titulo": event.titulo,
                                            "old_price": old_price,
                                            "new_price": new_price,
                                            "timestamp": datetime.now().isoformat()
                                        })

                                    if new_end and new_end < now:
                                        # Only update specific fields, not full save
                                        await db.update_event_fields(
                                            event.reference,
                                            {'terminado': True, 'cancelado': True, 'ativo': False, 'lance_atual': new_price or old_price}
                                        )
                                        await cache_manager.invalidate(event.reference)
                                        terminated_count += 1
                                        print(f"    🔴 Terminado: {event.reference}")

                                        # Create notification for ended event
                                        await create_event_ended_notification({
                                            'reference': event.reference,
                                            'titulo': event.titulo,
                                            'tipo': event.tipo,
                                            'subtipo': event.subtipo,
                                            'distrito': event.distrito,
                                            'lance_atual': new_price or old_price,
                                            'valor_base': event.valor_base,
                                            'data_fim': new_end
                                        }, db)

                                        # Broadcast event_ended via SSE
                                        from main import broadcast_price_update
                                        await broadcast_price_update({
                                            "type": "event_ended",
                                            "reference": event.reference,
                                            "titulo": event.titulo,
                                            "tipo": event.tipo,
                                            "final_price": new_price or old_price,
                                            "valor_base": event.valor_base,
                                            "timestamp": datetime.now().isoformat()
                                        })
                                else:
                                    # Not in API results = likely 404/not found
                                    await db.update_event_fields(
                                        event.reference,
                                        {'terminado': True, 'ativo': False}
                                    )
                                    terminated_count += 1
                                    print(f"    🔴 Não encontrado: {event.reference}")

                                    # Create notification for ended event (not found)
                                    await create_event_ended_notification({
                                        'reference': event.reference,
                                        'titulo': event.titulo,
                                        'tipo': event.tipo,
                                        'subtipo': event.subtipo,
                                        'distrito': event.distrito,
                                        'lance_atual': event.lance_atual,
                                        'valor_base': event.valor_base,
                                        'data_fim': event.data_fim
                                    }, db)

                                    # Broadcast event_ended via SSE
                                    from main import broadcast_price_update
                                    await broadcast_price_update({
                                        "type": "event_ended",
                                        "reference": event.reference,
                                        "titulo": event.titulo,
                                        "tipo": event.tipo,
                                        "final_price": event.lance_atual,
                                        "valor_base": event.valor_base,
                                        "timestamp": datetime.now().isoformat()
                                    })

                            except Exception as e:
                                print(f"    ❌ Erro {event.reference}: {str(e)[:50]}")
                    else:
                        print(f"    ✓ Nenhum evento terminado")

                print(f"  ✅ Y-Sync completo: {new_ids_count} novos, {terminated_count} terminados")

                # Stage 3: Cleanup old notifications (runs every Y-Sync = every 2h)
                print(f"  🗑️ Stage 3: Limpeza de notificações antigas...")
                from notification_engine import cleanup_old_notifications
                async with get_db() as db:
                    await cleanup_old_notifications(db, days=30)

            finally:
                await scraper.close()
                await cache_manager.close()
                self.pipelines['ysync'].is_running = False

                # Update pipeline stats AFTER completion (timer starts now)
                pipeline = self.pipelines['ysync']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                pipeline.next_run = (now + timedelta(hours=pipeline.interval_hours)).strftime("%Y-%m-%d %H:%M:%S")
                self._save_config()

                self._reschedule_pipeline('ysync')

        # Return the appropriate function
        tasks = {
            "xmonitor": run_xmonitor_pipeline,
            "ysync": run_ysync_pipeline,
            # Legacy support
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
