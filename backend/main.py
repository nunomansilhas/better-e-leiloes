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

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import List, Optional
import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from models import EventData, EventListResponse, ScraperStatus
from database import init_db, get_db
from scraper import EventScraper
from cache import CacheManager

load_dotenv()

# Global instances
scraper = None
cache_manager = None
scheduler = None
scheduled_job_id = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown da aplicação"""
    global scraper, cache_manager, scheduler

    # Startup
    print("🚀 Iniciando E-Leiloes API...")
    await init_db()

    scraper = EventScraper()
    cache_manager = CacheManager()

    # Inicializa scheduler para agendamento
    scheduler = AsyncIOScheduler()
    scheduler.start()
    print("⏰ Scheduler iniciado")

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
    limit: int = Query(50, ge=1, le=5000, description="Eventos por página"),
    tipo: Optional[str] = None,
    tipo_evento: Optional[str] = None,
    distrito: Optional[str] = None
):
    """
    Lista eventos com paginação e filtros.

    - **page**: Número da página (começa em 1)
    - **limit**: Quantidade de resultados por página (max 5000)
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
    tipo: Optional[int] = Query(None, ge=1, le=2, description="1=imoveis, 2=moveis, None=ambos"),
    max_pages: Optional[int] = Query(None, ge=1, description="Máximo de páginas por tipo")
):
    """
    STAGE 1: Scrape apenas IDs e valores básicos da listagem (rápido).

    - **tipo**: 1=imóveis, 2=móveis, None=ambos
    - **max_pages**: Máximo de páginas por tipo

    Retorna lista de IDs com valores básicos.
    Ideal para descobrir rapidamente o que existe.
    """
    try:
        ids = await scraper.scrape_ids_only(tipo=tipo, max_pages=max_pages)

        return {
            "stage": 1,
            "total_ids": len(ids),
            "ids": ids,
            "message": f"Stage 1 completo: {len(ids)} IDs recolhidos"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Stage 1: {str(e)}")


@app.post("/api/scrape/stage2/details")
async def scrape_stage2_details(
    references: List[str] = Query(..., description="Lista de referências para scrape"),
    save_to_db: bool = Query(True, description="Guardar na base de dados")
):
    """
    STAGE 2: Scrape detalhes completos (SEM imagens) para lista de IDs.

    - **references**: Lista de referências (ex: ["LO-2024-001", "NP-2024-002"])
    - **save_to_db**: Se True, guarda eventos na BD

    Retorna eventos com todos os detalhes exceto imagens.
    """
    try:
        events = await scraper.scrape_details_by_ids(references)

        # Guarda na BD se solicitado
        if save_to_db:
            async with get_db() as db:
                for event in events:
                    await db.save_event(event)
                    await cache_manager.set(event.reference, event)

        return {
            "stage": 2,
            "total_requested": len(references),
            "total_scraped": len(events),
            "events": [event.model_dump() for event in events],
            "saved_to_db": save_to_db,
            "message": f"Stage 2 completo: {len(events)} eventos processados"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Stage 2: {str(e)}")


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
    try:
        images_map = await scraper.scrape_images_by_ids(references)

        # Atualiza eventos na BD se solicitado
        if update_db:
            async with get_db() as db:
                for ref, images in images_map.items():
                    # Busca evento existente
                    event = await db.get_event(ref)
                    if event:
                        # Atualiza imagens
                        event.imagens = images
                        event.updated_at = datetime.utcnow()
                        await db.save_event(event)
                        await cache_manager.set(ref, event)

        return {
            "stage": 3,
            "total_requested": len(references),
            "total_scraped": len(images_map),
            "images_map": images_map,
            "updated_db": update_db,
            "message": f"Stage 3 completo: {len(images_map)} eventos processados"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Stage 3: {str(e)}")


@app.post("/api/scrape/pipeline")
async def scrape_full_pipeline(
    background_tasks: BackgroundTasks,
    tipo: Optional[int] = Query(None, ge=1, le=2, description="1=imoveis, 2=moveis, None=ambos"),
    max_pages: Optional[int] = Query(None, ge=1, description="Máximo de páginas por tipo")
):
    """
    PIPELINE COMPLETO: Executa os 3 stages sequencialmente em background.

    1. Stage 1: Scrape IDs
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


@app.get("/api/stats")
async def get_stats():
    """
    Estatísticas gerais da base de dados.
    """
    async with get_db() as db:
        stats = await db.get_stats()
        return stats


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
    try:
        print(f"🚀 Iniciando pipeline completo (tipo={tipo}, max_pages={max_pages})...")

        # Stage 1: Scrape IDs
        print("\n" + "="*50)
        print("STAGE 1: SCRAPING IDs")
        print("="*50)
        ids_data = await scraper.scrape_ids_only(tipo=tipo, max_pages=max_pages)
        references = [item['reference'] for item in ids_data]
        print(f"✅ Stage 1: {len(references)} IDs recolhidos\n")

        if not references:
            print("⚠️ Nenhum ID encontrado. Pipeline terminado.")
            return

        # Stage 2: Scrape Detalhes (sem imagens)
        print("\n" + "="*50)
        print("STAGE 2: SCRAPING DETALHES")
        print("="*50)
        events = await scraper.scrape_details_by_ids(references)
        print(f"✅ Stage 2: {len(events)} eventos processados\n")

        # Guarda eventos na BD
        async with get_db() as db:
            for event in events:
                await db.save_event(event)
                await cache_manager.set(event.reference, event)

        # Stage 3: Scrape Imagens
        print("\n" + "="*50)
        print("STAGE 3: SCRAPING IMAGENS")
        print("="*50)
        images_map = await scraper.scrape_images_by_ids(references)
        print(f"✅ Stage 3: {len(images_map)} eventos com imagens\n")

        # Atualiza eventos com imagens
        async with get_db() as db:
            for ref, images in images_map.items():
                event = await db.get_event(ref)
                if event:
                    event.imagens = images
                    event.updated_at = datetime.utcnow()
                    await db.save_event(event)
                    await cache_manager.set(ref, event)

        print("\n" + "="*50)
        print("🎉 PIPELINE COMPLETO!")
        print(f"   IDs: {len(references)}")
        print(f"   Detalhes: {len(events)}")
        print(f"   Imagens: {len(images_map)}")
        print("="*50 + "\n")

    except Exception as e:
        print(f"❌ Erro no pipeline: {e}")


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
