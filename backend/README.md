# E-Leiloes API Backend

Backend API para recolha e disponibilização de dados do **e-leiloes.pt**.

## 🆕 Versão 12.4 (Dezembro 2024)

### 🎯 Novidades

**Backend:**
- ✅ Filtro por `tipo_evento` (imovel/movel) no endpoint `/api/events`
- ✅ Schema completo: valores de leilão, GPS, tipologia, matrícula
- ✅ Endpoint DELETE `/api/database` para gestão de dados
- ✅ Two-phase scraping: listing + details (otimizado)
- ✅ Suporte completo para móveis e imóveis

**Frontend (Extensão):**
- 🎨 Ícones melhorados: `☰` lista, `▦` grelha
- 🔍 Filtros por tipo de evento funcionais
- 📊 Modal com visualização lista/grelha
- 🗑️ Gestão de base de dados integrada
- ⚡ Cards compactos responsivos

## 🏗️ Arquitetura

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Extensão      │─────▶│   FastAPI        │─────▶│   e-leiloes.pt  │
│   (Frontend)    │      │   (Backend)      │      │   (Scraping)    │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                │
                                ▼
                         ┌──────────────┐
                         │   SQLite DB  │
                         └──────────────┘
                                │
                                ▼
                         ┌──────────────┐
                         │ Redis Cache  │
                         │  (Opcional)  │
                         └──────────────┘
```

## ✨ Features

- ✅ **API RESTful** com FastAPI
- ✅ **Scraping assíncrono** com Playwright (two-phase: listing + details)
- ✅ **Base de dados** SQLite com schema completo (valores, GPS, detalhes)
- ✅ **Cache** Redis (opcional, fallback para memória)
- ✅ **Processamento em background** para scraping massivo
- ✅ **Paginação e filtros** avançados (tipo_evento, distrito, tipo)
- ✅ **CORS** configurado para extensão browser
- ✅ **Documentação automática** (Swagger/OpenAPI)
- ✅ **Gestão de base de dados** (delete all, stats)
- ✅ **Suporte completo** para imóveis e móveis

## 📋 Pré-requisitos

- Python 3.10+
- pip
- (Opcional) Redis para caching

## 🚀 Instalação

### 1. Clone e instale dependências

```bash
cd backend
pip install -r requirements.txt
```

### 2. Instale Playwright browsers

```bash
playwright install chromium
```

### 3. Configure variáveis de ambiente

```bash
cp .env.example .env
# Edita .env com tuas configurações
```

### 4. Inicie o servidor

```bash
python main.py
```

A API estará disponível em: **http://localhost:8000**

Documentação interativa: **http://localhost:8000/docs**

## 📚 Endpoints da API

### GET `/`
Health check da API

### GET `/api/events/{reference}`
Obtém dados de um evento específico.

**Exemplo:**
```bash
curl http://localhost:8000/api/events/NP-2024-12345
```

**Resposta:**
```json
{
  "reference": "NP-2024-12345",
  "tipoEvento": "imovel",
  "valores": {
    "valorBase": 150000.0,
    "valorAbertura": 140000.0,
    "valorMinimo": 130000.0,
    "lanceAtual": 155000.0
  },
  "gps": {
    "latitude": 38.7223,
    "longitude": -9.1393
  },
  "detalhes": {
    "tipo": "Apartamento",
    "subtipo": "Apartamento T2",
    "tipologia": "T2",
    "areaPrivativa": 85.5,
    "areaDependente": 10.0,
    "areaTotal": 95.5,
    "distrito": "Lisboa",
    "concelho": "Lisboa",
    "freguesia": "Avenidas Novas",
    "matricula": null
  },
  "scraped_at": "2024-12-05T10:30:00Z",
  "updated_at": null
}
```

### GET `/api/events`
Lista eventos com paginação e filtros.

**Query params:**
- `page`: Número da página (default: 1)
- `limit`: Resultados por página (default: 50, max: 200)
- `tipo`: Filtrar por tipo de propriedade (Apartamento, Moradia, etc) (opcional)
- `tipo_evento`: Filtrar por tipo de evento - "imovel" ou "movel" (opcional)
- `distrito`: Filtrar por distrito (opcional)

**Exemplos:**
```bash
# Apenas imóveis
curl "http://localhost:8000/api/events?tipo_evento=imovel&page=1&limit=10"

# Apartamentos em Lisboa
curl "http://localhost:8000/api/events?tipo=Apartamento&distrito=Lisboa"

# Apenas móveis
curl "http://localhost:8000/api/events?tipo_evento=movel"
```

### POST `/api/scrape/event/{reference}`
Força re-scraping de um evento específico (background task).

### POST `/api/scrape/all`
Inicia scraping de TODOS os eventos (⚠️ pode demorar horas!).

**Query params:**
- `max_pages`: Limitar número de páginas (opcional)

### GET `/api/scrape/status`
Status atual do scraper.

### DELETE `/api/cache`
Limpa todo o cache Redis/memória.

### DELETE `/api/database`
**⚠️ PERIGO:** Apaga TODOS os eventos da base de dados.

**Resposta:**
```json
{
  "message": "Base de dados limpa com sucesso",
  "deleted_events": 24
}
```

### GET `/api/stats`
Estatísticas da base de dados.

**Resposta:**
```json
{
  "total_events": 24,
  "with_gps": 12,
  "by_type": {
    "Apartamento": 8,
    "Moradia": 4,
    "Automóvel": 12
  }
}
```

## 🔧 Configuração

### `.env` principais variáveis:

```env
# API
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///./eleiloes.db

