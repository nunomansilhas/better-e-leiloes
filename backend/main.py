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

from models import EventData, EventListResponse, ScraperStatus
from database import init_db, get_db
from scraper import EventScraper
from cache import CacheManager

load_dotenv()

# Global instances
scraper = None
cache_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown da aplicação"""
    global scraper, cache_manager
    
    # Startup
    print("🚀 Iniciando E-Leiloes API...")
    await init_db()
    
    scraper = EventScraper()
    cache_manager = CacheManager()
    
    print("✅ API pronta!")
    
    yield
    
    # Shutdown
    print("👋 Encerrando API...")
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
    limit: int = Query(50, ge=1, le=200, description="Eventos por página"),
    tipo: Optional[str] = None,
    tipo_evento: Optional[str] = None,
    distrito: Optional[str] = None
):
    """
    Lista eventos com paginação e filtros.
    
    - **page**: Número da página (começa em 1)
    - **limit**: Quantidade de resultados por página (max 200)
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
