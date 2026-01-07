# E-Leiloes Dashboard v2.1

Sistema de monitorização para **e-leiloes.pt** com dashboard web, notificações em tempo real e extensões browser.

## 🚀 Quick Install

### Extensão Browser (Recomendado)

<table>
<tr>
<td align="center" width="50%">

**🔧 Chrome/Edge Extension**

[![Install Extension](https://img.shields.io/badge/Chrome-Install_Extension-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white)](chrome-extension/)

1. Abre `chrome://extensions/`
2. Ativa **Modo de programador**
3. Clica **Carregar sem compactação**
4. Seleciona pasta `chrome-extension/`

</td>
<td align="center" width="50%">

**🐒 Tampermonkey Userscript**

[![Install Userscript](https://img.shields.io/badge/Tampermonkey-Install_Script-00485B?style=for-the-badge&logo=tampermonkey&logoColor=white)](https://raw.githubusercontent.com/nunomansilhas/better-e-leiloes/main/betterE-Leiloes-CardEnhancer.user.js)

1. Instala [Tampermonkey](https://www.tampermonkey.net/)
2. Clica no botão acima
3. Confirma instalação

</td>
</tr>
</table>

### Backend Server

```bash
# Clone & Install
git clone https://github.com/nunomansilhas/better-e-leiloes.git
cd better-e-leiloes/backend
pip install -r requirements.txt && playwright install chromium

# Configure .env
echo "DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/eleiloes" > .env

# Run
python run.py
```

Dashboard: **http://localhost:8000** | API Docs: **http://localhost:8000/docs**

---

## ✨ Features

| Feature | Dashboard | Extension |
|---------|:---------:|:---------:|
| Carrossel de imagens | ✅ | ✅ |
| Preços detalhados (VB/VA/VM/Lance) | ✅ | ✅ |
| Contagem regressiva | ✅ | ✅ |
| Google Maps integration | ✅ | ✅ |
| Notificações toast SSE | ✅ | - |
| Sistema de regras/alertas | ✅ | - |
| X-Monitor (price tracking) | ✅ | - |
| Filtros avançados | ✅ | - |
| Settings popup | - | ✅ |

## 📦 Componentes

```
better-e-leiloes/
├── backend/                 # FastAPI server
│   ├── main.py             # API endpoints + SSE
│   ├── auto_pipelines.py   # X-Monitor, Y-Sync
│   ├── notification_engine.py
│   └── static/index.html   # Dashboard SPA
├── chrome-extension/        # Browser extension (Manifest V3)
│   ├── manifest.json
│   ├── content.js          # Card enhancer
│   └── popup.html          # Settings UI
└── betterE-Leiloes-CardEnhancer.user.js  # Tampermonkey script
```

## ⚙️ Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11, FastAPI, Playwright, SQLAlchemy |
| **Database** | MySQL + aiomysql |
| **Cache** | Redis (opcional) |
| **Frontend** | Vanilla JS SPA |
| **Extension** | Chrome Manifest V3 |

## 🔄 Pipelines

| Pipeline | Intervalo | Função |
|----------|-----------|--------|
| **X-Monitor** | 5s - 10min | Tracking de preços por urgência |
| **Y-Sync** | 2h | Sync novos eventos + notificações |
| **Auto Pipeline** | 8h | Full scrape: IDs + Content + Images |

## 📡 API Endpoints

<details>
<summary>Eventos & Filtros</summary>

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/events` | Lista com paginação |
| GET | `/api/events/{ref}` | Detalhes evento |
| GET | `/api/stats` | Estatísticas |
| GET | `/api/filters/subtypes/{tipo}` | Subtipos |
| GET | `/api/filters/distritos/{tipo}` | Distritos |

</details>

<details>
<summary>Notificações</summary>

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/notifications` | Lista |
| GET | `/api/notifications/count` | Não lidas |
| POST | `/api/notifications/read-all` | Marcar lidas |
| DELETE | `/api/notifications/delete-all` | Eliminar |

</details>

<details>
<summary>Regras</summary>

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/notification-rules` | Lista |
| POST | `/api/notification-rules` | Criar |
| PUT | `/api/notification-rules/{id}` | Atualizar |
| DELETE | `/api/notification-rules/{id}` | Eliminar |
| POST | `/api/notification-rules/{id}/toggle` | Toggle |

</details>

<details>
<summary>SSE (Real-time)</summary>

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/live/events` | Stream SSE |

**Eventos:** `price_update`, `event_ended`, `connected`, `ping`

</details>

## 🔧 Configuração

### Backend (.env)

```env
DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/eleiloes
REDIS_URL=redis://localhost:6379  # opcional
API_PORT=8000
```

### Extension (via popup)

- URL da API: `http://localhost:8000/api`
- URL Dashboard: `http://localhost:8000`
- Timeouts: GET 3s, Scrape 10s

---

## 📄 License

MIT License - **Nuno Mansilhas**
