"""
E-Leiloes Data API - FastAPI Backend
Recolhe e serve dados dos leilões do e-leiloes.pt
"""

import sys
import asyncio

# Fix para Windows - asyncio subprocess com Playwright
# CRÍTICO: WindowsProactorEventLoopPolicy suporta subprocessos
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# CRITICAL: Load .env BEFORE importing database!
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import List, Optional, Set
import os
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from models import EventData, EventListResponse, ScraperStatus, ValoresLeilao
from database import init_db, get_db
from scraper import EventScraper
from cache import CacheManager
from pipeline_state import get_pipeline_state
from auto_pipelines import get_auto_pipelines_manager
from collections import deque
import threading

# Global instances
scraper = None
cache_manager = None
scheduler = None
scheduled_job_id = None

# SSE: Set of queues for broadcasting price updates to connected clients
sse_clients: Set[asyncio.Queue] = set()

# Logging system for dashboard console
log_buffer = deque(maxlen=100)  # Circular buffer, keeps last 100 logs
log_lock = threading.Lock()

def add_dashboard_log(message: str, level: str = "info"):
    """Adiciona um log ao buffer para o dashboard console"""
    with log_lock:
        log_buffer.append({
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        })


async def broadcast_price_update(event_data: dict):
    """Broadcast a price update to all connected SSE clients"""
    dead_clients = set()
    for queue in sse_clients:
        try:
            await queue.put(event_data)
        except:
            dead_clients.add(queue)

    # Remove disconnected clients
    for client in dead_clients:
        sse_clients.discard(client)


