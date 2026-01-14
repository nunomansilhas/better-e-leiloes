# E-Leiloes Backend API

Backend para scraping e streaming de dados do e-leiloes.pt.

## Quick Start

```bash
cd backend
pip install -r requirements.txt
playwright install chromium

# Configure .env
cp .env.example .env
# Edit DATABASE_URL, REDIS_URL, etc.

# Run
python run.py
```

**Admin Panel:** http://localhost:8000
**API Docs:** http://localhost:8000/docs

## Structure

```
backend/
├── main.py              # FastAPI API
├── scraper.py           # Playwright scraper
├── auto_pipelines.py    # X-Monitor, Y-Sync, Z-Watch
├── database.py          # MySQL/SQLAlchemy
├── static/index.html    # Admin panel
└── migrations/          # SQL schemas
```

## Pipelines

| Pipeline | Interval | Function |
|----------|----------|----------|
| **X-Monitor** | 5s-10min | Price tracking (urgent events) |
| **Y-Sync** | 2h | Sync new events + mark finished |
| **Z-Watch** | 10min | Watch for new events |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/events` | List events |
| GET | `/api/events/{ref}` | Event details |
| GET | `/api/stats` | Statistics |
| POST | `/api/pipeline/api` | Run scrape pipeline |
| GET | `/api/live/events` | SSE stream |

## Config (.env)

```env
DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/eleiloes
REDIS_URL=redis://localhost:6379
API_PORT=8000
API_AUTH_KEY=your-secret-key
```

## Deploy (cPanel)

Uses `passenger_wsgi.py` for Passenger WSGI hosting.

---

MIT License - Nuno Mansilhas
