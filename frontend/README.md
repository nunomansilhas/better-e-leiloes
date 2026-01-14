# Frontend - E-Leiloes

Este folder contém os ficheiros do frontend para o utilizador final.

## Estrutura

```
frontend/
├── dashboard.html              # Dashboard completo para visualização de leilões
├── betterE-Leiloes-CardEnhancer.user.js  # Tampermonkey/Greasemonkey userscript
└── chrome-extension/           # Chrome extension
    ├── manifest.json
    ├── background.js
    ├── content.js
    ├── content.css
    ├── popup.html
    ├── popup.js
    └── icons/
```

## Dashboard

O `dashboard.html` é uma página standalone que se liga à API do backend para mostrar:
- Lista de leilões com filtros
- Preços em tempo real via SSE
- Notificações
- Estatísticas

**Para usar:** Abre o ficheiro no browser ou serve via webserver.

## Tampermonkey Script

O `betterE-Leiloes-CardEnhancer.user.js` melhora a experiência no site e-leiloes.pt:
- Enriquece os cards com dados da API
- Adiciona imagens carousel
- Mostra preços atualizados

**Instalação:**
1. Instala o Tampermonkey (Chrome) ou Greasemonkey (Firefox)
2. Abre o ficheiro `.user.js`
3. Clica "Install"

## Chrome Extension

Extensão para Chrome com funcionalidades extra:
- Popup com estatísticas rápidas
- Integração com a API

**Instalação:**
1. Chrome > `chrome://extensions`
2. Ativa "Developer mode"
3. "Load unpacked" > seleciona a pasta `chrome-extension/`

## Configuração

Todos os componentes apontam para `localhost:8000` por defeito.
Para produção, atualiza:
- `dashboard.html`: variável `API_BASE`
- `userscript`: constante `CONFIG.API_BASE`
- `chrome-extension/background.js`: URL da API
