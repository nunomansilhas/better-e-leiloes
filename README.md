# E-Leiloes Dashboard & Scraper System

Sistema completo de monitorização e scraping para **e-leiloes.pt** com dashboard web, pipelines automáticas, sistema de notificações e alertas em tempo real.

## Versão Atual: v2.0 (Janeiro 2025)

### Novidades Recentes

- **Sistema de Notificações** - Regras personalizáveis para alertas de novos eventos e alterações de preço
- **Quick Notifications** - Ativar notificações por tipo de evento com um clique
- **Notificações por Evento** - Seguir alterações de eventos específicos
- **X-Monitor Melhorado** - Monitorização de preços em tempo real com histórico JSON
- **Página de Alertas** - Interface com tabs para gerir notificações e regras
- **Filtros Avançados** - Distrito, concelho, freguesia, subtipo, tipologia, valor min/max
- **Modal de Inspeção** - Ver detalhes completos de qualquer evento
- **Subtipos Dinâmicos** - Carregados da BD para cada tipo de evento

## Componentes

### Dashboard Web
- **URL**: `http://localhost:8000`
- Interface moderna com sidebar navegável
- 6 páginas de eventos: Imóveis, Veículos, Direitos, Equipamentos, Mobiliário, Máquinas
- Filtros avançados por localização, tipo e preço
- Notificações em tempo real
- Estatísticas e métricas do sistema

### Backend API
- **Framework**: FastAPI + Playwright
- **Base de dados**: MySQL (async com aiomysql)
- **Cache**: Redis (opcional)
- **Scheduler**: APScheduler para pipelines automáticas

### Sistema de Notificações
- **Regras personalizáveis** - Por tipo, subtipo, distrito, preço
- **Quick Notifications** - Toggle rápido por tipo de evento
- **Notificações por evento** - Seguir eventos específicos
- **Página de Alertas** - Gerir notificações e regras

## Estrutura do Projeto

```
better-e-leiloes/
├── backend/
│   ├── main.py              # FastAPI app + endpoints
│   ├── database.py          # SQLAlchemy models + DB manager
│   ├── scraper.py           # Playwright scraper
│   ├── notification_engine.py # Motor de notificações
│   ├── auto_pipelines.py    # Pipelines automáticas (X-Monitor, Y-Sync)
│   ├── pipeline_state.py    # Estado das pipelines
│   ├── cache.py             # Redis cache manager
│   ├── models.py            # Pydantic models
│   ├── static/
│   │   └── index.html       # Dashboard SPA
│   └── requirements.txt
├── database/
│   ├── MYSQL_SETUP.md
│   └── FIX_MYSQL_CORRUPTION.md
└── README.md
```

## Pipelines Automáticas

| Pipeline | Intervalo | Target | Descrição |
|----------|-----------|--------|-----------|
| **Auto Pipeline** | 8 horas | Todos | Pipeline completa: IDs + Content + Images |
| **X-Monitor** | 5 seg - 10 min | Ativos | Monitoriza preços de eventos por urgência |
| **Y-Sync** | 2 horas | Novos | Sincroniza novos eventos e dispara notificações |

### X-Monitor (Price Tracking)
Monitorização inteligente baseada em urgência:
- **Critical** (< 5 min): Verifica a cada 5 segundos
- **Urgent** (< 1 hora): Verifica a cada 1 minuto
- **Soon** (< 24 horas): Verifica a cada 10 minutos

## Quick Start

### 1. Instalar Dependências

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

Dashboard disponível em: **http://localhost:8000**

## API Endpoints

### Eventos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/events` | Lista eventos com paginação e filtros |
| GET | `/api/events/{reference}` | Detalhes de um evento |
| GET | `/api/stats` | Estatísticas gerais |

### Notificações
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/notifications` | Lista notificações |
| GET | `/api/notifications/count` | Contagem de não lidas |
| POST | `/api/notifications/read-all` | Marcar todas como lidas |
| DELETE | `/api/notifications/delete-all` | Eliminar todas |

### Regras de Notificação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/notification-rules` | Lista regras |
| POST | `/api/notification-rules` | Criar regra |
| PUT | `/api/notification-rules/{id}` | Atualizar regra |
| DELETE | `/api/notification-rules/{id}` | Eliminar regra |
| POST | `/api/notification-rules/{id}/toggle` | Ativar/desativar |

