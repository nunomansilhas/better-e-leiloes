# 🚀 Guia de Instalação Rápida - betterE-Leiloes v12.0

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    NOVA ARQUITETURA v12.0                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Browser (Tampermonkey)          Python Backend (FastAPI)    │
│  ┌───────────────────┐           ┌────────────────────┐     │
│  │ betterE-Leiloes   │◀────API───│  FastAPI Server    │     │
│  │   v12.0 Script    │           │  (localhost:8000)  │     │
│  └───────────────────┘           └────────────────────┘     │
│          │                                 │                 │
│          │ Mostra dados                    │ Scraping        │
│          ▼                                 ▼                 │
│  ┌───────────────────┐           ┌────────────────────┐     │
│  │  e-leiloes.pt     │           │  e-leiloes.pt      │     │
│  │    (Website)      │           │  (Playwright)      │     │
│  └───────────────────┘           └────────────────────┘     │
│                                            │                 │
│                                            ▼                 │
│                                   ┌────────────────────┐     │
│                                   │  SQLite Database   │     │
│                                   │   + Redis Cache    │     │
│                                   └────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

**O que mudou?**
- ❌ **Antes (v11.x)**: Browser scraping direto (lento, instável)
- ✅ **Agora (v12.0)**: API centralizada (rápido, confiável)

---

## 📦 Parte 1: Instalar o Backend (Servidor)

### Passo 1: Requisitos
```powershell
# Verifica Python (precisa 3.10+)
python --version

# Se não tiver Python:
# Baixa de: https://www.python.org/downloads/
```

### Passo 2: Setup Automático
```powershell
# Vai para o diretório backend
cd c:\Users\mansi\Downloads\e-leiloes-aux\backend

# Executa o script de setup
python setup.py
```

O script `setup.py` vai:
1. ✅ Criar virtual environment
2. ✅ Instalar todas as dependências
3. ✅ Instalar Playwright browser
4. ✅ Criar arquivo `.env`
5. ✅ Testar se tudo funciona

**Tempo estimado:** 3-5 minutos

### Passo 3: Iniciar o Servidor
```powershell
# Ativa o ambiente virtual
.\venv\Scripts\activate

# Inicia o servidor
python main.py
```

**Verifica se funcionou:**
- Abre navegador: http://localhost:8000
- Deves ver: `{"status": "online", "version": "1.0.0"}`
- Swagger docs: http://localhost:8000/docs

---

## 🌐 Parte 2: Instalar a Extensão (Browser)

### Passo 1: Instalar Tampermonkey
1. Abre Chrome/Edge/Firefox
2. Vai para a loja de extensões:
   - Chrome: https://chrome.google.com/webstore
   - Firefox: https://addons.mozilla.org
3. Procura por "Tampermonkey"
4. Clica "Adicionar ao navegador"

### Passo 2: Instalar o Script
1. Abre o Tampermonkey (ícone no browser)
2. Clica "Create a new script"
3. Apaga tudo
4. Copia TUDO de `betterE-Leiloes-v12.0-API.user.js`
5. Cola no editor
6. Clica File > Save (ou Ctrl+S)

### Passo 3: Testar
1. Vai para https://www.e-leiloes.pt
2. Deves ver no canto inferior direito:
   ```
   ┌─────────────────────────┐
   │ 🚀 betterE-Leiloes v12.0│
   │ ┌─────────────────────┐ │
   │ │📥 Recolher Tudo (API)│ │
   │ │👁️ Ver Dados         │ │
   │ │📊 Estatísticas       │ │
   │ │🗑️ Limpar Cache API  │ │
   │ └─────────────────────┘ │
   └─────────────────────────┘
   ```

---

## 🎯 Como Usar

### Recolher Dados Pela Primeira Vez

1. **Inicia o scraping no servidor:**
   ```
   Clica no botão: 📥 Recolher Tudo (API)
   ```
   - Confirma a ação
   - O servidor vai começar a recolher TODOS os eventos
   - ⏱️ Pode demorar 1-2 horas (depende do total de eventos)

2. **Acompanha o progresso:**
   ```
   Clica no botão: 📊 Estatísticas
   ```
   - Mostra quantos eventos já foram recolhidos
   - Mostra se o scraper está a correr

3. **Ver os dados:**
   ```
   Clica no botão: 👁️ Ver Dados
   ```
   - Abre modal com todos os eventos
   - Paginação: 20 eventos por página
   - Filtros: por tipo ou distrito
   - Botão "Ver no Mapa" em cada evento

### Uso Diário

Depois do primeiro scraping completo:

1. **Na página de listagem:**
   - Os cards já mostram badges automáticos:
     - 📍 GPS (clica para abrir Google Maps)
     - 📋 Detalhes (tipo, área, etc.)

