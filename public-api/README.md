# Public API - Better E-Leiloes

API publica read-only para clientes (dashboard, extensoes, apps).

**Porta:** 3000

---

## TLDR - Para o Proximo AI

### ATENCAO - Modelo EventDB Separado!

Este projeto tem **DOIS modelos EventDB diferentes**:

| Ficheiro | Uso | Campos |
|----------|-----|--------|
| `backend/database.py` | Scraping/Admin | COMPLETO (~70 campos) |
| `public-api/database.py` | API Publica | SIMPLIFICADO (~30 campos) |

**Se adicionares campos ao backend, adiciona TAMBEM ao public-api!**

### Campos Que Faltavam (ja adicionados)

```python
# public-api/database.py - Campos adicionados:
observacoes: Mapped[Optional[str]]       # IMPORTANTE!
morada_cp: Mapped[Optional[str]]
cerimonia_data: Mapped[Optional[datetime]]
cerimonia_local: Mapped[Optional[str]]
cerimonia_morada: Mapped[Optional[str]]
gestor_nome: Mapped[Optional[str]]
gestor_email: Mapped[Optional[str]]
gestor_telefone: Mapped[Optional[str]]
gestor_tipo: Mapped[Optional[str]]
gestor_cedula: Mapped[Optional[str]]
```

### Endpoint /api/events/{reference}

Agora devolve TODOS os campos automaticamente:

```python
# Usa SQLAlchemy inspect para iterar todos os campos
for column in inspect(EventDB).mapper.column_attrs:
    data[column.key] = getattr(event, column.key, None)
```

### Diferenca do Backend

| Aspecto | Backend (8000) | Public-API (3000) |
|---------|----------------|-------------------|
| Escrita DB | Sim | Nao (read-only) |
| Scraping | Sim | Nao |
| Pipelines | Sim | Nao |
| Notificacoes | Gera | Le/Gere |
| Favoritos | Nao | Sim |
| Dashboard | Admin | Cliente |

---

## Estrutura

```
public-api/
├── main.py              # FastAPI app (~800 linhas)
├── database.py          # SQLAlchemy models (SIMPLIFICADO!)
├── requirements.txt     # Dependencias
├── .env.example         # Template configuracao
└── static/              # Dashboard HTML
```

## Quick Start

```bash
# Instalar
pip install -r requirements.txt

# Configurar
cp .env.example .env
nano .env  # Configurar DATABASE_URL

# Correr
uvicorn main:app --port 3000 --reload
```

## Endpoints

### Eventos

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/events/{ref}` | Detalhes completos |
| POST | `/api/events/batch` | Multiplos eventos |
| GET | `/api/ending-soon` | Eventos a terminar |
| GET | `/api/search` | Pesquisa eventos |

### Favoritos

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/favorites` | Lista favoritos |
| POST | `/api/favorites` | Adicionar favorito |
| DELETE | `/api/favorites/{ref}` | Remover favorito |

### Notificacoes

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/notifications` | Lista notificacoes |
| POST | `/api/notifications/{id}/read` | Marcar como lida |
| GET | `/api/notifications/rules` | Regras de notificacao |
| POST | `/api/notifications/rules` | Criar regra |

### Precos

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/price-history/{ref}` | Historico precos |
| GET | `/api/price-changes` | Mudancas recentes |

### Refresh

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/refresh-request/{ref}` | Pedir refresh ao backend |
| GET | `/api/refresh-status/{ref}` | Estado do pedido |

### Estatisticas

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/stats` | Estatisticas gerais |
| GET | `/api/stats/by-district` | Por distrito |
| GET | `/api/stats/by-type` | Por tipo |

## Configuracao (.env)

```env
# Database (mesmo que backend - read-only)
DATABASE_URL=mysql+aiomysql://user:pass@host:3306/eleiloes

# Opcional
API_AUTH_KEY=key-for-protected-endpoints
```

## Como Funciona

```
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│   Cliente   │───────>│ Public-API  │───────>│   MySQL     │
│ (Dashboard) │<───────│  (3000)     │<───────│  (events)   │
└─────────────┘        └─────────────┘        └─────────────┘
                              │
                              │ refresh-request
                              ▼
                       ┌─────────────┐
                       │   Backend   │
                       │   (8000)    │
                       └─────────────┘
```

1. Cliente pede dados ao Public-API
2. Public-API le da base de dados (read-only)
3. Se cliente quer refresh, cria entrada em `refresh_logs`
4. Backend processa `refresh_logs` e atualiza `events`
5. Proximo pedido do cliente tem dados atualizados

## Adicionar Novos Campos

Se precisares de expor um novo campo:

1. **Verificar se existe no backend** (`backend/database.py`)
2. **Adicionar ao modelo public-api** (`public-api/database.py`):
   ```python
   class EventDB(Base):
       # ... campos existentes ...
       novo_campo: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
   ```
3. **Reiniciar o servidor** - o endpoint `/api/events/{ref}` ja devolve automaticamente

## Notas

- Esta API e **read-only** - nao escreve na tabela `events`
- Pode escrever em `favorites`, `notifications`, `refresh_logs`
- O modelo EventDB e **simplificado** - nao tem todos os campos do backend
- Se um campo aparece null mas existe na DB, verificar se esta no modelo

---

MIT License - Nuno Mansilhas
