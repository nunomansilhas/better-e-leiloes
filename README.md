# E-Leiloes Dashboard & Scraper System

Sistema completo de monitorização e scraping para **e-leiloes.pt** com dashboard web, pipelines automáticas e alertas em tempo real.

## Componentes

### Dashboard Web
- **URL**: `http://localhost:8000`
- Interface moderna com sidebar navegável
- Visualização de todos os eventos em tempo real
- Filtros avançados por tipo, distrito e estado
- Estatísticas e métricas do sistema

### Backend API
- **Framework**: FastAPI + Playwright
- **Base de dados**: MySQL (async com aiomysql)
- **Cache**: Redis (opcional)
- **Scheduler**: APScheduler para pipelines automáticas

### Extensao Browser (Tampermonkey)
- **Arquivo**: `betterE-Leiloes-v12.0-API.user.js`
- Badges nos cards: GPS, Valores, Detalhes
- Modal de visualizacao integrado

## Pipelines Automaticas

O sistema inclui 5 pipelines automáticas configuráveis:

| Pipeline | Intervalo | Target | Descricao |
|----------|-----------|--------|-----------|
| **Auto Pipeline** | 8 horas | Todos | Pipeline completa: IDs + Content + Images |
| **X-Critical** | 5 segundos | < 5 min | Monitoriza precos de eventos a terminar |
| **X-Urgent** | 1 minuto | < 1 hora | Precos de eventos urgentes |
| **X-Soon** | 10 minutos | < 24 horas | Precos de eventos proximos |
| **Y-Info** | 2 horas | Todos | Verificacao geral de informacoes |

## Scrapers Independentes

Executa cada fase separadamente:

- **IDs** - Descobre novos eventos no site
- **Recheck** - Verifica eventos novos (smart scraping)
- **Content** - Extrai detalhes de todos os eventos
- **Images** - Download de imagens dos eventos

## Pipeline Completo (3 Stages)

```
Stage 1: IDs      Stage 2: Content      Stage 3: Images
   [1] ────────────── [2] ────────────────── [3]
   Descobrir IDs      Extrair detalhes       Download imagens
```

## Quick Start

### 1. Instalar Dependencias

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### 2. Configurar Base de Dados

Criar ficheiro `.env`:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database - MySQL
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/eleiloes

# Redis Cache (opcional)
REDIS_URL=redis://localhost:6379

# Scraping
SCRAPE_DELAY=0.8
CONCURRENT_REQUESTS=4
```

### 3. Iniciar Servidor

```bash
python run.py
```

Dashboard disponivel em: **http://localhost:8000**

## API Endpoints

### Eventos
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/events` | Lista eventos com paginacao |
| GET | `/api/events/{reference}` | Detalhes de um evento |
| GET | `/api/events/stream` | Stream SSE de eventos |
| GET | `/api/stats` | Estatisticas gerais |

### Scraping
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/scrape/stage1/ids` | Descobrir IDs |
| POST | `/api/scrape/stage2/details` | Extrair conteudo |
| POST | `/api/scrape/stage3/images` | Download imagens |
| POST | `/api/scrape/pipeline` | Pipeline completo |
| POST | `/api/scrape/smart/new-events` | Smart scraping |
| GET | `/api/scrape/status` | Estado do scraper |
| POST | `/api/scrape/stop` | Parar scraping |

### Pipelines Automaticas
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/auto-pipelines/status` | Estado de todas as pipelines |
| POST | `/api/auto-pipelines/{type}/toggle` | Ativar/desativar pipeline |
| GET | `/api/auto-pipelines/prices/cache-info` | Info da cache de precos |

### Sistema
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/health` | Health check |
| GET | `/api/logs` | Logs do sistema |
| DELETE | `/api/database` | Limpar base de dados |
| DELETE | `/api/cache` | Limpar cache |

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Dashboard Web (Port 8000)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Eventos    │  │  Pipelines  │  │  Scrapers           │  │
│  │  Listagem   │  │  Automaticas│  │  Independentes      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST API + SSE
┌───────────────────────────┴─────────────────────────────────┐
│                      FastAPI Backend                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ APScheduler │  │  Playwright │  │  Auto Pipelines     │  │
│  │  (Jobs)     │  │  (Scraper)  │  │  Manager            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
      ┌───────┴───────┐           ┌───────┴───────┐
      │    MySQL      │           │    Redis      │
      │  (Eventos)    │           │   (Cache)     │
      └───────────────┘           └───────────────┘
```

## Funcionalidades do Dashboard

### Visualizacao de Eventos
- Cards com informacao completa
- Imagens dos eventos
- Valores base e actuais
- Tempo restante ate fim do leilao
- GPS e localizacao

### Filtros
- Tipo de evento (Imovel/Movel)
- Distrito
- Estado (Ativo/Terminado)
- Pesquisa por texto

### Gestao de Pipelines
- Toggle on/off para cada pipeline
- Visualizacao do estado em tempo real
- Contador de execucoes
- Proxima execucao agendada

## Troubleshooting

**Dashboard nao carrega:**
```bash
# Verificar se o servidor esta a correr
curl http://localhost:8000/health
```

**Erros de base de dados:**
```bash
# Verificar conexao MySQL
mysql -u user -p -h localhost eleiloes
```

**Scraping lento:**
- Ajustar `SCRAPE_DELAY` no .env
- Verificar `CONCURRENT_REQUESTS`

## Tecnologias

- **Backend**: Python 3.11, FastAPI, Playwright
- **Database**: MySQL + aiomysql
- **Cache**: Redis
- **Scheduler**: APScheduler
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)

## Licenca

MIT License

## Autor

**Nuno Mansilhas**

---

Dashboard: **http://localhost:8000** | API Docs: **http://localhost:8000/docs**
