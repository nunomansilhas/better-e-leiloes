# 🏠 betterE-Leiloes v12.4

Extensão Tampermonkey + API Backend para melhorar a experiência de navegação no **e-leiloes.pt** com dados completos de leilões (valores, GPS, detalhes).

## 📦 Componentes

### 🎨 Frontend (Extensão Browser)
- **Arquivo**: `betterE-Leiloes-v12.0-API.user.js`
- **Versão**: 12.4
- **Plataforma**: Tampermonkey (Chrome, Firefox, Edge)
- **Features**:
  - 🏷️ Badges nos cards: GPS, Valores, Detalhes
  - 📊 Modal de visualização: Lista e grelha compacta
  - 🔍 Filtros avançados: Tipo de evento (imóvel/móvel) e distrito
  - 🗑️ Gestão de dados: Limpar base de dados
  - 📈 Estatísticas: Total de eventos, tipos
  - ⚡ Scraping em background com polling

### 🚀 Backend (API)
- **Diretório**: `backend/`
- **Framework**: FastAPI + Playwright
- **Base de dados**: SQLite (async)
- **Cache**: Redis ou memória
- **Features**:
  - ✅ REST API completa
  - ✅ Two-phase scraping (listing + details)
  - ✅ Suporte para imóveis e móveis
  - ✅ Valores de leilão completos
  - ✅ GPS para imóveis
  - ✅ Filtros avançados
  - ✅ Background tasks

## 🚀 Quick Start

### 1. Backend API

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
python run.py
```

API disponível em: **http://localhost:8000**

### 2. Frontend (Extensão)

1. Instala [Tampermonkey](https://www.tampermonkey.net/)
2. Abre `betterE-Leiloes-v12.0-API.user.js`
3. Clica "Install"
4. Navega para [e-leiloes.pt](https://www.e-leiloes.pt)

### 3. Usar a Extensão

1. **Recolher dados**: Clica "📥 Recolher Tudo (API)" (scraping automático)
2. **Ver dados**: Clica "👁️ Ver Dados" (modal com filtros)
3. **Alternar vista**: Usa botões `☰` (lista) e `▦` (grelha)
4. **Filtrar**: Seleciona tipo (imóvel/móvel) e/ou distrito

## 📊 Arquitetura

```
┌─────────────────────────┐
│  Browser Extension      │
│  (Tampermonkey)         │
│  v12.4                  │
└───────────┬─────────────┘
            │ HTTP
            ▼
┌─────────────────────────┐
│  FastAPI Backend        │
│  Port 8000              │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐      ┌──────────────────┐
│  SQLite Database        │      │  Playwright      │
│  (eleiloes.db)          │      │  (Scraper)       │
└─────────────────────────┘      └──────────────────┘
```

## 🎯 Features v12.4

### Backend
- ✅ Endpoint `/api/events?tipo_evento=imovel` (filtro funcional)
- ✅ Endpoint `DELETE /api/database` (gestão de dados)
- ✅ Schema completo: `tipo_evento`, `valores`, `gps`, `detalhes`
- ✅ Two-phase scraping otimizado
- ✅ Suporte completo para móveis e imóveis

### Frontend
- 🎨 Ícones melhorados: `☰` lista, `▦` grelha
- 🔍 Filtros funcionais por tipo de evento
- 📊 Cards compactos responsivos em grelha
- 🗑️ Limpar base de dados com dupla confirmação
- ⚡ Auto-reload após operações

## 📚 Documentação

- **Backend API**: Ver [backend/README.md](backend/README.md)
- **Instalação**: Ver [INSTALL.md](INSTALL.md)
- **API Docs**: http://localhost:8000/docs (Swagger)

## 🔧 Configuração

### Backend (.env)
```env
API_HOST=0.0.0.0
API_PORT=8000
DATABASE_URL=sqlite+aiosqlite:///./eleiloes.db
SCRAPE_DELAY=0.8
CONCURRENT_REQUESTS=4
```

### Frontend (JS)
```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000/api',
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000,
    POLL_INTERVAL: 2000
};
```

## 📈 Estatísticas de Scraping

**Two-Phase Strategy:**
- Fase 1 (Listing): ~4 páginas (2 imóveis + 2 móveis)
- Fase 2 (Details): ~24 eventos em paralelo
- Tempo total: ~2 minutos
- Stop automático em páginas vazias

## 🐛 Troubleshooting

**Extensão não conecta à API:**
```bash
# Verifica se o servidor está a correr
curl http://localhost:8000/

# Vê logs do servidor
cd backend
python run.py
```

**Scraping não funciona:**
```bash
# Reinstala playwright
playwright install chromium

# Testa manualmente
curl -X POST http://localhost:8000/api/scrape/all
```

**Filtros não funcionam:**
- F5 no browser (força reload da extensão v12.4)
- Verifica versão no painel: deve ser v12.4
- Abre consola do browser (F12) e procura erros

## 🤝 Contribuir

1. Fork o projeto
2. Cria branch: `git checkout -b feature/nova-feature`
3. Commit: `git commit -m 'Add nova feature'`
4. Push: `git push origin feature/nova-feature`
5. Abre Pull Request

## 📄 Licença

MIT License

## 👨‍💻 Autor

**Nuno Mansilhas**

---

⭐ **Se gostaste do projeto, dá uma estrela no GitHub!**
