# Backend - Better E-Leiloes

API principal com scraping, pipelines automaticos e admin panel.

---

## TLDR - Para o Proximo AI

### Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| `Can't patch loop of type uvloop.Loop` | nest_asyncio com uvloop | So usar nest_asyncio em Windows |
| `Browser.new_context: 'NoneType' object has no attribute 'send'` | Scraper criado fora do proactor | Criar scraper DENTRO de `run_in_proactor` |
| `observacoes: null` apesar de existir | Campo nao esta no modelo public-api | Adicionar a `public-api/database.py` |
| Z-Watch "Nenhum evento" | API usa campo `list` | Verificar `['list', 'items', ...]` |

### Ficheiros Criticos

```
backend/
├── main.py              # ~3000 linhas - API endpoints + admin
├── scraper.py           # ~2200 linhas - EventScraper (Playwright)
├── auto_pipelines.py    # ~2000 linhas - X-Monitor, Y-Sync, Z-Watch
├── database.py          # ~2100 linhas - SQLAlchemy models
├── models.py            # ~300 linhas - Pydantic EventData
└── services/
    ├── ai_analysis_service.py   # Analise AI de veiculos
    └── ollama_service.py        # Integracao Ollama
```

### Scraper - Metodos Importantes

```python
class EventScraper:
    # Scraping via API (rapido, mas pode faltar observacoes)
    async def scrape_details_via_api(refs: List[str]) -> List[EventData]

    # Scraping via HTML (lento, mas captura tudo)
    async def scrape_event_html(reference: str) -> EventData

    # Fechar browser
    async def close()
```

### Pipelines - O Que Fazem

```
X-Monitor (5s-10min)
├── Busca eventos com data_fim < 1 hora
├── Atualiza lance_atual via API
└── Regista alteracoes em price_history

Y-Sync (2h)
├── Busca eventos ativos na DB
├── Verifica quais terminaram
├── Marca terminado=True
└── Adiciona novos eventos

Z-Watch (10min)
├── Chama API EventosMaisRecentes
├── Encontra novos eventos
├── Scrape detalhes via API
└── Insere na DB
```

### Funcao Helper Critica

```python
# Em auto_pipelines.py - SEMPRE usar isto para scraping
async def scrape_refs_with_new_scraper(references: list):
    """Cria scraper DENTRO do thread correto."""
    from scraper import EventScraper
    scraper = EventScraper()
    try:
        return await scraper.scrape_details_via_api(references)
    finally:
        await scraper.close()

# Uso:
events = await run_in_proactor(scrape_refs_with_new_scraper, refs)
```

### EventData Schema (Flat)

```python
# models.py - EventData usa schema FLAT
class EventData(BaseModel):
    reference: str
    lance_atual: float = 0           # NAO event.valores.lanceAtual
    data_fim: Optional[datetime]     # NAO event.datas.dataFim
    observacoes: Optional[str]       # Campo importante!
    # ... outros campos flat
```

---

## Estrutura

```
backend/
├── main.py              # FastAPI app + endpoints
├── run.py               # Entry point
├── scraper.py           # Playwright web scraper
├── auto_pipelines.py    # Pipelines automaticos
├── database.py          # SQLAlchemy async
├── models.py            # Pydantic models
├── cache.py             # Redis cache manager
├── services/            # Servicos externos
│   ├── ai_analysis_service.py
│   ├── ai_questions_service.py
│   └── ollama_service.py
├── routers/             # API routers
│   ├── ai_tips_router.py
│   └── vehicle_router.py
├── static/              # Admin panel
│   └── index.html
├── migrations/          # SQL schemas
└── requirements.txt
```

## Quick Start

```bash
# Instalar dependencias
pip install -r requirements.txt
playwright install chromium

# Configurar
cp .env.example .env
nano .env

# Correr
python run.py
```

## Endpoints Principais

### Eventos

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/events` | Lista eventos (paginado) |
| GET | `/api/events/{ref}` | Detalhes evento |
| POST | `/api/events/{ref}/rescrape` | Rescrape via HTML |
| POST | `/api/refresh/{ref}` | Atualizar via API |
| POST | `/api/events/batch` | Buscar multiplos |

### Pipelines

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/pipeline/status` | Estado pipelines |
| POST | `/api/pipeline/{name}/toggle` | Ativar/desativar |
| POST | `/api/pipeline/{name}/run` | Executar agora |

### Debug

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/debug/db-observacoes/{ref}` | Ver observacoes na DB |
| GET | `/api/debug/api-raw/{ref}` | Ver resposta raw da API |

### Admin

| URL | Descricao |
|-----|-----------|
| `/` | Admin panel (static/index.html) |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |

## Configuracao (.env)

```env
# Database (obrigatorio)
DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/eleiloes

# Redis (opcional)
REDIS_URL=redis://localhost:6379

# API
API_PORT=8000
API_HOST=0.0.0.0
API_AUTH_KEY=secret-key-for-admin

# Ollama (para AI)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## Database Schema

Tabelas principais:

| Tabela | Descricao |
|--------|-----------|
| `events` | Eventos de leilao |
| `price_history` | Historico de precos |
| `pipeline_state` | Estado dos pipelines |
| `refresh_logs` | Log de refreshes |
| `favorites` | Favoritos do utilizador |
| `notifications` | Notificacoes |
| `notification_rules` | Regras de notificacao |
| `event_ai_tips` | Dicas AI geradas |

## Notas Importantes

### Playwright no Linux

- uvloop (default no uvicorn) NAO e compativel com nest_asyncio
- Playwright precisa de ProactorEventLoop no Windows
- Solucao: usar `run_in_proactor()` helper

### Observacoes Field

O campo `observacoes` pode conter informacao critica sobre o leilao:
- Condicoes especiais
- Alertas do agente de execucao
- Informacao sobre heranças
- Notas sobre visitas

Se `observacoes` aparece null na API mas existe na DB:
1. Verificar se o campo existe no modelo SQLAlchemy
2. Verificar se esta a ser serializado no endpoint

### Cache

O backend usa Redis para cache de eventos. Se dados parecem desatualizados:
- Usar `?skip_cache=true` no endpoint
- Ou limpar cache manualmente

---

MIT License - Nuno Mansilhas