def get_sse_clients():
    """Get the SSE clients set (for use in auto_pipelines)"""
    return sse_clients


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown da aplicação"""
    global scraper, cache_manager, scheduler

    # CRITICAL: Set Windows event loop policy for Playwright subprocess support
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Startup
    print("🚀 Iniciando E-Leiloes API...")
    await init_db()

    # Clear pipeline state on startup (clean slate)
    pipeline_state = get_pipeline_state()
    await pipeline_state.stop()
    print("🧹 Pipeline state limpo")

    scraper = EventScraper()
    cache_manager = CacheManager()

    # Inicializa scheduler para agendamento
    scheduler = AsyncIOScheduler()
    scheduler.start()
    print("⏰ Scheduler iniciado")

    # Auto-start enabled pipelines
    from auto_pipelines import get_auto_pipelines_manager
    pipelines_manager = get_auto_pipelines_manager()
    enabled_count = 0
    for pipeline_type, pipeline in pipelines_manager.pipelines.items():
        if pipeline.enabled:
            await pipelines_manager._schedule_pipeline(pipeline_type, scheduler)
            enabled_count += 1
            print(f"  ▶️ Auto-started: {pipeline.name}")
    if enabled_count > 0:
        print(f"🔄 {enabled_count} pipeline(s) auto-started from saved config")

    print("✅ API pronta!")

    yield

    # Shutdown
    print("👋 Encerrando API...")
    if scheduler:
        scheduler.shutdown()
    if scraper:
        await scraper.close()
    if cache_manager:
        await cache_manager.close()

app = FastAPI(
    title="E-Leiloes Data API",
    description="API para recolha e consulta de dados de leilões do e-leiloes.pt",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============== ENDPOINTS ==============

@app.get("/")
async def root():
    """Redireciona para a dashboard"""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "online",
        "service": "E-Leiloes Data API",
        "version": "1.0.0"
    }


@app.get("/api/pipeline/status")
async def get_pipeline_status():
    """Get current pipeline state for real-time feedback"""
    pipeline_state = get_pipeline_state()
    state = await pipeline_state.get_state()
    return JSONResponse(state)


@app.post("/api/pipeline/kill")
async def kill_pipeline():
    """
    KILL SWITCH: Para imediatamente qualquer pipeline em execução.

    Limpa o estado da pipeline e sinaliza paragem ao scraper.
    """
    pipeline_state = get_pipeline_state()

    # Get current state before killing
    state = await pipeline_state.get_state()
    was_active = state.get("active", False)
    stage = state.get("stage")
    stage_name = state.get("stage_name")

    # Stop the scraper - ALWAYS set the flag regardless of is_running
    if scraper:
        scraper.stop_requested = True
        print("🛑 Scraper stop_requested = True")

    # Clear pipeline state
    await pipeline_state.stop()

    add_dashboard_log("🛑 Pipeline KILLED pelo utilizador", "warning")

    return {
        "success": True,
        "message": "Pipeline terminada com sucesso",
        "was_active": was_active,
        "killed_stage": stage,
        "killed_stage_name": stage_name
    }


@app.post("/api/pipeline/test")
async def test_pipeline_feedback(
    items: int = Query(10, description="Número de itens para simular"),
    stage: int = Query(2, description="Stage para simular (1, 2, ou 3)")
):
    """
    TEST ENDPOINT: Simula uma pipeline em execução para testar o feedback.
    Útil para testar o sistema sem precisar do Playwright.
    """
    pipeline_state = get_pipeline_state()

    stage_names = {
        1: "Stage 1 - IDs (Test)",
        2: "Stage 2 - Detalhes (Test)",
        3: "Stage 3 - Imagens (Test)"
    }

    try:
        # Iniciar pipeline
        await pipeline_state.start(
            stage=stage,
            stage_name=stage_names.get(stage, "Test Stage"),
            total=items,
            details={"test": True}
        )

        # Simular processamento
        for i in range(1, items + 1):
            await asyncio.sleep(0.5)  # Simular tempo de processamento

            await pipeline_state.update(
                current=i,
                message=f"Processando item {i}/{items} - TEST-{i:04d}"
            )

        # Completar
        await pipeline_state.complete(
            message=f"✅ Test concluído! {items} itens processados"
        )

        # Parar após delay
        await asyncio.sleep(2)
        await pipeline_state.stop()

        return {
            "success": True,
            "message": f"Test pipeline concluída: {items} itens em stage {stage}",
            "stage": stage,
            "items": items
        }

    except Exception as e:
        await pipeline_state.add_error(str(e))
        await pipeline_state.stop()
        raise HTTPException(status_code=500, detail=str(e))


# ============== AUTOMATIC PIPELINES ENDPOINTS ==============

@app.get("/api/auto-pipelines/status")
async def get_auto_pipelines_status():
    """Get status of all automatic pipelines"""
    auto_pipelines = get_auto_pipelines_manager()
    return JSONResponse(auto_pipelines.get_status())


@app.post("/api/auto-pipelines/{pipeline_type}/toggle")
async def toggle_auto_pipeline(
    pipeline_type: str,
    enabled: bool = Query(..., description="Enable or disable the pipeline")
):
    """
    Enable or disable an automatic pipeline.

    - **pipeline_type**: Type of pipeline (full, prices, info)
    - **enabled**: True to enable, False to disable

    Returns pipeline configuration and next run time if enabled.
    """
    auto_pipelines = get_auto_pipelines_manager()

    try:
        result = await auto_pipelines.toggle_pipeline(
            pipeline_type=pipeline_type,
            enabled=enabled,
            scheduler=scheduler
        )

        add_dashboard_log(
            f"{'🟢 Ativada' if enabled else '🔴 Desativada'} pipeline automática: {pipeline_type}",
            "info"
        )

        return JSONResponse(result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao alterar pipeline: {str(e)}")


@app.get("/api/auto-pipelines/prices/cache-info")
async def get_prices_cache_info():
    """Get Pipeline X cache information (number of cached events)"""
    auto_pipelines = get_auto_pipelines_manager()

    cache_count = len(auto_pipelines._critical_events_cache)
    last_refresh = auto_pipelines._cache_last_refresh

    return JSONResponse({
        "cached_events": cache_count,
        "last_refresh": last_refresh.strftime("%Y-%m-%d %H:%M:%S") if last_refresh else None
    })


# ============== END AUTOMATIC PIPELINES ENDPOINTS ==============


@app.get("/api/events/{reference}", response_model=EventData)
async def get_event(reference: str):
    """
    Obtém dados de um evento específico por referência.
    
    - **reference**: Referência do evento (ex: NP-2024-12345 ou LO-2024-67890)
    
    Retorna dados completos incluindo GPS, áreas, tipo, etc.
    """
    # Verifica cache primeiro
    cached = await cache_manager.get(reference)
    if cached:
        return cached
    
    # Verifica base de dados
    async with get_db() as db:
        event = await db.get_event(reference)
        if event:
            await cache_manager.set(reference, event)
            return event
    
    # Se não existe, faz scraping
    try:
        event_data = await scraper.scrape_event(reference)
        
        # Guarda na BD
        async with get_db() as db:
            await db.save_event(event_data)
        
        # Guarda no cache
        await cache_manager.set(reference, event_data)
        
        return event_data
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Evento não encontrado: {str(e)}")


@app.get("/api/events", response_model=EventListResponse)
async def get_events(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(50, ge=1, le=100000, description="Eventos por página"),
    tipo: Optional[str] = None,
    tipo_evento: Optional[str] = None,
    distrito: Optional[str] = None
):
    """
    Lista eventos com paginação e filtros.

    - **page**: Número da página (começa em 1)
    - **limit**: Quantidade de resultados por página (max 100000)
    - **tipo**: Filtrar por tipo (Apartamento, Moradia, etc)
    - **tipo_evento**: Filtrar por tipo de evento (imovel, movel)
    - **distrito**: Filtrar por distrito
    """
    async with get_db() as db:
        events, total = await db.list_events(
            page=page,
            limit=limit,
            tipo=tipo,
            tipo_evento=tipo_evento,
            distrito=distrito
        )
        
        return EventListResponse(
            events=events,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )


@app.post("/api/scrape/event/{reference}")
async def trigger_scrape_event(reference: str, background_tasks: BackgroundTasks):
    """
    Força re-scraping de um evento específico (atualiza cache).
    Executa em background.
    """
    background_tasks.add_task(scrape_and_update, reference)
    
    return {
        "message": f"Scraping do evento {reference} iniciado em background",
        "reference": reference
    }


@app.post("/api/scrape/all")
async def trigger_scrape_all(
    background_tasks: BackgroundTasks,
    max_pages: int = Query(None, description="Máximo de páginas para scrape (None = todas)")
):
    """
    Inicia scraping de TODOS os eventos (pode demorar horas).
    Executa em background.
    
    ⚠️ Use com cuidado! Pode gerar muitas requests.
    """
    background_tasks.add_task(scrape_all_events, max_pages)
    
    return {
        "message": "Scraping total iniciado em background",
        "max_pages": max_pages or "todas"
    }


@app.get("/api/scrape/status", response_model=ScraperStatus)
async def get_scraper_status():
    """
    Retorna status atual do scraper (eventos processados, erros, etc).
    """
    return scraper.get_status()


@app.post("/api/scrape/stop")
async def stop_scraper():
    """
    Para o scraping em execução.

    Se o scraper estiver a correr, solicita a paragem graceful.
    """
    if not scraper.is_running:
        raise HTTPException(
            status_code=400,
            detail="Scraper não está em execução"
        )

    scraper.stop()

    return {
        "message": "Paragem do scraper solicitada",
        "status": "stopping"
    }


@app.post("/api/scrape/schedule")
async def schedule_scraping(hours: int = Query(..., ge=1, le=24, description="Intervalo em horas (1-24)")):
    """
    Agenda scraping automático a cada X horas.

    - **hours**: Intervalo em horas (1, 3, 6, 12, 24)

    Remove agendamento anterior se existir.
    """
    global scheduled_job_id

    # Remove job anterior se existir
    if scheduled_job_id and scheduler.get_job(scheduled_job_id):
        scheduler.remove_job(scheduled_job_id)
        print(f"🗑️ Agendamento anterior removido")

    # Cria novo job
    trigger = IntervalTrigger(hours=hours)
    job = scheduler.add_job(
        scheduled_scrape_task,
        trigger=trigger,
        id=f"scrape_every_{hours}h",
        name=f"Scraping a cada {hours}h",
        replace_existing=True
    )

    scheduled_job_id = job.id
    next_run = job.next_run_time

    print(f"⏰ Scraping agendado a cada {hours}h. Próxima execução: {next_run}")

    return {
        "message": f"Scraping agendado a cada {hours} hora(s)",
        "interval_hours": hours,
        "next_run": next_run.isoformat() if next_run else None,
        "job_id": scheduled_job_id
    }


@app.delete("/api/scrape/schedule")
async def cancel_scheduled_scraping():
    """
    Cancela o agendamento automático de scraping.
    """
    global scheduled_job_id

    if not scheduled_job_id:
        raise HTTPException(
            status_code=404,
            detail="Não existe agendamento ativo"
        )

    job = scheduler.get_job(scheduled_job_id)
    if not job:
        scheduled_job_id = None
        raise HTTPException(
            status_code=404,
            detail="Job de agendamento não encontrado"
        )

    scheduler.remove_job(scheduled_job_id)
    print(f"🗑️ Agendamento '{scheduled_job_id}' cancelado")
    scheduled_job_id = None

    return {
        "message": "Agendamento cancelado com sucesso"
    }


@app.get("/api/scrape/schedule")
async def get_schedule_info():
    """
    Retorna informação sobre o agendamento ativo (se existir).
    """
    global scheduled_job_id

    if not scheduled_job_id:
        return {
            "scheduled": False,
            "interval_hours": None,
            "next_run": None
        }

    job = scheduler.get_job(scheduled_job_id)
    if not job:
        scheduled_job_id = None
        return {
            "scheduled": False,
            "interval_hours": None,
            "next_run": None
        }

    # Extrai intervalo do trigger
    interval_hours = None
    if hasattr(job.trigger, 'interval'):
        interval_seconds = job.trigger.interval.total_seconds()
        interval_hours = int(interval_seconds / 3600)

    return {
        "scheduled": True,
        "interval_hours": interval_hours,
        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        "job_id": job.id
    }


# ============== MULTI-STAGE SCRAPING ENDPOINTS ==============

@app.post("/api/scrape/stage1/ids")
async def scrape_stage1_ids(
    tipo: Optional[int] = Query(None, ge=1, le=6, description="1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos"),
    max_pages: Optional[int] = Query(None, ge=1, description="Máximo de páginas por tipo"),
    save_to_db: bool = Query(True, description="Guardar na base de dados")
):
    """
    STAGE 1: Scrape apenas IDs e valores básicos da listagem (rápido).

    AGORA COM INSERÇÃO NA BD: Guarda eventos básicos na BD com referência e valores.

    - **tipo**: 1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos
    - **max_pages**: Máximo de páginas por tipo
    - **save_to_db**: Se True, guarda eventos na BD (default: True)

    Retorna lista de IDs com valores básicos.
    Ideal para descobrir rapidamente o que existe e popular a BD.
    """
    pipeline_state = get_pipeline_state()

    try:
        add_dashboard_log("🔍 STAGE 1: A obter IDs...", "info")

        # Iniciar pipeline state
        tipo_str = "Imóveis" if tipo == 1 else "Móveis" if tipo == 2 else "Todos"
        await pipeline_state.start(
            stage=1,
            stage_name=f"Stage 1 - IDs ({tipo_str})",
            total=0,  # Será atualizado conforme scraping
            details={"tipo": tipo, "max_pages": max_pages}
        )

        ids = await scraper.scrape_ids_only(tipo=tipo, max_pages=max_pages)

        # Atualizar total após scraping
        await pipeline_state.update(total=len(ids), message=f"{len(ids)} IDs recolhidos")

        # Guardar na BD se solicitado
        saved_count = 0
        if save_to_db:
            await pipeline_state.update(message=f"Guardando {len(ids)} eventos na BD...")

            async with get_db() as db:
                for idx, item in enumerate(ids, 1):
                    try:
                        # Cria evento básico com apenas referência e valores
                        from models import EventDetails

                        event = EventData(
                            reference=item['reference'],
                            tipoEvento=item.get('tipo', 'imovel'),
                            valores=item.get('valores', ValoresLeilao()),
                            detalhes=EventDetails(
                                tipo=item.get('tipo', 'N/A'),
                                subtipo='N/A'
                            ),
                            # Campos vazios serão preenchidos no Stage 2
                            descricao=None,
                            observacoes=None,
                            imagens=[]
                        )

                        await db.save_event(event)
                        await cache_manager.set(event.reference, event)
                        saved_count += 1

                        # Atualizar progresso
                        await pipeline_state.update(
                            current=idx,
                            message=f"Guardando {idx}/{len(ids)} - {item['reference']}"
                        )

                    except Exception as e:
                        print(f"  ⚠️ Erro ao guardar {item['reference']}: {e}")
                        await pipeline_state.add_error(f"Erro ao guardar {item['reference']}: {e}")
                        continue

            add_dashboard_log(f"💾 {saved_count} eventos guardados na BD", "success")

        add_dashboard_log(f"✅ Stage 1 completo: {len(ids)} IDs recolhidos", "success")

        # Marcar como completo
        await pipeline_state.complete(
            message=f"✅ {len(ids)} IDs recolhidos{', ' + str(saved_count) + ' guardados' if save_to_db else ''}"
        )

        # Parar pipeline após pequeno delay para UI mostrar
        await asyncio.sleep(2)
        await pipeline_state.stop()

        return {
            "stage": 1,
            "total_ids": len(ids),
            "saved_to_db": saved_count if save_to_db else 0,
            "ids": ids,
            "message": f"Stage 1 completo: {len(ids)} IDs recolhidos{', ' + str(saved_count) + ' guardados na BD' if save_to_db else ''}"
        }

    except Exception as e:
        msg = f"❌ Erro no Stage 1: {str(e)}"
        add_dashboard_log(msg, "error")
        await pipeline_state.add_error(msg)
        await pipeline_state.stop()
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/scrape/smart/new-events")
async def scrape_smart_new_events(
    tipo: Optional[int] = Query(None, ge=1, le=6, description="1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos"),
    max_pages: Optional[int] = Query(None, ge=1, description="Máximo de páginas por tipo")
):
    """
    SCRAPE INTELIGENTE: Identifica automaticamente eventos novos.

    Compara IDs scraped com os já existentes na BD e retorna apenas os novos.

    - **tipo**: 1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos
    - **max_pages**: Máximo de páginas por tipo

    Retorna apenas IDs de eventos que ainda não estão na base de dados.
    """
    try:
        add_dashboard_log("🧠 SCRAPE INTELIGENTE: A identificar eventos novos...", "info")

        # 1. Scrape todos os IDs disponíveis
        all_ids_data = await scraper.scrape_ids_only(tipo=tipo, max_pages=max_pages)
        all_references = [item['reference'] for item in all_ids_data]
        add_dashboard_log(f"📊 Total de eventos encontrados: {len(all_references)}", "info")

        # 2. Obter IDs já existentes na BD
        async with get_db() as db:
            existing_references = await db.get_all_references()

        existing_set = set(existing_references)
        add_dashboard_log(f"💾 Eventos já na BD: {len(existing_references)}", "info")

        # 3. Identificar novos eventos
        new_ids_data = [item for item in all_ids_data if item['reference'] not in existing_set]
        new_count = len(new_ids_data)

        if new_count > 0:
            add_dashboard_log(f"✨ {new_count} eventos novos identificados!", "success")
        else:
            add_dashboard_log("✅ Nenhum evento novo. BD está atualizada.", "success")

        return {
            "total_scraped": len(all_references),
            "already_in_db": len(existing_references),
            "new_events": new_count,
            "new_ids": new_ids_data,
            "message": f"Smart Scraping: {new_count} eventos novos de {len(all_references)} totais"
        }

    except Exception as e:
        msg = f"❌ Erro no scrape inteligente: {str(e)}"
        add_dashboard_log(msg, "error")
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/scrape/stage2/details")
async def scrape_stage2_details(
    references: List[str] = Query(..., description="Lista de referências para scrape"),
    save_to_db: bool = Query(True, description="Guardar na base de dados")
):
    """
    STAGE 2: Scrape detalhes completos (SEM imagens) para lista de IDs.

    INSERÇÃO EM TEMPO REAL: Cada evento é guardado na BD assim que é scraped.

    - **references**: Lista de referências (ex: ["LO-2024-001", "NP-2024-002"])
    - **save_to_db**: Se True, guarda eventos na BD em tempo real

    Retorna eventos com todos os detalhes exceto imagens.
    """
    pipeline_state = get_pipeline_state()
    scraped_count = 0

    try:
        # Iniciar pipeline state
        await pipeline_state.start(
            stage=2,
            stage_name="Stage 2 - Detalhes",
            total=len(references),
            details={"save_to_db": save_to_db}
        )

        # Callback para inserir cada evento assim que é scraped (TEMPO REAL)
        async def save_event_callback(event: EventData):
            """Salva evento na BD em tempo real"""
            nonlocal scraped_count
            scraped_count += 1

            async with get_db() as db:
                await db.save_event(event)
                await cache_manager.set(event.reference, event)
                print(f"  💾 {event.reference} guardado em tempo real")

            # Atualizar progresso da pipeline
            await pipeline_state.update(
                current=scraped_count,
                message=f"Scraping {scraped_count}/{len(references)} - {event.reference}"
            )

        # Se save_to_db=True, passa callback; senão, None
        callback = save_event_callback if save_to_db else None
        events = await scraper.scrape_details_by_ids(references, on_event_scraped=callback)

        # Marcar como completo
        await pipeline_state.complete(
            message=f"✅ {len(events)} eventos processados{' e guardados' if save_to_db else ''}"
        )

        # Parar pipeline após pequeno delay para UI mostrar
        await asyncio.sleep(2)
        await pipeline_state.stop()

        return {
            "stage": 2,
            "total_requested": len(references),
            "total_scraped": len(events),
            "events": [event.model_dump() for event in events],
            "saved_to_db": save_to_db,
            "message": f"Stage 2 completo: {len(events)} eventos processados {'e guardados em tempo real' if save_to_db else ''}"
        }

    except Exception as e:
        msg = f"Erro no Stage 2: {str(e)}"
        await pipeline_state.add_error(msg)
        await pipeline_state.stop()
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/scrape/stage3/images")
async def scrape_stage3_images(
    references: List[str] = Query(..., description="Lista de referências para scrape"),
    update_db: bool = Query(True, description="Atualizar eventos na BD com imagens")
):
    """
    STAGE 3: Scrape apenas imagens para lista de IDs.

    - **references**: Lista de referências
    - **update_db**: Se True, atualiza eventos existentes na BD com imagens

    Retorna mapa {reference: [image_urls]}.
    """
    pipeline_state = get_pipeline_state()
    progress_counter = {"count": 0}

    try:
        # Iniciar pipeline state
        await pipeline_state.start(
            stage=3,
            stage_name="Stage 3 - Imagens",
            total=len(references),
            details={"update_db": update_db}
        )

        # Callback para atualizar progresso durante o scraping
        async def on_images_progress(ref: str, images: List[str]):
            progress_counter["count"] += 1
            await pipeline_state.update(
                current=progress_counter["count"],
                message=f"Scraping {progress_counter['count']}/{len(references)} - {ref} ({len(images)} imagens)"
            )

        images_map = await scraper.scrape_images_by_ids(references, on_images_scraped=on_images_progress)

        # Atualiza eventos na BD se solicitado
        updated_count = 0
        if update_db:
            await pipeline_state.update(message=f"Atualizando {len(images_map)} eventos na BD...")

            async with get_db() as db:
                for idx, (ref, images) in enumerate(images_map.items(), 1):
                    # Busca evento existente
                    event = await db.get_event(ref)
                    if event:
                        # Atualiza imagens
                        event.imagens = images
                        event.updated_at = datetime.utcnow()
                        await db.save_event(event)
                        await cache_manager.set(ref, event)
                        updated_count += 1

                        # Atualizar progresso
                        await pipeline_state.update(
                            current=idx,
                            message=f"Atualizando {idx}/{len(images_map)} - {ref} ({len(images)} imagens)"
                        )

        # Marcar como completo
        await pipeline_state.complete(
            message=f"✅ {len(images_map)} eventos processados{', ' + str(updated_count) + ' atualizados' if update_db else ''}"
        )

        # Parar pipeline após pequeno delay para UI mostrar
        await asyncio.sleep(2)
        await pipeline_state.stop()

        return {
            "stage": 3,
            "total_requested": len(references),
            "total_scraped": len(images_map),
            "images_map": images_map,
            "updated_db": update_db,
            "message": f"Stage 3 completo: {len(images_map)} eventos processados"
        }

    except Exception as e:
        msg = f"Erro no Stage 3: {str(e)}"
        await pipeline_state.add_error(msg)
        await pipeline_state.stop()
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/scrape/pipeline")
async def scrape_full_pipeline(
    background_tasks: BackgroundTasks,
    tipo: Optional[int] = Query(None, ge=1, le=6, description="1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos"),
    max_pages: Optional[int] = Query(None, ge=1, description="Máximo de páginas por tipo")
):
    """
    PIPELINE COMPLETO: Executa os 3 stages sequencialmente em background.

    1. Stage 1: Scrape IDs (todos os 6 tipos)
    2. Stage 2: Scrape detalhes
    3. Stage 3: Scrape imagens

    Executa em background e guarda tudo na BD.
    """
    background_tasks.add_task(run_full_pipeline, tipo, max_pages)

    return {
        "message": "Pipeline completo iniciado em background",
        "stages": ["Stage 1: IDs", "Stage 2: Detalhes", "Stage 3: Imagens"],
        "tipo": tipo,
        "max_pages": max_pages
    }


@app.delete("/api/cache")
async def clear_cache():
    """
    Limpa todo o cache Redis (se configurado).
    """
    await cache_manager.clear_all()
    return {"message": "Cache limpo com sucesso"}


@app.delete("/api/database")
async def clear_database():
    """
    Apaga TODOS os eventos da base de dados.
    ATENÇÃO: Esta operação é irreversível!
    """
    async with get_db() as db:
        deleted = await db.delete_all_events()
    
    # Limpa também o cache
    await cache_manager.clear_all()
    
    return {
        "message": "Base de dados limpa com sucesso",
        "deleted_events": deleted
    }


@app.get("/api/database/check")
async def check_database():
    """
    Verifica integridade da base de dados: duplicados e estatísticas.
    """
    from sqlalchemy import func, select
    from database import EventDB

    async with get_db() as db:
        # Total de eventos
        result = await db.session.execute(
            select(func.count()).select_from(EventDB)
        )
        total = result.scalar()

        # Verificar duplicados por reference
        duplicates_result = await db.session.execute(
            select(EventDB.reference, func.count(EventDB.reference).label('cnt'))
            .group_by(EventDB.reference)
            .having(func.count(EventDB.reference) > 1)
        )
        duplicates = duplicates_result.fetchall()

        # Contar eventos únicos
        unique_result = await db.session.execute(
            select(func.count(func.distinct(EventDB.reference)))
        )
        unique_count = unique_result.scalar()

        return {
            "total_rows": total,
            "unique_references": unique_count,
            "duplicate_references": len(duplicates),
            "duplicates": [{"reference": ref, "count": cnt} for ref, cnt in duplicates[:20]]
        }


@app.post("/api/database/cleanup")
async def cleanup_database():
    """
    Remove eventos duplicados, mantendo apenas o mais recente.
    """
    from sqlalchemy import func, select
    from database import EventDB

    async with get_db() as db:
        # Encontrar duplicados
        duplicates_result = await db.session.execute(
            select(EventDB.reference, func.count(EventDB.reference).label('cnt'))
            .group_by(EventDB.reference)
            .having(func.count(EventDB.reference) > 1)
        )
        duplicates = duplicates_result.fetchall()

        removed_count = 0
        for ref, cnt in duplicates:
            # Buscar todos os eventos com este reference, ordenados por updated_at desc
            events_result = await db.session.execute(
                select(EventDB)
                .where(EventDB.reference == ref)
                .order_by(EventDB.updated_at.desc())
            )
            events = events_result.scalars().all()

            # Manter o primeiro (mais recente), remover os outros
            for event in events[1:]:
                await db.session.delete(event)
                removed_count += 1

        await db.session.commit()

        return {
            "message": f"Cleanup concluído: {removed_count} duplicados removidos",
            "duplicates_found": len(duplicates),
            "removed": removed_count
        }


@app.post("/api/database/migrate-tipos")
async def migrate_event_types():
    """
    Migra tipos de evento antigos para o novo formato.

    Conversões:
    - "imovel" -> "imoveis"
    - "movel" -> "veiculos"
    """
    from sqlalchemy import update, select, func
    from database import EventDB

    migrations = {
        "imovel": "imoveis",
        "movel": "veiculos"
    }

    async with get_db() as db:
        total_updated = 0
        details = []

        for old_type, new_type in migrations.items():
            # Contar quantos existem
            count_result = await db.session.execute(
                select(func.count()).select_from(EventDB).where(EventDB.tipo_evento == old_type)
            )
            count = count_result.scalar()

            if count > 0:
                # Atualizar
                await db.session.execute(
                    update(EventDB).where(EventDB.tipo_evento == old_type).values(tipo_evento=new_type)
                )
                total_updated += count
                details.append(f"{old_type} -> {new_type}: {count} eventos")

        await db.session.commit()

        # Estatísticas finais por tipo
        stats_result = await db.session.execute(
            select(EventDB.tipo_evento, func.count(EventDB.tipo_evento))
            .group_by(EventDB.tipo_evento)
        )
        stats = {tipo: count for tipo, count in stats_result.fetchall()}

        return {
            "message": f"Migração concluída: {total_updated} eventos atualizados",
            "migrations": details,
            "current_stats": stats
        }


@app.get("/api/stats")
async def get_stats():
    """
    Estatísticas gerais da base de dados.
    """
    async with get_db() as db:
        stats = await db.get_stats()
        return stats


@app.get("/api/logs")
async def get_logs():
    """
    Retorna os logs recentes do scraping e limpa o buffer.
    Este endpoint é chamado pelo dashboard console para mostrar logs em tempo real.
    """
    logs_to_return = []

    with log_lock:
        # Copy all logs
        logs_to_return = list(log_buffer)
        # Clear buffer after reading
        log_buffer.clear()

    return {"logs": logs_to_return}


# ============== BACKGROUND TASKS ==============

async def scrape_and_update(reference: str):
    """Scrape um evento e atualiza BD + cache"""
    try:
        event_data = await scraper.scrape_event(reference)
        
        async with get_db() as db:
            await db.save_event(event_data)
        
        await cache_manager.set(reference, event_data)
        
        print(f"✅ Evento {reference} atualizado")
    except Exception as e:
        print(f"❌ Erro ao atualizar {reference}: {e}")


async def scrape_all_events(max_pages: Optional[int] = None):
    """Scrape todos os eventos do site"""
    try:
        print(f"🚀 Iniciando scraping total (max_pages={max_pages})...")

        all_events = await scraper.scrape_all_events(max_pages=max_pages)

        async with get_db() as db:
            for event in all_events:
                await db.save_event(event)
                await cache_manager.set(event.reference, event)

        print(f"✅ Scraping total concluído: {len(all_events)} eventos")

    except Exception as e:
        print(f"❌ Erro no scraping total: {e}")


async def scheduled_scrape_task():
    """
    Task agendada para scraping automático.
    Usa a mesma lógica de scrape_all_events mas é chamada pelo scheduler.
    """
    if scraper.is_running:
        print("⚠️ Scraping já em execução. Pulando execução agendada.")
        return

    print(f"⏰ Iniciando scraping agendado às {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await scrape_all_events(max_pages=None)


async def run_full_pipeline(tipo: Optional[int], max_pages: Optional[int]):
    """
    Executa o pipeline completo de 3 stages em sequência.

    Stage 1: Scrape IDs → Stage 2: Scrape Detalhes → Stage 3: Scrape Imagens
    """
    pipeline_state = get_pipeline_state()

    try:
        # CRITICAL: Clean pipeline state at start
        await pipeline_state.stop()

        msg = f"🚀 Iniciando pipeline completo (tipo={tipo}, max_pages={max_pages})..."
        print(msg)
        add_dashboard_log(msg, "info")

        # ===== STAGE 1: Scrape IDs =====
        tipo_str = "Imóveis" if tipo == 1 else "Móveis" if tipo == 2 else "Todos"
        await pipeline_state.start(
            stage=1,
            stage_name=f"Stage 1 - IDs ({tipo_str})",
            total=6 if tipo is None else 1,  # Number of types to scrape
            details={"tipo": tipo, "max_pages": max_pages}
        )

        # Set initial message showing "Total: 0"
        await pipeline_state.update(
            current=0,
            total=0,
            message="Total: 0",
            details={"types_done": 0, "total_ids": 0, "breakdown": {}}
        )

        add_dashboard_log("🔍 STAGE 1: SCRAPING IDs", "info")

        # Callback to log progress as each type completes
        type_counter = {"count": 0}

        async def on_type_complete(tipo_nome: str, count: int, totals: dict):
            """Log when each type is complete"""
            type_counter["count"] += 1
            total_ids = sum(totals.values())

            # Build totals string: "Total: X | Imóveis: X | Veículos: X"
            totals_parts = [f"Total: {total_ids}"]
            tipo_names_map = {
                "imoveis": "Imóveis",
                "veiculos": "Veículos",
                "direitos": "Direitos",
                "equipamentos": "Equipamentos",
                "mobiliario": "Mobiliário",
                "maquinas": "Máquinas"
            }
            for tipo_key, tipo_count in totals.items():
                display_name = tipo_names_map.get(tipo_key, tipo_key)
                totals_parts.append(f"{display_name}: {tipo_count}")

            msg = " | ".join(totals_parts)
            add_dashboard_log(f"✓ {tipo_nome}: {count} IDs | {msg}", "info")

            # Update pipeline state - use total_ids for display
            await pipeline_state.update(
                current=total_ids,  # Show total IDs collected
                total=total_ids,    # Same value (we don't know final total)
                message=msg,
                details={"types_done": type_counter["count"], "total_ids": total_ids, "breakdown": totals}
            )

        # Check if scraper was stopped before starting
        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline cancelada antes de iniciar", "warning")
            await pipeline_state.stop()
            return

        ids_data = await scraper.scrape_ids_only(
            tipo=tipo,
            max_pages=max_pages,
            on_type_complete=on_type_complete
        )

        references = [item['reference'] for item in ids_data]

        # Check if stopped during scraping - but still report what we got
        if scraper.stop_requested:
            if len(references) > 0:
                msg = f"🛑 Pipeline interrompida - {len(references)} IDs recolhidos parcialmente"
                add_dashboard_log(msg, "warning")
                # Update state to show what we collected
                await pipeline_state.update(total=len(references), message=msg)
            else:
                add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False  # Reset flag
            return

        # Update total after scraping
        await pipeline_state.update(total=len(references), message=f"{len(references)} IDs recolhidos")
        await pipeline_state.complete(message=f"✅ Stage 1: {len(references)} IDs recolhidos")

        msg = f"✅ Stage 1: {len(references)} IDs recolhidos"
        print(msg)
        add_dashboard_log(msg, "success")

        if not references:
            msg = "⚠️ Nenhum ID encontrado. Pipeline terminado."
            print(msg)
            add_dashboard_log(msg, "warning")
            await asyncio.sleep(2)
            await pipeline_state.stop()
            return

        # ===== STAGE 2: Scrape Detalhes =====
        # Check if stopped
        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False
            return

        await pipeline_state.start(
            stage=2,
            stage_name="Stage 2 - Detalhes",
            total=len(references),
            details={"save_to_db": True}
        )

        add_dashboard_log("📋 STAGE 2: SCRAPING DETALHES", "info")

        # Counter for tracking progress
        scraped_count = 0

        # Callback para inserir cada evento assim que é scraped
        async def save_event_callback(event: EventData):
            """Salva evento na BD em tempo real"""
            nonlocal scraped_count
            scraped_count += 1

            async with get_db() as db:
                await db.save_event(event)
                await cache_manager.set(event.reference, event)

            # Update pipeline state in real-time
            await pipeline_state.update(
                current=scraped_count,
                message=f"Scraping {scraped_count}/{len(references)} - {event.reference}"
            )

        events = await scraper.scrape_details_by_ids(references, on_event_scraped=save_event_callback)

        # Check if stopped during scraping
        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False
            return

        await pipeline_state.complete(message=f"✅ Stage 2: {len(events)} eventos processados e salvos")

        msg = f"✅ Stage 2: {len(events)} eventos processados e salvos em tempo real"
        print(msg)
        add_dashboard_log(msg, "success")

        # ===== STAGE 3: Scrape Imagens =====
        # Check if stopped
        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False
            return

        await pipeline_state.start(
            stage=3,
            stage_name="Stage 3 - Imagens",
            total=len(references),
            details={"update_db": True}
        )

        add_dashboard_log("🖼️ STAGE 3: SCRAPING IMAGENS", "info")

        # Counter for tracking progress
        images_count = 0

        # Callback para atualizar imagens assim que são scraped
        async def update_images_callback(ref: str, images: List[str]):
            """Atualiza imagens do evento em tempo real"""
            nonlocal images_count
            images_count += 1

            async with get_db() as db:
                event = await db.get_event(ref)
                if event:
                    event.imagens = images
                    event.updated_at = datetime.utcnow()
                    await db.save_event(event)
                    await cache_manager.set(ref, event)

            # Update pipeline state in real-time
            await pipeline_state.update(
                current=images_count,
                message=f"Atualizando {images_count}/{len(references)} - {ref} ({len(images)} imagens)"
            )

        images_map = await scraper.scrape_images_by_ids(references, on_images_scraped=update_images_callback)

        # Check if stopped during scraping
        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False
            return

        await pipeline_state.complete(message=f"✅ Stage 3: {len(images_map)} eventos com imagens atualizadas")

        msg = f"✅ Stage 3: {len(images_map)} eventos com imagens atualizadas em tempo real"
        print(msg)
        add_dashboard_log(msg, "success")

        # Final message
        msg = f"🎉 PIPELINE COMPLETO! IDs: {len(references)} | Detalhes: {len(events)} | Imagens: {len(images_map)}"
        print(msg)
        add_dashboard_log(msg, "success")

        # Delay to show final message, then stop
        await asyncio.sleep(3)
        await pipeline_state.stop()

    except Exception as e:
        msg = f"❌ Erro no pipeline: {e}"
        print(msg)
        add_dashboard_log(msg, "error")
        await pipeline_state.add_error(msg)
        await asyncio.sleep(2)
        await pipeline_state.stop()


# ============== SSE & STREAMING ENDPOINTS ==============

@app.get("/api/events/stream")
async def stream_events(
    limit: int = Query(5000, ge=1, le=5000, description="Max events to stream"),
    tipo_evento: Optional[str] = None,
    distrito: Optional[str] = None
):
    """
    Stream events one by one for progressive loading.
    Each event is sent as a JSON line (NDJSON format).
    Frontend can render each card as it arrives.
    """
    async def event_generator():
        async with get_db() as db:
            events, total = await db.list_events(
                page=1,
                limit=limit,
                tipo_evento=tipo_evento,
                distrito=distrito
            )

            # First, send metadata
            yield json.dumps({"type": "meta", "total": total}) + "\n"

            # Then stream events one by one
            for event in events:
                yield json.dumps({
                    "type": "event",
                    "data": event.model_dump(mode='json')
                }) + "\n"
                # Small delay to allow progressive rendering
                await asyncio.sleep(0.01)

            # Signal end of stream
            yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.get("/api/events/live")
async def live_price_updates():
    """
    Server-Sent Events (SSE) endpoint for real-time price updates.
    Connect to this endpoint to receive live price changes as they happen.

    Event format:
    {
        "reference": "LO1234567890",
        "old_price": 100.0,
        "new_price": 150.0,
        "time_remaining": "5min",
        "timestamp": "2025-01-01T12:00:00"
    }
    """
    async def event_stream():
        queue = asyncio.Queue()
        sse_clients.add(queue)

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to live price updates'})}\n\n"

            # Keep connection alive and send updates
            while True:
                try:
                    # Wait for update with timeout (for keepalive)
                    update = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(update)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_clients.discard(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============== ERRO HANDLERS ==============

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Recurso não encontrado"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"}
    )


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    # Desabilita reload no Windows para evitar conflitos com Playwright
    reload_enabled = False if sys.platform == 'win32' else True
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level="info"
    )