2. **Ver dados específicos:**
   - Clica "👁️ Ver Dados"
   - Filtra por tipo: "Apartamento"
   - Filtra por distrito: "Lisboa"

3. **Atualizar dados:**
   - Se quiser re-scrape: "📥 Recolher Tudo (API)"
   - Se quiser limpar cache: "🗑️ Limpar Cache API"

---

## 🔧 Configuração Avançada

### Mudar URL da API

Se instalares o backend noutro servidor:

1. Edita `betterE-Leiloes-v12.0-API.user.js`
2. Muda linha 14:
   ```javascript
   API_BASE_URL: 'http://localhost:8000/api',
   // Para:
   API_BASE_URL: 'http://teu-servidor.com:8000/api',
   ```

### Configurar Backend

Edita `backend/.env`:

```env
# Porta do servidor
API_PORT=8000

# Velocidade do scraping
SCRAPE_DELAY=0.8  # Segundos entre requests
CONCURRENT_REQUESTS=4  # Quantos simultâneos

# Redis (opcional)
REDIS_URL=redis://localhost:6379
```

**Scraping mais rápido:**
- Diminui `SCRAPE_DELAY` (ex: 0.5)
- Aumenta `CONCURRENT_REQUESTS` (ex: 6)
- ⚠️ Cuidado: muito rápido pode ser bloqueado

**Scraping mais seguro:**
- Aumenta `SCRAPE_DELAY` (ex: 1.5)
- Diminui `CONCURRENT_REQUESTS` (ex: 2)

---

## 🐳 Deploy em Servidor

### Opção 1: Docker (Recomendado)

```bash
# No servidor
cd backend

# Cria Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium
COPY . .
CMD ["python", "main.py"]
EOF

# Build e run
docker build -t eleiloes-api .
docker run -d -p 8000:8000 --name eleiloes-api eleiloes-api
```

### Opção 2: systemd Service

```bash
# Cria service file
sudo nano /etc/systemd/system/eleiloes-api.service
```

```ini
[Unit]
Description=E-Leiloes API Backend
After=network.target

[Service]
Type=simple
User=teu-user
WorkingDirectory=/caminho/para/backend
Environment="PATH=/caminho/para/backend/venv/bin"
ExecStart=/caminho/para/backend/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Ativa e inicia
sudo systemctl enable eleiloes-api
sudo systemctl start eleiloes-api
sudo systemctl status eleiloes-api
```

### Opção 3: Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name teu-dominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## ❓ Troubleshooting

### Backend não inicia

**Erro: "playwright not installed"**
```bash
playwright install chromium
```

**Erro: "Redis connection failed"**
- Redis é opcional
- O sistema usa memória se Redis não disponível
- Para instalar Redis: https://redis.io/download

**Erro: "Port 8000 already in use"**
```bash
# Muda porta no .env
API_PORT=8001
```

### Extensão não funciona

**Erro no console: "Failed to fetch"**
- Verifica se backend está a correr: http://localhost:8000
- Verifica URL no script (linha 14)
- Verifica CORS no backend (`ALLOWED_ORIGINS` no `.env`)

**Badges não aparecem**
- Abre DevTools (F12) > Console
- Vê se há erros
- Verifica se API responde: http://localhost:8000/api/events

**Botões não fazem nada**
- Recarrega a página (F5)
- Verifica se Tampermonkey está ativo
- Vê console do browser

---

## 📊 Comparação v11 vs v12

| Feature                  | v11.x (Cliente) | v12.0 (API)      |
|-------------------------|-----------------|------------------|
| **Velocidade**          | ~10-15 min      | 1-2h inicial     |
| **Uso depois**          | Scrape sempre   | Instantâneo      |
| **Confiabilidade**      | Instável        | Robusto          |
| **Múltiplos users**     | Cada um scrape  | Dados partilhados|
| **Cache**               | localStorage    | Redis + DB       |
| **Background**          | Não             | Sim              |
| **Histórico**           | Não             | Sim (database)   |
| **Filtros avançados**   | Limitado        | Full SQL         |

---

## 🎉 Próximos Passos

Depois de tudo instalado:

1. ✅ **Primeiro scraping**: Deixa correr durante a noite
2. ✅ **Teste a extensão**: Navega no site, vê badges
3. ✅ **Explora o Swagger**: http://localhost:8000/docs
4. ✅ **Deploy no servidor**: Usa Docker ou systemd
5. ✅ **Configura SSL**: Usa Let's Encrypt

---

## 📞 Suporte

- **Documentação API**: http://localhost:8000/docs
- **Logs do servidor**: Console onde corres `python main.py`
- **Logs do browser**: F12 > Console

**Happy scraping! 🚀**
