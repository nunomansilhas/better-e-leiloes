# Prompt: AI Assistant Window - Current Problems

**Data:** 2026-01-16
**Branch anterior:** `claude/resume-previous-work-gQRMt`
**Novo branch sugerido:** `claude/fix-ai-assistant-<session-id>`

---

## TLDR - Contexto Rapido

Este projeto e um sistema de scraping/monitorizacao de leiloes judiciais portugueses (e-leiloes.pt). Tem integracao com **Ollama** para gerar dicas AI sobre eventos.

### Arquitetura AI

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │     │    Backend      │     │    Ollama       │
│   (Dashboard)   │────>│   (FastAPI)     │────>│  (Local LLM)    │
│                 │     │                 │     │                 │
│ AI Tips Panel   │     │ /api/ai/*       │     │ llama3.1:8b     │
│ Vehicle Analysis│     │ OllamaService   │     │ llava (vision)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Ficheiros AI Relevantes

| Ficheiro | Descricao | Linhas |
|----------|-----------|--------|
| `backend/services/ollama_service.py` | Comunicacao com Ollama | ~300 |
| `backend/services/ai_analysis_service.py` | Analise de imagens (LLaVA) | ~500 |
| `backend/services/ai_questions_service.py` | Perguntas automaticas sobre veiculos | ~1000 |
| `backend/services/market_price_service.py` | Precos de mercado + AI estimation | ~600 |
| `backend/routers/ai_tips_router.py` | Endpoints /api/ai/* | ~400 |
| `backend/ai_pipeline.py` | Pipeline de processamento batch | ~200 |

---

## Problemas Conhecidos

### 1. Ollama Connection Errors

**Sintoma:** AI tips falham silenciosamente, dashboard mostra "pending" forever

**Causa provavel:**
- Ollama nao esta a correr
- Modelo nao esta instalado
- Timeout muito curto

**Codigo relevante:** `backend/services/ollama_service.py:63-66`
```python
except httpx.ConnectError:
    return {"healthy": False, "error": "Cannot connect to Ollama. Is it running?"}
```

**Verificar:**
```bash
# Ollama esta a correr?
curl http://localhost:11434/api/tags

# Modelo existe?
ollama list
ollama pull llama3.1:8b
```

### 2. AI Tips Queue Stuck

**Sintoma:** Tips ficam em "processing" mas nunca completam

**Causa provavel:**
- Pipeline crashou sem marcar status
- Lock nao foi libertado

**Tabela:** `event_ai_tips` (status: pending/processing/completed/failed)

**Fix manual:**
```sql
UPDATE event_ai_tips SET status = 'pending' WHERE status = 'processing';
```

### 3. Vehicle Image Analysis (LLaVA) Fails

**Sintoma:** Analise de imagens de veiculos falha

**Causa provavel:**
- Modelo LLaVA nao instalado
- Imagem muito grande
- Timeout

**Codigo:** `backend/services/ai_analysis_service.py:177-230`

**Verificar:**
```bash
# LLaVA instalado?
ollama pull llava

# Testar
ollama run llava "Describe this image" --image test.jpg
```

### 4. Market Price AI Estimation Wrong

**Sintoma:** Precos estimados pelo AI sao incorretos

**Causa provavel:**
- Prompt mal formulado
- Modelo nao tem conhecimento de precos PT

**Codigo:** `backend/services/market_price_service.py:450-490`

### 5. Questions Service JSON Parse Errors

**Sintoma:** Respostas do AI nao sao parseadas corretamente

**Causa provavel:**
- AI devolve JSON invalido
- Markdown no output (```json blocks)

**Codigo:** `backend/services/ai_questions_service.py:1026-1037`

---

## Endpoints AI

| Method | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/ai/health` | Health check Ollama |
| GET | `/api/ai/tips` | Lista tips gerados |
| GET | `/api/ai/tips/{ref}` | Tip especifico |
| POST | `/api/ai/tips/{ref}/generate` | Gerar tip para evento |
| POST | `/api/ai/analyze-image` | Analise de imagem (LLaVA) |
| GET | `/api/ai/pipeline/status` | Estado do pipeline |
| POST | `/api/ai/pipeline/start` | Iniciar pipeline batch |

---

## Configuracao Ollama (.env)

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=120
```

---

## Tarefas Sugeridas

### Alta Prioridade

- [ ] Verificar porque AI tips ficam em "pending"
- [ ] Adicionar melhor error handling no pipeline
- [ ] Implementar retry logic para Ollama timeouts
- [ ] Adicionar logs detalhados no ai_pipeline.py

### Media Prioridade

- [ ] Melhorar prompts para precos de mercado PT
- [ ] Adicionar fallback quando LLaVA nao disponivel
- [ ] Cache de respostas AI (evitar reprocessar)

### Baixa Prioridade

- [ ] Dashboard: mostrar progresso do pipeline em tempo real
- [ ] Adicionar mais modelos de analise (veiculos vs imoveis)
- [ ] Exportar tips para PDF

---

## Como Testar

### 1. Health Check
```bash
curl http://localhost:8000/api/ai/health
```

Resposta esperada:
```json
{
  "service": "ollama",
  "status": "healthy",
  "details": {
    "healthy": true,
    "model": "llama3.1:8b",
    "model_available": true
  }
}
```

### 2. Gerar Tip
```bash
curl -X POST http://localhost:8000/api/ai/tips/NP1164212026/generate
```

### 3. Ver Tips
```bash
curl http://localhost:8000/api/ai/tips?status=completed
```

---

## Notas Adicionais

- O Ollama precisa de estar a correr ANTES do backend
- Modelos grandes (70B) podem dar timeout - usar 8B para testes
- LLaVA precisa de ~8GB RAM
- Pipeline batch processa 10 eventos de cada vez por defeito

---

## Leitura Recomendada

1. `README.md` - Arquitetura geral e regras criticas
2. `backend/README.md` - Detalhes do backend
3. `backend/services/ollama_service.py` - Como funciona a comunicacao

---

*Criado por AI assistant em 2026-01-16*