### Filtros Dinâmicos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/filters/subtypes/{tipo_id}` | Subtipos por tipo |
| GET | `/api/filters/distritos/{tipo_id}` | Distritos por tipo |

### Scraping
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/scrape/stage1/ids` | Descobrir IDs |
| POST | `/api/scrape/stage2/details` | Extrair conteúdo |
| POST | `/api/scrape/stage3/images` | Download imagens |
| GET | `/api/scrape/status` | Estado do scraper |
| POST | `/api/scrape/stop` | Parar scraping |

### Pipelines Automáticas
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/auto-pipelines/status` | Estado das pipelines |
| POST | `/api/auto-pipelines/{type}/toggle` | Ativar/desativar |
| GET | `/api/x-monitor/history` | Histórico X-Monitor |

## Funcionalidades do Dashboard

### Páginas de Eventos
- **6 categorias**: Imóveis, Veículos, Direitos, Equipamentos, Mobiliário, Máquinas
- **Cards informativos** com imagem, valores, tempo restante
- **Botões de ação**: Ver no site, recarregar, mapa, notificar
- **Paginação** client-side com todos os dados carregados

### Filtros Avançados
- Pesquisa por texto
- Distrito / Concelho / Freguesia (cascata)
- Subtipo e Tipologia (dinâmicos)
- Valor mínimo / máximo
- Ordenação por data ou valor

### Sistema de Notificações
- **Quick Toggle** - Botão no header de cada página para ativar notificações do tipo
- **Por Evento** - Botão de sino em cada card para seguir evento específico
- **Regras Personalizadas** - Criar regras com filtros avançados

### Página de Alertas
- **Tab Notificações** - Lista de alertas com ações (ver, marcar lida)
- **Tab Regras** - Tabela de regras com toggle e delete
- **Contadores** - Notificações não lidas e regras ativas

### Modal de Inspeção
- Ver todos os detalhes de um evento
- Galeria de imagens
- Mapa com localização GPS
- Informações de ónus e executados

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Dashboard Web (Port 8000)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Eventos    │  │  Alertas    │  │  Scrapers           │  │
│  │  6 Páginas  │  │  & Regras   │  │  & Pipelines        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST API + SSE
┌───────────────────────────┴─────────────────────────────────┐
│                      FastAPI Backend                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Notification│  │  Playwright │  │  Auto Pipelines     │  │
│  │   Engine    │  │  (Scraper)  │  │  X-Monitor/Y-Sync   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
      ┌───────┴───────┐           ┌───────┴───────┐
      │    MySQL      │           │    Redis      │
      │  (Eventos +   │           │   (Cache)     │
      │  Notificações)│           └───────────────┘
      └───────────────┘
```

## Base de Dados

### Tabelas Principais
- `events` - Todos os eventos com detalhes completos
- `notification_rules` - Regras de notificação configuradas
- `notifications` - Notificações geradas

### Schema de Notificações
```sql
-- Regras
CREATE TABLE notification_rules (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    rule_type VARCHAR(50),  -- 'new_event', 'price_change'
    active BOOLEAN,
    tipos JSON,             -- ["imoveis", "veiculos"]
    distritos JSON,         -- ["Lisboa", "Porto"]
    preco_min FLOAT,
    preco_max FLOAT,
    event_reference VARCHAR(50),  -- Para regras de evento específico
    triggers_count INT DEFAULT 0,
    created_at DATETIME
);

-- Notificações
CREATE TABLE notifications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    rule_id INT,
    notification_type VARCHAR(50),
    event_reference VARCHAR(50),
    event_titulo VARCHAR(500),
    preco_anterior FLOAT,
    preco_atual FLOAT,
    read BOOLEAN DEFAULT FALSE,
    created_at DATETIME
);
```

## Tecnologias

- **Backend**: Python 3.11, FastAPI, Playwright, SQLAlchemy
- **Database**: MySQL + aiomysql (async)
- **Cache**: Redis
- **Scheduler**: APScheduler
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla SPA)

## Troubleshooting

**Dashboard não carrega:**
```bash
curl http://localhost:8000/health
```

**Erros de base de dados:**
```bash
mysql -u user -p -h localhost eleiloes
```

**Migração de colunas:**
O sistema executa migrações automáticas no startup (init_db).

## Licença

MIT License

## Autor

**Nuno Mansilhas**

---

Dashboard: **http://localhost:8000** | API Docs: **http://localhost:8000/docs**
