# Better E-Leiloes

Sistema completo para scraping, monitorização e análise de leilões do e-leiloes.pt (portal oficial de leilões judiciais em Portugal).

---

## TLDR - Para o Proximo AI

### Arquitetura (3 Componentes)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    BACKEND      │     │   PUBLIC-API    │     │    FRONTEND     │
│   (porta 8000)  │     │   (porta 3000)  │     │   (dashboard)   │
│                 │     │                 │     │                 │
│ - Scraping      │     │ - Read-only     │     │ - dashboard.html│
│ - Pipelines     │────>│ - Para clientes │<────│ - Chrome ext    │
│ - Admin panel   │     │ - Notificacoes  │     │ - Userscript    │
│ - AI analysis   │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────┴──────┐
              │   MySQL DB  │
              │   (events)  │
              └─────────────┘
```

### Regras Criticas

1. **nest_asyncio + uvloop NAO FUNCIONA** - So aplicar nest_asyncio em Windows:
   ```python
   if sys.platform == 'win32':
       import nest_asyncio
       nest_asyncio.apply()
   ```

2. **Playwright precisa de ProactorEventLoop** - Criar scraper DENTRO do proactor thread:
   ```python
   async def scrape_refs_with_new_scraper(references: list):
       scraper = EventScraper()  # Criar AQUI, nao fora
       try:
           return await scraper.scrape_details_via_api(references)
       finally:
           await scraper.close()

   events = await run_in_proactor(scrape_refs_with_new_scraper, refs)
   ```

3. **API e-leiloes.pt retorna eventos no campo 'list'** (nao 'items' ou 'lista'):
   ```python
   for key in ['list', 'items', 'eventos', 'events', 'data', 'results', 'lista']:
       if key in api_response:
           events = api_response[key]
   ```

4. **Dois modelos EventDB separados** - Backend e public-api tem modelos DIFERENTES:
   - `backend/database.py` - Modelo completo com TODOS os campos
   - `public-api/database.py` - Modelo simplificado (adicionar campos novos aqui tambem!)

5. **Schema flat (novo)** vs Schema nested (legado):
   ```python
   # CORRETO (flat)
   event.lance_atual
   event.data_fim
   event.observacoes

   # ERRADO (legado - nao existe mais)
   event.valores.lanceAtual  # AttributeError!
   event.datas.dataFim       # AttributeError!
   ```

### Ficheiros Importantes

| Ficheiro | Descricao |
|----------|-----------|
| `backend/main.py` | API principal, endpoints, admin panel |
| `backend/scraper.py` | EventScraper com Playwright |
| `backend/auto_pipelines.py` | X-Monitor, Y-Sync, Z-Watch |
| `backend/database.py` | SQLAlchemy models + DB operations |
| `public-api/main.py` | API publica read-only |
| `public-api/database.py` | Modelos simplificados (SINCRONIZAR!) |

### Pipelines

| Pipeline | Intervalo | Funcao |
|----------|-----------|--------|
| **X-Monitor** | 5s-10min | Monitoriza precos de eventos urgentes (< 1h) |
| **Y-Sync** | 2h | Sincroniza novos eventos + marca terminados |
| **Z-Watch** | 10min | Vigia novos eventos na API |

### Endpoints Principais

| Porta | Endpoint | Descricao |
|-------|----------|-----------|
| 8000 | `/api/events/{ref}` | Evento completo (backend) |
| 8000 | `/api/refresh/{ref}` | Rescrape evento |
| 8000 | `/api/debug/db-observacoes/{ref}` | Debug campo observacoes |
| 3000 | `/api/events/{ref}` | Evento (public-api) |
| 3000 | `/api/ending-soon` | Eventos a terminar |

### Campos do EventData

```
reference, id_api, titulo, capa, tipo_id, tipo, subtipo, tipologia,
valor_base, valor_abertura, valor_minimo, lance_atual,
data_inicio, data_fim, data_fim_inicial,
distrito, concelho, freguesia, morada, morada_cp, latitude, longitude,
area_privativa, area_dependente, area_total, matricula,
descricao, observacoes,  # <-- observacoes pode ter info importante!
processo_numero, processo_tribunal, processo_comarca,
gestor_nome, gestor_email, gestor_telefone, gestor_tipo, gestor_cedula,
cerimonia_data, cerimonia_local, cerimonia_morada,
fotos, onus, executados, anexos,
terminado, cancelado, iniciado, ativo
```

---

## Estrutura do Projeto

```
better-e-leiloes/
├── backend/                 # API principal + scraping
│   ├── main.py             # FastAPI app
│   ├── scraper.py          # Playwright scraper
│   ├── auto_pipelines.py   # Pipelines automaticos
│   ├── database.py         # SQLAlchemy models
│   ├── models.py           # Pydantic models
│   ├── static/             # Admin panel HTML
│   ├── services/           # AI services (Ollama)
│   └── routers/            # API routers
│
├── public-api/             # API publica (read-only)
│   ├── main.py             # FastAPI app
│   ├── database.py         # Modelos simplificados
│   └── static/             # Dashboard HTML
│
├── frontend/               # Clientes
│   ├── dashboard.html      # Dashboard standalone
│   ├── chrome-extension/   # Chrome extension
│   └── *.user.js          # Tampermonkey script
│
└── passenger_wsgi.py       # Deploy cPanel
```

## Quick Start

### Backend (porta 8000)

```bash
cd backend
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Configurar DATABASE_URL, REDIS_URL

python run.py
```

### Public API (porta 3000)

```bash
cd public-api
pip install -r requirements.txt

cp .env.example .env
# Configurar DATABASE_URL

uvicorn main:app --port 3000
```

## Configuracao (.env)

```env
# Database
DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/eleiloes

# Redis (opcional, para cache)
REDIS_URL=redis://localhost:6379

# API
API_PORT=8000
API_AUTH_KEY=your-secret-key

# Ollama (para AI tips)
OLLAMA_URL=http://localhost:11434
```

## Deploy (cPanel)

O projeto usa `passenger_wsgi.py` para deploy em cPanel com Passenger WSGI.

---

MIT License - Nuno Mansilhas
