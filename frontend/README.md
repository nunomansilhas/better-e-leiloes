# Frontend - Better E-Leiloes

Clientes para visualizacao de leiloes: Dashboard, Chrome Extension e Userscript.

---

## TLDR - Para o Proximo AI

### Arquitetura

```
┌────────────────────────────────────────────────────────────┐
│                        FRONTENDS                            │
├──────────────────┬──────────────────┬──────────────────────┤
│   dashboard.html │ Chrome Extension │    Userscript        │
│   (standalone)   │    (nativo)      │  (Tampermonkey)      │
├──────────────────┴──────────────────┴──────────────────────┤
│                           │                                 │
│                           ▼                                 │
│                    Public-API (3000)                        │
│                           │                                 │
│                           ▼                                 │
│                      MySQL (events)                         │
└────────────────────────────────────────────────────────────┘
```

### Portas

| Componente | Porta | URL |
|------------|-------|-----|
| Backend (admin) | 8000 | `http://localhost:8000` |
| Public-API | 3000 | `http://localhost:3000` |
| Dashboard | - | Abrir ficheiro ou servir |

### Configuracao API

Todos os clientes apontam para `localhost:3000` por defeito.

Para producao, alterar:
- `dashboard.html`: variavel `API_BASE`
- `chrome-extension/popup.js`: settings
- `userscript`: constante `CONFIG.API_BASE`

---

## Estrutura

```
frontend/
├── dashboard.html                      # Dashboard standalone
├── betterE-Leiloes-CardEnhancer.user.js  # Tampermonkey userscript
└── chrome-extension/                   # Chrome extension
    ├── manifest.json                   # Config extensao
    ├── background.js                   # Service worker
    ├── content.js                      # Injeta nos cards
    ├── content.css                     # Estilos cards
    ├── popup.html                      # Popup settings
    ├── popup.js                        # Logica popup
    └── icons/                          # Icones
```

## Dashboard

Dashboard web completo para visualizacao de leiloes.

### Funcionalidades

- Lista de eventos com filtros (tipo, distrito, preco)
- Detalhes completos de cada evento
- Historico de precos (graficos)
- Favoritos e notificacoes
- Estatisticas e metricas
- Updates em tempo real (SSE)

### Uso

```bash
# Opcao 1: Abrir diretamente
open dashboard.html

# Opcao 2: Servir com Python
python -m http.server 8080
# Abrir http://localhost:8080/dashboard.html

# Opcao 3: O public-api serve em /static
# http://localhost:3000/static/dashboard.html
```

### Configuracao

No inicio do ficheiro:

```javascript
const API_BASE = 'http://localhost:3000';  // Alterar para producao
```

## Chrome Extension

Extensao nativa para Chrome/Edge que melhora os cards no site e-leiloes.pt.

### Funcionalidades

- Carrossel de imagens
- Lightbox para fotos
- Precos detalhados (VB, VA, VM, Lance)
- Info especifica por tipo (imoveis, veiculos)
- Contagem regressiva
- Integracao GPS (Google Maps)
- Botao sync para atualizar dados
- Acesso rapido ao dashboard

### Instalacao

```
1. Chrome: chrome://extensions/
2. Ativar "Developer mode"
3. "Load unpacked" > selecionar pasta chrome-extension/
```

### Configuracao

Clicar no icone da extensao para aceder a:

- URL da API
- URL do Dashboard
- Ativar/desativar enriquecimento
- Numero max de imagens
- Timeouts

## Userscript (Tampermonkey)

Script para Tampermonkey/Greasemonkey que melhora o site e-leiloes.pt.

### Funcionalidades

- Enriquece cards com dados da API
- Adiciona imagens carousel
- Mostra precos atualizados
- Links rapidos para dashboard

### Instalacao

```
1. Instalar Tampermonkey (Chrome) ou Greasemonkey (Firefox)
2. Abrir ficheiro .user.js
3. Clicar "Install"
```

### Configuracao

Editar constantes no inicio do script:

```javascript
const CONFIG = {
    API_BASE: 'http://localhost:3000',
    DASHBOARD_URL: 'http://localhost:3000/static/dashboard.html',
    // ...
};
```

## Comparacao

| Funcionalidade | Dashboard | Extension | Userscript |
|---------------|-----------|-----------|------------|
| Standalone | Sim | Nao | Nao |
| Requer browser | Qualquer | Chrome/Edge | Chrome/Firefox |
| Config grafica | Nao | Sim | Nao |
| Auto-update | Manual | Pode ser | Manual |
| Injeta em e-leiloes.pt | Nao | Sim | Sim |

## Desenvolvimento

### Dashboard

Editar `dashboard.html` e recarregar pagina.

### Extension

```
1. Editar ficheiros
2. chrome://extensions > reload (↻)
3. Recarregar pagina e-leiloes.pt
```

### Userscript

```
1. Editar no Tampermonkey
2. Recarregar pagina e-leiloes.pt
```

---

MIT License - Nuno Mansilhas
