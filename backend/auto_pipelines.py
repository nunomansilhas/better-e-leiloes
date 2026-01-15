"""
Automatic Pipelines Management System
Manages scheduled automatic scrapers with persistent configuration
"""

import sys
import json
import asyncio
import concurrent.futures
from datetime import datetime, timedelta


# Thread pool para executar Playwright operations no Windows
_proactor_executor = None


def get_proactor_executor():
    """Get or create a thread pool executor for Playwright operations."""
    global _proactor_executor
    if _proactor_executor is None:
        _proactor_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="proactor"
        )
    return _proactor_executor


async def run_in_proactor(coro_func, *args, **kwargs):
    """
    Windows fix: Run an async function in a thread with ProactorEventLoop.
    This allows Playwright to work even when the main loop is SelectorEventLoop.
    On Linux/Mac, just runs the coroutine directly.
    """
    if sys.platform != 'win32':
        # Linux/Mac: run directly
        return await coro_func(*args, **kwargs)

    # Windows: run in thread with ProactorEventLoop
    main_loop = asyncio.get_event_loop()

    def thread_target():
        # Create ProactorEventLoop for this thread
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            coro = coro_func(*args, **kwargs)
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    return await main_loop.run_in_executor(get_proactor_executor(), thread_target)


# nest_asyncio para nested event loops (APScheduler + Playwright)
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass
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
        ),
        "zwatch": PipelineConfig(
            type="zwatch",
            name="Z-Watch",
            description="Monitoriza EventosMaisRecentes API a cada 10 minutos",
            enabled=False,
            interval_hours=10/60  # A cada 10 minutos
        )
    }

    def __init__(self):
        self.pipelines: Dict[str, PipelineConfig] = {}
        self.job_ids: Dict[str, str] = {}  # pipeline_type -> scheduler_job_id
        self._scheduler = None  # Store scheduler reference for rescheduling

        # Mutex for heavy pipelines (Y-Sync, Z-Watch, Pipeline API)
        # X-Monitor is exempt - it runs freely for real-time price tracking
        self._heavy_pipeline_lock = asyncio.Lock()
        self._heavy_pipeline_running: Optional[str] = None  # Which heavy pipeline is running
        self._heavy_pipeline_waiting: list = []  # Queue of waiting pipelines

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
        """Load configuration from file or create default (sync fallback)"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)

                # Convert dict to PipelineConfig objects
                for key, value in data.items():
                    self.pipelines[key] = PipelineConfig(**value)

                # Log which pipelines are enabled
                enabled = [k for k, p in self.pipelines.items() if p.enabled]
                print(f"📂 Auto-pipelines config loaded from JSON: {len(self.pipelines)} pipelines (enabled: {enabled or 'none'})")
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
        """Save configuration to JSON file (sync fallback)"""
        try:
            data = {k: asdict(v) for k, v in self.pipelines.items()}

            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            # Log which pipelines are enabled
            enabled = [k for k, v in data.items() if v.get('enabled')]
            print(f"💾 Auto-pipelines config saved to JSON (enabled: {enabled or 'none'})")
        except Exception as e:
            print(f"⚠️ Error saving auto-pipelines config: {e}")

    async def load_from_database(self):
        """Load pipeline state from database (async)"""
        from database import get_db

        try:
            async with get_db() as db:
                states = await db.get_all_pipeline_states()

                for state in states:
                    if state.pipeline_name in self.pipelines:
                        # Update in-memory config from database
                        self.pipelines[state.pipeline_name].enabled = state.enabled
                        self.pipelines[state.pipeline_name].is_running = state.is_running
                        self.pipelines[state.pipeline_name].last_run = state.last_run.isoformat() if state.last_run else None
                        self.pipelines[state.pipeline_name].next_run = state.next_run.isoformat() if state.next_run else None
                        self.pipelines[state.pipeline_name].runs_count = state.runs_count

                enabled = [s.pipeline_name for s in states if s.enabled]
                print(f"📂 Auto-pipelines loaded from DB: {len(states)} pipelines (enabled: {enabled or 'none'})")

                # Also save to JSON for quick startup next time
                self._save_config()

        except Exception as e:
            print(f"⚠️ Error loading from database, using JSON fallback: {e}")

    async def save_to_database(self, pipeline_type: str):
        """Save single pipeline state to database (async)"""
        from database import get_db

        if pipeline_type not in self.pipelines:
            return

        config = self.pipelines[pipeline_type]

        try:
            async with get_db() as db:
                # Parse datetime strings
                last_run = None
                if config.last_run:
                    try:
                        last_run = datetime.fromisoformat(config.last_run)
                    except:
                        pass

                next_run = None
                if config.next_run:
                    try:
                        next_run = datetime.fromisoformat(config.next_run)
                    except:
                        pass

                await db.save_pipeline_state(
                    pipeline_name=pipeline_type,
                    enabled=config.enabled,
                    is_running=config.is_running,
                    interval_hours=config.interval_hours,
                    description=config.description,
                    last_run=last_run,
                    next_run=next_run,
                    runs_count=config.runs_count
                )
                print(f"💾 Pipeline {pipeline_type} saved to DB (enabled: {config.enabled})")

        except Exception as e:
            print(f"⚠️ Error saving to database: {e}")

        # Also save to JSON as backup
        self._save_config()

    async def refresh_critical_events_cache(self):
        """Refresh cache of events ending in < 6 minutes OR recently ended (called every 5 minutes)"""
        from database import get_db

        try:
            # Get events for monitoring (upcoming + recently ended in last 10 min)
            async with get_db() as db:
                events = await db.get_events_for_monitoring(hours_ahead=1, minutes_behind=10)

            if not events:
                self._critical_events_cache = []
                self._cache_last_refresh = datetime.now()
                print(f"🔴 Critical cache: No events to monitor")
                return

            # Filter events ending in < 6 minutes OR ended in last 5 minutes
            now = datetime.now()
            critical_events = []

            for event in events:
                if event.data_fim:
                    time_until_end = event.data_fim - now
                    seconds_until_end = time_until_end.total_seconds()

                    # Include: ending in < 6 min (360s) OR ended in last 5 min (-300s)
                    if -300 <= seconds_until_end <= 360:
                        critical_events.append(event)

            self._critical_events_cache = critical_events
            self._cache_last_refresh = datetime.now()

            if critical_events:
                upcoming = sum(1 for e in critical_events if (e.data_fim - now).total_seconds() > 0)
                expired = len(critical_events) - upcoming
                print(f"🔴 Critical cache: {len(critical_events)} events ({upcoming} upcoming, {expired} expired)")

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
        # Calculate X-Monitor stats with EXCLUSIVE tier counts (no overlap)
        now = datetime.now()
        critical_count = 0
        urgent_count = 0
        soon_count = 0

        # Count from soon cache (largest) and categorize by actual time remaining
        for event in self._soon_events_cache or []:
            if event.data_fim:
                seconds = (event.data_fim - now).total_seconds()
                if 0 < seconds <= 300:  # < 5 min = Critical
                    critical_count += 1
                elif 300 < seconds <= 3600:  # 5-60 min = Urgent
                    urgent_count += 1
                elif 3600 < seconds <= 86400:  # 1-24h = Soon
                    soon_count += 1

        return {
            "pipelines": {k: asdict(v) for k, v in self.pipelines.items()},
            "total": len(self.pipelines),
            "enabled": sum(1 for p in self.pipelines.values() if p.enabled),
            "xmonitor_stats": {
                "total": critical_count + urgent_count + soon_count,
                "critical": critical_count,
                "urgent": urgent_count,
                "soon": soon_count
            },
            # Mutex status for heavy pipelines
            "heavy_pipeline_running": self._heavy_pipeline_running,
            "heavy_pipeline_waiting": self._heavy_pipeline_waiting.copy()
        }

    async def acquire_heavy_lock(self, pipeline_name: str) -> bool:
        """
        Try to acquire lock for heavy pipeline (Y-Sync, Z-Watch, Pipeline API).
        Returns True if lock acquired, False if should skip (another heavy pipeline running).
        """
        if self._heavy_pipeline_lock.locked():
            # Another heavy pipeline is running
            if pipeline_name not in self._heavy_pipeline_waiting:
                self._heavy_pipeline_waiting.append(pipeline_name)
            print(f"⏸️ {pipeline_name} aguarda (a correr: {self._heavy_pipeline_running})")
            return False

        await self._heavy_pipeline_lock.acquire()
        self._heavy_pipeline_running = pipeline_name
        if pipeline_name in self._heavy_pipeline_waiting:
            self._heavy_pipeline_waiting.remove(pipeline_name)
        print(f"🔒 {pipeline_name} adquiriu lock")
        return True

    def release_heavy_lock(self, pipeline_name: str):
        """Release lock for heavy pipeline."""
        if self._heavy_pipeline_running == pipeline_name:
            self._heavy_pipeline_running = None
            if self._heavy_pipeline_lock.locked():
                self._heavy_pipeline_lock.release()
            print(f"🔓 {pipeline_name} libertou lock")

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

        # Save to database (async)
        await self.save_to_database(pipeline_type)

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
                                    # Record to price history DB
                                    await record_price_change(event.reference, new_price, old_price, source='xmonitor')
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
                                    # Record to price history DB
                                    await record_price_change(event.reference, new_price, old_price, source='xmonitor')
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
                                    # Record to price history DB
                                    await record_price_change(event.reference, new_price, old_price, source='xmonitor')
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
                # Reschedule for 30 seconds later
                self._reschedule_xmonitor(30)
                return

            # Mark as running
            self.pipelines['xmonitor'].is_running = True
            await self.save_to_database('xmonitor')

            # Refresh caches to get current events
            now = datetime.now()
            await self.refresh_critical_events_cache()
            await self.refresh_urgent_events_cache()
            await self.refresh_soon_events_cache()

            # Count events in each tier
            critical_events = []
            urgent_events = []
            soon_events = []
            expired_events = []  # Events that just ended (need to mark as ativo=0)

            for event in self._critical_events_cache or []:
                if event.data_fim:
                    seconds = (event.data_fim - now).total_seconds()
                    if 0 < seconds <= 300:
                        critical_events.append({'event': event, 'tier': 'critical', 'seconds': seconds})
                    elif -300 <= seconds <= 0:  # Ended in the last 5 minutes
                        expired_events.append({'event': event, 'tier': 'expired', 'seconds': seconds})

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
                await self.save_to_database('xmonitor')
                # Reschedule to check again in 30 minutes
                self._reschedule_xmonitor(1800)
                return

            print(f"🔴 X-Monitor {tier_name}: {len(events_to_process)} eventos (🔴{len(critical_events)} 🟠{len(urgent_events)} 🟡{len(soon_events)} ⏱️{len(expired_events)})")

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
                                    # Record to price history DB
                                    await record_price_change(event.reference, new_price, old_price, source='xmonitor')
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

                # Process expired events - mark as ativo=0
                terminated_count = 0
                if expired_events:
                    print(f"  ⏱️ X-Monitor: {len(expired_events)} eventos expirados a processar...")
                    from cache import CacheManager
                    cache_manager = CacheManager()

                    for item in expired_events:
                        event = item['event']
                        try:
                            volatile_data = await scraper.scrape_volatile_via_api([event.reference])

                            async with get_db() as db:
                                if volatile_data and len(volatile_data) > 0:
                                    data = volatile_data[0]
                                    # Use API values for terminado/cancelado
                                    api_terminado = data.get('terminado', True)
                                    api_cancelado = data.get('cancelado', False)
                                    final_price = data.get('lanceAtual') or event.lance_atual

                                    await db.update_event_fields(
                                        event.reference,
                                        {'terminado': api_terminado, 'cancelado': api_cancelado, 'ativo': False, 'lance_atual': final_price}
                                    )
                                    await cache_manager.invalidate(event.reference)
                                    terminated_count += 1

                                    status_icon = "🚫" if api_cancelado else "✅"
                                    status_text = "Cancelado" if api_cancelado else "Vendido"
                                    print(f"    {status_icon} {status_text}: {event.reference} - {final_price}€")
                                else:
                                    # Not found in API - mark as cancelled
                                    await db.update_event_fields(
                                        event.reference,
                                        {'terminado': True, 'cancelado': True, 'ativo': False}
                                    )
                                    await cache_manager.invalidate(event.reference)
                                    terminated_count += 1
                                    print(f"    🚫 Removido: {event.reference}")

                        except Exception as e:
                            print(f"    ⚠️ Error processing expired {event.reference}: {e}")

                    if terminated_count > 0:
                        print(f"  ✅ X-Monitor: {terminated_count} eventos marcados como terminados")

                # Update pipeline stats
                pipeline = self.pipelines['xmonitor']
                now = datetime.now()
                pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                pipeline.runs_count += 1
                self._save_config()

            finally:
                await scraper.close()
                self.pipelines['xmonitor'].is_running = False
                # Reschedule with adaptive interval (updates next_run)
                self._reschedule_xmonitor(next_interval_seconds)
                # Save to database AFTER reschedule so next_run is correct
                await self.save_to_database('xmonitor')

        async def run_ysync_pipeline():
            """Y-Sync: Sincroniza novos IDs e marca eventos terminados"""
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager
            from pipeline_state import get_pipeline_state

            scraper = None
            cache_manager = None
            skipped = False
            lock_acquired = False

            try:
                # Skip if main pipeline is running
                main_pipeline = get_pipeline_state()
                if main_pipeline.is_active:
                    print(f"⏸️ Y-Sync skipped - main pipeline is running")
                    # Update next_run to avoid constant retries (retry in 5 min)
                    pipeline = self.pipelines['ysync']
                    pipeline.next_run = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    skipped = True
                    return

                # Try to acquire heavy pipeline lock (mutex with Z-Watch, Pipeline API)
                lock_acquired = await self.acquire_heavy_lock("Y-Sync")
                if not lock_acquired:
                    # Update next_run to avoid constant retries (retry in 2 min)
                    pipeline = self.pipelines['ysync']
                    pipeline.next_run = (datetime.now() + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    skipped = True
                    return

                # Mark as running
                self.pipelines['ysync'].is_running = True
                self._save_config()
                await self.save_to_database('ysync')

                print(f"🔄 Y-Sync: A iniciar sincronização completa...")

                scraper = EventScraper()
                cache_manager = CacheManager()
                new_ids_count = 0
                terminated_count = 0

                # Stage 1: Discover ALL IDs (full scan, no page limit)
                print(f"  🔍 Stage 1: A descobrir TODOS os IDs...")
                # Use run_in_proactor for Windows compatibility (SelectorEventLoop doesn't support subprocesses)
                ids = await run_in_proactor(scraper.scrape_ids_only, tipo=None, max_pages=None)
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
                    events = await run_in_proactor(scraper.scrape_details_via_api, new_refs)

                    # Process notifications for new events
                    from notification_engine import process_new_events_batch
                    from main import broadcast_new_event
                    notifications_count = 0

                    async with get_db() as db:
                        for event in events:
                            await db.save_event(event)
                            await cache_manager.set(event.reference, event)
                            new_ids_count += 1

                            # Broadcast new event to SSE clients
                            await broadcast_new_event({
                                "reference": event.reference,
                                "titulo": event.titulo,
                                "tipo": event.tipo,
                                "capa": event.capa,
                                "distrito": event.distrito,
                                "concelho": event.concelho,
                                "valor_minimo": event.valor_minimo,
                                "lance_atual": event.lance_atual,
                                "valor_base": event.valor_base,
                                "data_fim": event.data_fim.isoformat() if event.data_fim else None,
                                "data_inicio": event.data_inicio.isoformat() if event.data_inicio else None,
                                "timestamp": datetime.now().isoformat()
                            })

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
                    # Get active events (not cancelled AND still active)
                    events, total = await db.list_events(limit=500, cancelado=False, ativo=True)

                    candidates = []
                    for event in events:
                        if event.data_fim and event.data_fim < now:
                            candidates.append(event)

                    if candidates:
                        print(f"    📋 {len(candidates)} candidatos a terminado")

                        # OPTIMIZED: Batch API call instead of one-by-one
                        refs = [e.reference for e in candidates]
                        api_results = await run_in_proactor(scraper.scrape_volatile_via_api, refs)

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
                                        await record_price_change(event.reference, new_price, old_price, source='ysync')
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
                                        # Use API values for terminado/cancelado
                                        api_terminado = data.get('terminado', True)
                                        api_cancelado = data.get('cancelado', False)

                                        # Only update specific fields, not full save
                                        await db.update_event_fields(
                                            event.reference,
                                            {'terminado': api_terminado, 'cancelado': api_cancelado, 'ativo': False, 'lance_atual': new_price or old_price}
                                        )
                                        await cache_manager.invalidate(event.reference)
                                        terminated_count += 1
                                        status_icon = "🚫" if api_cancelado else "✅"
                                        status_text = "Cancelado" if api_cancelado else "Vendido"
                                        print(f"    {status_icon} {status_text}: {event.reference}")

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
                                    # Not in API results = likely removed/cancelled
                                    await db.update_event_fields(
                                        event.reference,
                                        {'terminado': True, 'cancelado': True, 'ativo': False}
                                    )
                                    await cache_manager.invalidate(event.reference)
                                    terminated_count += 1
                                    print(f"    🚫 Removido da API: {event.reference}")

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
                # Close resources safely (don't let errors here block the rest)
                try:
                    if scraper:
                        await run_in_proactor(scraper.close)
                except:
                    pass
                try:
                    if cache_manager:
                        await cache_manager.close()
                except:
                    pass

                # ALWAYS reset is_running if we started (not skipped)
                if not skipped:
                    self.pipelines['ysync'].is_running = False
                    pipeline = self.pipelines['ysync']
                    now = datetime.now()
                    pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                    pipeline.runs_count += 1
                    pipeline.next_run = (now + timedelta(hours=pipeline.interval_hours)).strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    print(f"  ⏰ Y-Sync: próxima execução em {pipeline.interval_hours}h")

                # Release heavy pipeline lock
                if lock_acquired:
                    self.release_heavy_lock("Y-Sync")

                # ALWAYS reschedule - even if skipped
                self._reschedule_pipeline('ysync')

                # Save to database AFTER reschedule so next_run is correct
                if not skipped:
                    await self.save_to_database('ysync')

        async def run_zwatch_pipeline():
            """Z-Watch: Monitoriza EventosMaisRecentes API para novos eventos"""
            import httpx
            from scraper import EventScraper
            from database import get_db
            from cache import CacheManager
            from pipeline_state import get_pipeline_state

            # Check if pipeline exists
            if 'zwatch' not in self.pipelines:
                return

            scraper = None
            cache_manager = None
            skipped = False
            lock_acquired = False

            try:
                # Skip if main pipeline is running
                main_pipeline = get_pipeline_state()
                if main_pipeline.is_active:
                    print(f"⏸️ Z-Watch skipped - main pipeline is running")
                    # Update next_run to avoid constant retries (retry in 5 min)
                    pipeline = self.pipelines['zwatch']
                    pipeline.next_run = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    skipped = True
                    return

                # Try to acquire heavy pipeline lock (mutex with Y-Sync, Pipeline API)
                lock_acquired = await self.acquire_heavy_lock("Z-Watch")
                if not lock_acquired:
                    # Update next_run to avoid constant retries (retry in 2 min)
                    pipeline = self.pipelines['zwatch']
                    pipeline.next_run = (datetime.now() + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    skipped = True
                    return

                # Mark as running
                self.pipelines['zwatch'].is_running = True
                self._save_config()
                await self.save_to_database('zwatch')

                print(f"👁️ Z-Watch: A verificar EventosMaisRecentes...")

                scraper = EventScraper()
                cache_manager = CacheManager()
                new_count = 0

                # Call the EventosMaisRecentes API
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                    api_url = "https://www.e-leiloes.pt/api/EventosMaisRecentes/"

                    # Try with browser-like headers
                    headers = {
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Referer': 'https://www.e-leiloes.pt/',
                        'Origin': 'https://www.e-leiloes.pt'
                    }

                    response = await client.get(api_url, headers=headers)

                    if response.status_code != 200:
                        print(f"  ⚠️ EventosMaisRecentes API returned {response.status_code}")
                        return

                    data = response.json()

                    # The API returns a list of recent events
                    events_list = data if isinstance(data, list) else data.get('items', data.get('eventos', []))

                    if not events_list:
                        print(f"  ✓ Nenhum evento na resposta")
                        return

                    print(f"  📊 {len(events_list)} eventos na API")

                    # Extract references and check which are new
                    new_refs = []
                    async with get_db() as db:
                        for item in events_list:
                            # Try different field names for reference
                            ref = item.get('reference') or item.get('referencia') or item.get('id') or item.get('codigo')
                            if ref:
                                existing = await db.get_event(ref)
                                if not existing:
                                    new_refs.append(ref)

                    if not new_refs:
                        print(f"  ✓ Nenhum evento novo")
                        return

                    print(f"  🆕 {len(new_refs)} eventos novos encontrados!")

                    # Scrape details for new events (use run_in_proactor for Windows)
                    events = await run_in_proactor(scraper.scrape_details_via_api, new_refs)

                    # Process notifications for new events
                    from notification_engine import process_new_events_batch
                    from main import broadcast_new_event

                    async with get_db() as db:
                        for event in events:
                            await db.save_event(event)
                            await cache_manager.set(event.reference, event)
                            new_count += 1

                            # Broadcast new event to SSE clients
                            await broadcast_new_event({
                                "reference": event.reference,
                                "titulo": event.titulo,
                                "tipo": event.tipo,
                                "capa": event.capa,
                                "distrito": event.distrito,
                                "concelho": event.concelho,
                                "valor_minimo": event.valor_minimo,
                                "lance_atual": event.lance_atual,
                                "valor_base": event.valor_base,
                                "data_fim": event.data_fim.isoformat() if event.data_fim else None,
                                "data_inicio": event.data_inicio.isoformat() if event.data_inicio else None,
                                "timestamp": datetime.now().isoformat()
                            })

                            print(f"    ✨ Novo: {event.reference} - {event.titulo[:50]}...")

                        # Check notification rules for new events
                        notifications_count = await process_new_events_batch(events, db)

                        if notifications_count > 0:
                            print(f"  🔔 {notifications_count} notificações criadas")

                    print(f"  ✅ Z-Watch: {new_count} novos eventos adicionados")

            except httpx.RequestError as e:
                print(f"  ❌ Z-Watch erro de rede: {str(e)[:50]}")
            except Exception as e:
                print(f"  ❌ Z-Watch erro: {str(e)[:100]}")
            finally:
                # Close resources safely (don't let errors here block the rest)
                try:
                    if scraper:
                        await run_in_proactor(scraper.close)
                except:
                    pass
                try:
                    if cache_manager:
                        await cache_manager.close()
                except:
                    pass

                # ALWAYS reset is_running if we started (not skipped)
                if not skipped:
                    self.pipelines['zwatch'].is_running = False
                    pipeline = self.pipelines['zwatch']
                    now = datetime.now()
                    pipeline.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                    pipeline.runs_count += 1
                    pipeline.next_run = (now + timedelta(hours=pipeline.interval_hours)).strftime("%Y-%m-%d %H:%M:%S")
                    self._save_config()
                    print(f"  ⏰ Z-Watch: próxima execução em {pipeline.interval_hours * 60:.0f} min")

                # Release heavy pipeline lock
                if lock_acquired:
                    self.release_heavy_lock("Z-Watch")

                # ALWAYS reschedule - even if skipped
                self._reschedule_pipeline('zwatch')

                # Save to database AFTER reschedule so next_run is correct
                if not skipped:
                    await self.save_to_database('zwatch')

        # Return the appropriate function
        tasks = {
            "xmonitor": run_xmonitor_pipeline,
            "ysync": run_ysync_pipeline,
            "zwatch": run_zwatch_pipeline,
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