# Redis (opcional)
REDIS_URL=redis://localhost:6379

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://www.e-leiloes.pt

# Scraping
SCRAPE_DELAY=0.8  # Delay entre requests (segundos)
CONCURRENT_REQUESTS=4  # Requests paralelos
```

## 📊 Base de Dados

SQLite schema automático:

```sql
CREATE TABLE events (
    reference TEXT PRIMARY KEY,
    tipo_evento TEXT NOT NULL,  -- 'imovel' ou 'movel'
    
    -- Valores do leilão
    valor_base REAL,
    valor_abertura REAL,
    valor_minimo REAL,
    lance_atual REAL,
    
    -- GPS (apenas imóveis)
    latitude REAL,
    longitude REAL,
    
    -- Detalhes gerais
    tipo TEXT,
    subtipo TEXT,
    
    -- Detalhes imóveis
    tipologia TEXT,
    area_privativa REAL,
    area_dependente REAL,
    area_total REAL,
    
    -- Localização
    distrito TEXT,
    concelho TEXT,
    freguesia TEXT,
    
    -- Detalhes móveis
    matricula TEXT,
    
    -- Metadados
    scraped_at DATETIME,
    updated_at DATETIME
);
```

## 🐳 Deploy com Docker

```dockerfile
# Dockerfile (criar)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "main.py"]
```

```bash
docker build -t eleiloes-api .
docker run -p 8000:8000 --env-file .env eleiloes-api
```

## ⚡ Performance & Scraping

### Two-Phase Scraping Strategy

O scraper usa uma estratégia em duas fases:

**Fase 1 - Listing (tipo=1 e tipo=2):**
- Navega pelas páginas de listagem (imoveis e moveis)
- Extrai referências e valores dos cards
- Para automaticamente em páginas vazias
- ~2 páginas por tipo = 4 páginas totais

**Fase 2 - Details:**
- Processa cada evento individualmente
- Extrai GPS (imóveis), tipologia, áreas, localização
- Processa 4 eventos em paralelo
- Total: ~24 eventos em 2 minutos

### Otimizações

- **Cache Redis**: Reduz latência de ~800ms para <10ms
- **Processamento paralelo**: 4 eventos simultâneos (configurável)
- **Delay configurável**: Evita sobrecarga do site (800ms default)
- **Background tasks**: Scraping massivo sem bloquear API
- **Stop on empty**: Para navegação em páginas vazias automaticamente

## 🔒 Segurança

- **CORS** restrito aos domínios configurados
- **Rate limiting** (TODO: adicionar)
- **API Key** (TODO: adicionar autenticação)

## 📝 Logs

Logs estruturados no stdout:
```
🚀 Iniciando E-Leiloes API...
✅ Database inicializada
✅ Redis conectado
✅ API pronta!
```

## 🧪 Testes

```bash
# Teste unitário
pytest

# Teste de carga
locust -f tests/load_test.py
```

## 📈 Monitorização

Integração com:
- Prometheus (métricas)
- Grafana (dashboards)
- Sentry (error tracking)

## 🤝 Integração com Extensão

A extensão Tampermonkey (`betterE-Leiloes-v12.4-API.user.js`) faz requests para:

```javascript
const API_URL = 'http://localhost:8000/api';

// Buscar evento específico
async function getEventData(reference) {
    const response = await fetch(`${API_URL}/events/${reference}`);
    return await response.json();
}

// Listar eventos com filtros
async function listEvents(page = 1, limit = 50, filters = {}) {
    let url = `${API_URL}/events?page=${page}&limit=${limit}`;
    
    if (filters.tipoEvento) url += `&tipo_evento=${filters.tipoEvento}`;
    if (filters.distrito) url += `&distrito=${filters.distrito}`;
    
    const response = await fetch(url);
    return await response.json();
}

// Trigger scraping completo
async function triggerFullScrape() {
    const response = await fetch(`${API_URL}/scrape/all`, { method: 'POST' });
    return await response.json();
}

// Limpar base de dados
async function clearDatabase() {
    const response = await fetch(`${API_URL}/database`, { method: 'DELETE' });
    return await response.json();
}
```

### Features da Extensão v12.4

- 🎨 **Badges nos cards**: GPS, Valores, Detalhes
- 📊 **Modal de visualização**: Lista e grelha compacta
- 🔍 **Filtros avançados**: Por tipo de evento (imóvel/móvel) e distrito
- 🗑️ **Gestão de dados**: Limpar base de dados com confirmação dupla
- 📈 **Estatísticas**: Total de eventos, GPS, tipos
- ⚡ **Scraping em background**: Com polling de status

## 🐛 Troubleshooting

**Erro: "playwright not installed"**
```bash
playwright install chromium
```

**Erro: "Redis connection failed"**
- Verifica se Redis está a correr: `redis-cli ping`
- Ou desativa Redis no `.env` (usa cache em memória)

**Scraping muito lento**
- Aumenta `CONCURRENT_REQUESTS` no `.env`
- Reduz `SCRAPE_DELAY` (cuidado com rate limiting)

## 📄 Licença

MIT License

## 👨‍💻 Autor

Nuno Mansilhas
