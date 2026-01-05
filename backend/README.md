# E-Leiloes API Backend

Backend FastAPI para o sistema E-Leiloes Dashboard com scraping, notificações e monitorização em tempo real.

## Versão 2.0 (Janeiro 2025)

### Principais Ficheiros

| Ficheiro | Descrição |
|----------|-----------|
| `main.py` | FastAPI app, todos os endpoints REST |
| `database.py` | SQLAlchemy models, DB manager, migrações |
| `scraper.py` | Playwright scraper (IDs, Content, Images) |
| `notification_engine.py` | Motor de notificações (regras, matching) |
| `auto_pipelines.py` | X-Monitor, Y-Sync, Auto Pipeline |
| `pipeline_state.py` | Estado global das pipelines |
| `cache.py` | Redis cache manager |
| `models.py` | Pydantic models (EventData, etc.) |
| `static/index.html` | Dashboard SPA completo |

## Instalação

```bash
# Dependências Python
pip install -r requirements.txt

# Playwright browsers
playwright install chromium

# Configurar .env
cp .env.example .env
```

## Configuração (.env)

```env
# API
API_HOST=0.0.0.0
API_PORT=8000

# Database - MySQL
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/eleiloes

# Redis (opcional)
REDIS_URL=redis://localhost:6379

# Scraping
SCRAPE_DELAY=0.8
CONCURRENT_REQUESTS=4
```

## Iniciar Servidor

```bash
python run.py
# ou
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Eventos

```bash
# Listar com filtros
GET /api/events?tipo_evento=imoveis&page=1&limit=50&distrito=Lisboa

# Detalhes
GET /api/events/{reference}

# Estatísticas
GET /api/stats
```

### Notificações

```bash
# Listar
GET /api/notifications?limit=50&unread_only=true

# Contagem não lidas
GET /api/notifications/count

# Marcar lida
POST /api/notifications/{id}/read

# Marcar todas lidas
POST /api/notifications/read-all

# Eliminar todas
DELETE /api/notifications/delete-all
```

### Regras de Notificação

```bash
# Listar
GET /api/notification-rules?active_only=true

# Criar
POST /api/notification-rules
{
    "name": "Quick Notifications",
    "rule_type": "new_event",
    "tipos": ["imoveis", "veiculos"],
    "distritos": ["Lisboa"],
    "preco_max": 200000,
    "active": true
}

# Atualizar
PUT /api/notification-rules/{id}
{
    "tipos": ["imoveis", "veiculos", "direitos"]
}

# Toggle ativo/inativo
POST /api/notification-rules/{id}/toggle?active=false

# Eliminar
DELETE /api/notification-rules/{id}
```

### Filtros Dinâmicos

```bash
# Subtipos por tipo (1=imóveis, 2=veículos, etc.)
GET /api/filters/subtypes/1

# Distritos por tipo
GET /api/filters/distritos/1
```

### Scraping

```bash
# Stage 1 - Descobrir IDs
POST /api/scrape/stage1/ids?tipo=1&max_pages=10

# Stage 2 - Extrair detalhes
POST /api/scrape/stage2/details

# Stage 3 - Download imagens
POST /api/scrape/stage3/images

# Pipeline completo
POST /api/scrape/pipeline?tipo=1

# Estado
GET /api/scrape/status

# Parar
POST /api/scrape/stop
```

### Pipelines Automáticas

```bash
# Estado de todas
GET /api/auto-pipelines/status

# Toggle pipeline
POST /api/auto-pipelines/x-monitor/toggle

# Histórico X-Monitor
GET /api/x-monitor/history
```

## Base de Dados

### Tabelas

```sql
-- Eventos (schema completo)
events (
    reference VARCHAR(50) PRIMARY KEY,
    titulo, capa, tipo_id, subtipo_id,
    valor_base, valor_minimo, lance_atual,
    data_inicio, data_fim,
    distrito, concelho, freguesia,
    latitude, longitude,
    area_total, area_privativa,
    fotos JSON, onus JSON,
    ...
)

-- Regras de notificação
notification_rules (
    id INT PRIMARY KEY,
    name, rule_type, active,
    tipos JSON, distritos JSON,
    preco_min, preco_max,
    event_reference,  -- Para regras de evento específico
    triggers_count, created_at
)

-- Notificações geradas
notifications (
    id INT PRIMARY KEY,
    rule_id, notification_type,
    event_reference, event_titulo,
    preco_anterior, preco_atual,
    read, created_at
)
```

### Migrações Automáticas

O `init_db()` executa migrações automáticas:
- Adiciona `event_reference` à tabela `notification_rules` se não existir

## Notification Engine

### Tipos de Regra

| Tipo | Descrição |
|------|-----------|
| `new_event` | Novo evento que corresponde aos filtros |
| `price_change` | Alteração de preço num evento |

### Filtros Disponíveis

- `tipos` - Array de tipos: `["imoveis", "veiculos"]`
- `subtipos` - Array de subtipos: `["Apartamento", "Moradia"]`
- `distritos` - Array de distritos: `["Lisboa", "Porto"]`
- `preco_min` / `preco_max` - Range de preço
- `event_reference` - Evento específico (para notificações por evento)

### Fluxo

1. **Y-Sync** detecta novos eventos
2. **NotificationEngine** avalia contra regras ativas
3. Se match, cria entrada em `notifications`
4. Dashboard atualiza badge e lista

## Pipelines Automáticas

### X-Monitor
Monitoriza preços de eventos ativos:
- **Critical** (< 5 min): 5 segundos
- **Urgent** (< 1 hora): 1 minuto
- **Soon** (< 24 horas): 10 minutos

### Y-Sync
Sincroniza novos eventos a cada 2 horas e dispara notificações.

### Auto Pipeline
Pipeline completa (IDs + Content + Images) a cada 8 horas.

## Dashboard (static/index.html)

SPA com ~7500 linhas que inclui:

- **6 páginas de eventos** com cards, filtros, paginação
- **Página de Alertas** com tabs (Notificações/Regras)
- **Modal de Inspeção** para detalhes de eventos
- **Quick Notifications** toggle no header de cada página
- **Botão de notificação** em cada card de evento
- **Página de Scraper** para gestão manual
- **Console de logs** em tempo real

### Funções JavaScript Principais

```javascript
// Eventos
loadEvents(type, page)
createEventCard(event)
openInspectionModal(reference)

// Notificações
loadNotifications()
loadNotificationRules()
toggleQuickNotification(tipo, tipoId)
toggleEventNotification(reference, titulo, tipoEvento)
updateNotifyButtonStates()

// Filtros
loadSubtypesForPage(tipo)
updateDistritoFilter()
applyFilters(type)
```

## Logs

```
🚀 Iniciando E-Leiloes API...
✅ Database inicializada
✅ Added event_reference column to notification_rules
✅ API pronta em http://localhost:8000
🔔 Notificação criada: LO20250001234 (regra: Quick Notifications)
```

## Troubleshooting

**Erro "Unknown column 'event_reference'":**
- Reiniciar servidor - migração automática adiciona a coluna

**Playwright não funciona:**
```bash
playwright install chromium --with-deps
```

**Redis connection failed:**
- Sistema funciona sem Redis (usa cache em memória)

## Tecnologias

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy 2.0 (async)
- Playwright
- APScheduler
- aiomysql + PyMySQL
- Redis (opcional)

## Licença

MIT License - Nuno Mansilhas
