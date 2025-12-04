# 🚗 betterE-Leiloes v11.1

**Userscript Tampermonkey para melhorar a experiência no site e-leiloes.pt**

![Version](https://img.shields.io/badge/version-11.1-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Tampermonkey-red)

---

## 📋 Índice

- [Características](#-características)
- [Instalação](#-instalação)
- [Funcionalidades Principais](#-funcionalidades-principais)
- [Interface Visual](#-interface-visual)
- [Sistema de Cache](#-sistema-de-cache)
- [Recolha Automática](#-recolha-automática)
- [Estrutura de Dados](#-estrutura-de-dados)
- [Performance](#-performance)
- [Compatibilidade](#-compatibilidade)
- [Desenvolvimento](#-desenvolvimento)

---

## ✨ Características

### 🎨 **Design Modernizado**
- Cards com animações suaves e hover effects
- Gradientes e sombras profissionais
- Badges informativas com tooltips
- Layout responsivo e clean

### 🗺️ **Integração Google Maps**
- GPS com coordenadas exatas extraídas de cada leilão
- Abertura direta no Google Maps com localização precisa
- Cache de coordenadas para acesso rápido
- Ícone interativo com loading visual

### 📊 **Recolha Massiva de Dados**
- **Sistema automático** que percorre todas as páginas
- **Modal de progresso em tempo real** com:
  - Barra de progresso animada (0-100%)
  - Contador de páginas e eventos processados
  - Tempo decorrido, estimativa e tempo restante
  - Estatísticas de erros
- **Processamento paralelo** de 4 eventos simultâneos
- **Velocidade otimizada**: ~1.2s por evento

### 💾 **Sistema de Cache Inteligente**
- Armazenamento persistente em `localStorage`
- Cache incremental (só recolhe dados novos)
- Botão para limpar cache quando necessário
- Recuperação automática após reload

### 📈 **Informações Enriquecidas**
Cada evento recolhe automaticamente:
- 📍 **GPS**: Latitude e Longitude exatas
- 🏠 **Tipo**: Categoria do imóvel
- 🏘️ **Subtipo**: Subcategoria específica
- 🛏️ **Tipologia**: Ex: T2, T3, etc.
- 📐 **Áreas**:
  - Área Privativa
  - Área Dependente
  - Área Total

---

## 🔧 Instalação

### Pré-requisitos
1. **Navegador**: Chrome, Firefox, Edge ou Opera
2. **Extensão**: [Tampermonkey](https://www.tampermonkey.net/)

### Passos
1. Instala a extensão **Tampermonkey** no teu navegador
2. Clica no ícone do Tampermonkey → **Create a new script**
3. Cola todo o conteúdo do ficheiro `betterE-Leiloes-v11.0.user.js`
4. Guarda (Ctrl+S ou File → Save)
5. Acede a [e-leiloes.pt](https://www.e-leiloes.pt)
6. **Done!** 🎉

---

## 🎯 Funcionalidades Principais

### 1️⃣ **Cards Melhorados**

#### Antes ❌
- Layout básico
- Informação desorganizada
- Sem feedback visual

#### Depois ✅
- Design moderno com gradientes
- Valores inline: `VB: X € | VM: Y € | PMA: Z €`
- Badges de status:
  - ✓ Verde: Tem lances ativos
  - ✗ Vermelho: Sem lances
  - ? Info: Desconto face ao VM
- Data relativa: "Daqui a 5 dias" com tooltip da data exata
- Hover effect com zoom na imagem

### 2️⃣ **Google Maps com GPS Exato**

```javascript
// Clica no ícone 🗺️ ao lado da localização
// → Abre Google Maps com coordenadas precisas
// Exemplo: 41.1579, -8.6291
```

**Funcionalidades:**
- 🔍 Cache primeiro (instantâneo se já tiver)
- ⏳ Loading visual durante extração
- 🎯 Coordenadas GPS reais do leilão
- 🖱️ Ctrl+Click para forçar atualização

### 3️⃣ **Três Botões de Ação**

Posicionados no canto inferior direito:

#### 🔄 **Recolher Tudo** (Verde)
```
Posição: right: 152px
Função: Recolhe dados de TODAS as páginas automaticamente
Modal: Mostra progresso em tempo real com estimativas
```

**Features do Modal:**
- 📊 Estatísticas: Páginas, Eventos, Erros
- 📈 Barra de progresso animada com shimmer effect
- ⏱️ Tempo decorrido (mm:ss)
- 📊 Estimativa total (ex: "10-15 min")
- ⏳ Tempo restante (mm:ss)
- 🎨 Overlay com blur na página
- ❌ Não pode ser cancelado (segurança)

#### 📊 **Ver Dados** (Azul)
```
Posição: right: 86px
Função: Abre modal com tabela de todos os dados recolhidos
```

**Features do Modal:**
- 📋 Tabela completa com todas as colunas
- 🎨 Header sticky (fica fixo ao scroll)
- 🦓 Zebra striping nas linhas
- 🎨 Hover effects
- 🔍 Dados formatados:
  - Referências em azul e bold
  - GPS em verde monospace
  - Áreas alinhadas à direita com unidade
- ❌ Fecha com X, ESC ou clique fora
- 📭 Empty state se não houver dados

#### 🗑️ **Limpar Cache** (Vermelho)
```
Posição: right: 20px
Função: Limpa todo o localStorage
Confirmação: Obrigatória antes de executar
```

### 4️⃣ **Navegação Melhorada**

- **Click normal**: Abre leilão na mesma tab
- **Ctrl+Click**: Abre em nova tab
- **Scroll do rato**: Abre em nova tab
- **Badges não clicáveis**: Previne conflitos

### 5️⃣ **Recolha Automática por Página**

```javascript
// Sistema inteligente que deteta mudanças de página
// → Aguarda 2s para carregar
// → Melhora cards automaticamente
// → Recolhe dados novos em background
```

---

## 🎨 Interface Visual

### Cores e Gradientes

```css
/* Verde - Sucesso / Ações Positivas */
background: linear-gradient(135deg, #10b981 0%, #059669 100%);

/* Vermelho - Alertas / Ações Destrutivas */
background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);

/* Azul - Informação / Dados */
background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);

/* Laranja - Loading / Processamento */
background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
```

### Animações

- **fadeIn**: Entrada suave de overlays (0.2s)
- **slideUp**: Modal desliza de baixo (0.3s)
- **pulse**: Pulsação para badges urgentes (2s loop)
- **shimmer**: Efeito de brilho na barra de progresso (2s loop)
- **spin**: Rotação de spinners (0.8s loop)

---

## 💾 Sistema de Cache

### Estrutura localStorage

```javascript
Key: 'eleiloes_detalhes_cache'
Value: JSON.stringify([
  {
    reference: "NP241200003",
    gps: {
      latitude: "41.1579",
      longitude: "-8.6291"
    },
    detalhes: {
      tipo: "Imóvel Urbano",
      subtipo: "Apartamento",
      tipologia: "T2",
      areaPrivativa: "85.50",
      areaDependente: "12.00",
      areaTotal: "97.50"
    }
  },
  // ... mais eventos
])
```

### Funções de Cache

```javascript
loadCache()       // Carrega ao iniciar
saveCache()       // Guarda após updates
isInCache(ref)    // Verifica se existe
getCachedData(ref) // Obtém dados de uma ref
```

### Comportamento

1. **Page Load**: Carrega cache existente
2. **Recolha Normal**: Só processa novos eventos
3. **Recolha Forçada**: Reprocessa tudo (Ctrl+Click no Maps ou botão Recolher Tudo)
4. **Limpar**: Remove tudo e pede reload

---

## 🚀 Recolha Automática

### Processo Completo

```
1. Clica em "Recolher Tudo" 🔄
   ↓
2. Confirma quantidade (ex: 1207 eventos, 101 páginas)
   ↓
3. Modal de progresso aparece (overlay blur)
   ↓
4. Sistema processa:
   - Página atual (12 eventos)
   - Clica "Próxima" → Aguarda 2s
   - Processa nova página (12 eventos)
   - Repete até ao fim
   ↓
5. Modal fecha após 2s
   ↓
6. Alert com resumo final
   ↓
7. Dados disponíveis em:
   - window.eleiloesDetalhes (JS)
   - localStorage (persistente)
   - Modal "Ver Dados" 📊
```

### Otimizações de Performance

| Configuração | Valor | Motivo |
|-------------|-------|---------|
| Batch Size | 4 eventos | Paralelismo sem sobrecarregar |
| Batch Delay | 200ms | Evita rate limiting |
| Page Wait | 2000ms | Tempo para Vue.js renderizar |
| Iframe Timeout | 800ms | Suficiente para carregar detalhes |
| Progress Update | 500ms | Responsivo sem lag |

### Cálculo de Estimativa

```javascript
// Tempo médio por evento
avgTimePerEvent = elapsed / processedEvents

// Total estimado
estimatedTotal = avgTimePerEvent * totalEvents

// Intervalo (±10%)
minEstimate = estimatedTotal * 0.9
maxEstimate = estimatedTotal * 1.1

// Output: "10-15 min"
```

---

## 📊 Estrutura de Dados

### Array Global

```javascript
window.eleiloesDetalhes = [
  {
    reference: "NP241200003",
    gps: { latitude: "41.1579", longitude: "-8.6291" },
    detalhes: {
      tipo: "Imóvel Urbano",
      subtipo: "Apartamento",
      tipologia: "T2",
      areaPrivativa: "85.50",
      areaDependente: "12.00",
      areaTotal: "97.50"
    }
  }
]
```

### Acesso aos Dados

#### Console do Browser (F12)

```javascript
// Ver todos os dados
console.table(window.eleiloesDetalhes)

// Filtrar por tipo
window.eleiloesDetalhes.filter(d => d.detalhes.tipo === "Imóvel Urbano")

// Contar por tipologia
window.eleiloesDetalhes.reduce((acc, d) => {
  acc[d.detalhes.tipologia] = (acc[d.detalhes.tipologia] || 0) + 1
  return acc
}, {})

// Exportar como JSON
copy(JSON.stringify(window.eleiloesDetalhes, null, 2))
```

#### Modal Visual

```javascript
// Clica no botão azul 📊
// → Abre tabela com todos os dados
// → Scroll para ver tudo
// → Fecha com X, ESC ou clique fora
```

---

## ⚡ Performance

### Métricas

| Operação | Tempo | Notas |
|----------|-------|-------|
| Load Script | ~50ms | Injeção CSS + JS |
| Enhance Card | ~5ms | Por card individual |
| Extract GPS | ~800ms | Via iframe + Vue render |
| Extract Details | ~800ms | Incluído no GPS |
| Save Cache | ~10ms | localStorage write |
| Page Navigation | ~2s | Espera Vue.js |

### Otimizações Aplicadas

✅ **Paralelismo**: 4 iframes simultâneos
✅ **Delays reduzidos**: 200ms entre batches
✅ **Cache inteligente**: Só processa novos
✅ **Cleanup de iframes**: Previne memory leaks
✅ **Debounce de observers**: Evita reprocessamento
✅ **Batch updates**: Guarda cache no fim

### Estimativas Reais

```
100 eventos  ≈ 2 minutos
500 eventos  ≈ 10 minutos
1000 eventos ≈ 20 minutos
1500 eventos ≈ 30 minutos
```

---

## 🔧 Compatibilidade

### Navegadores Testados

| Browser | Versão | Status |
|---------|--------|--------|
| Chrome | 120+ | ✅ Funciona |
| Firefox | 120+ | ✅ Funciona |
| Edge | 120+ | ✅ Funciona |
| Opera | 105+ | ✅ Funciona |
| Safari | ❌ | Não testado |

### Requisitos

- **Tampermonkey**: v4.x ou superior
- **JavaScript**: ES6+ (async/await, arrow functions)
- **localStorage**: Ativo (quota ~5-10MB)
- **iframes**: Permitidos (mesma origem)

### Limitações Conhecidas

⚠️ **Vue.js SSR**: Precisa aguardar 800ms para render
⚠️ **Rate Limiting**: Processa 4 eventos/vez para evitar
⚠️ **localStorage Quota**: ~1000-1500 eventos máximo
⚠️ **Cross-Origin**: Só funciona em e-leiloes.pt

---

## 🛠️ Desenvolvimento

### Arquitetura

```
betterE-Leiloes v11.1
│
├── 🎨 Styles (GM_addStyle)
│   ├── Cards modernos
│   ├── Badges e tooltips
│   ├── Botões de ação
│   ├── Modal de progresso
│   └── Modal de dados
│
├── 🔧 Core Functions
│   ├── extractCardData()        # Extrai VB, VM, PMA, datas
│   ├── extractEventDetails()    # GPS + Detalhes via iframe
│   ├── collectAllDetails()      # Recolha em batch
│   ├── enhanceCard()            # Melhora visual do card
│   └── enhanceAllCards()        # Loop de todos os cards
│
├── 💾 Cache System
│   ├── loadCache()
│   ├── saveCache()
│   ├── isInCache()
│   └── getCachedData()
│
├── 🎨 UI Components
│   ├── createProgressModal()    # Modal de recolha
│   ├── openDataModal()          # Modal de tabela
│   ├── createClearCacheButton()
│   ├── createViewDataButton()
│   └── createCollectAllButton()
│
├── 🔄 Observers
│   ├── setupPaginationListeners() # Deteta mudança de página
│   └── MutationObserver          # Deteta novos cards
│
└── 🚀 Init
    └── init()                    # Ponto de entrada
```

### Fluxo de Execução

```
1. Script Load
   ↓
2. GM_addStyle (inject CSS)
   ↓
3. init() (após DOMContentLoaded)
   ↓
4. loadCache() → window.eleiloesDetalhes
   ↓
5. Create Buttons (após 1s)
   ↓
6. enhanceAllCards() (após 2s)
   ↓
7. collectAllDetails() auto (após 3s)
   ↓
8. setupPaginationListeners()
   ↓
9. MutationObserver ativo
   ↓
10. setInterval(enhanceAllCards, 5s)
```

### Debugging

#### Console Logs

```javascript
// Script iniciado
"🚗 betterE-Leiloes v11.1 INICIADO!"

// Cache carregado
"📦 Cache carregado: 150 eventos"

// Recolha em progresso
"🤖 Recolha automática: 8/12 novos"
"📊 2/8 (25%)"
"📊 4/8 (50%)"

// Página processada
"✅ Página 5 OK - Total: 60/1207 eventos"

// Concluído
"🎉 CONCLUÍDO: 1207/1207 eventos em 101/101 páginas"
```

#### Erros Comuns

```javascript
// Timeout do iframe (normal em conexões lentas)
"⚠️ NP241200003: Timeout"

// Botão próxima não disponível (última página)
"⚠️ Botão 'Próxima' não disponível"

// localStorage cheio
"⚠️ Erro ao guardar cache: QuotaExceededError"
```

### Extensibilidade

#### Adicionar Nova Coluna

```javascript
// 1. Atualizar extractEventDetails()
detalhes: {
  // ... campos existentes
  novoCampo: extractDetail('Novo Campo:')
}

// 2. Atualizar modal de dados
thead.innerHTML = `
  <tr>
    <!-- ... colunas existentes -->
    <th>Novo Campo</th>
  </tr>
`

row.innerHTML = `
  <!-- ... células existentes -->
  <td>${d.detalhes.novocamp || 'N/A'}</td>
`
```

#### Adicionar Nova Badge

```javascript
const badge3 = document.createElement('span');
badge3.className = 'eleiloes-badge success';
badge3.innerHTML = '🏆';
badge3.setAttribute('data-tooltip', 'Destaque!');
badgesContainer.appendChild(badge3);
```

---

## 📝 Changelog

### v11.1 (Current)
- ✅ Recolha automática de todas as páginas
- ✅ Modal de progresso com tempo real
- ✅ Estimativa em intervalo (ex: "10-15 min")
- ✅ Processamento paralelo 4x
- ✅ Cache incremental otimizado
- ✅ Delays reduzidos (2-3x mais rápido)
- ✅ Debug logs detalhados
- ✅ Cálculo baseado em eventos (não páginas)

### v11.0
- ✅ Modal de dados com tabela completa
- ✅ Sistema de 3 botões de ação
- ✅ Detecção de paginação automática
- ✅ Cache em localStorage
- ✅ GPS + 6 campos de detalhes

### v10.6
- ✅ Extração de áreas (3 campos)
- ✅ Badges com tooltips
- ✅ Google Maps com GPS exato

### v10.5
- ✅ Cards modernizados
- ✅ Valores inline
- ✅ Data relativa

---

## 📄 Licença

**MIT License**

```
Copyright (c) 2024 Nuno

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🤝 Contribuir

Contribuições são bem-vindas! 

### Como Contribuir

1. Fork este repositório
2. Cria um branch para a tua feature (`git checkout -b feature/AmazingFeature`)
3. Commit as tuas alterações (`git commit -m 'Add some AmazingFeature'`)
4. Push para o branch (`git push origin feature/AmazingFeature`)
5. Abre um Pull Request

### Guidelines

- Mantém o código limpo e comentado
- Testa extensivamente antes de submeter
- Atualiza o README se necessário
- Segue o estilo de código existente

---

## 📞 Suporte

### Issues Conhecidos

Se encontrares problemas:

1. **Verifica a consola** (F12 → Console)
2. **Limpa o cache** (botão vermelho 🗑️)
3. **Recarrega a página** (F5)
4. **Reinstala o script** se necessário

### Reportar Bugs

Ao reportar bugs, inclui:
- 📋 Versão do script
- 🌐 Navegador e versão
- 📝 Logs da consola
- 🎬 Passos para reproduzir
- 📸 Screenshots se aplicável

---

## ⭐ Créditos

- **Autor**: Nuno
- **Versão**: 11.1
- **Website**: [e-leiloes.pt](https://www.e-leiloes.pt)
- **Tampermonkey**: [tampermonkey.net](https://www.tampermonkey.net/)

---

## 🎯 Roadmap Futuro

### Possíveis Melhorias

- [ ] Exportar dados para CSV/Excel
- [ ] Filtros avançados na tabela
- [ ] Ordenação por colunas
- [ ] Gráficos e estatísticas
- [ ] Notificações de novos leilões
- [ ] Comparador de leilões
- [ ] Histórico de preços
- [ ] Sistema de favoritos
- [ ] Dark mode
- [ ] Multi-idioma

---

**Made with ❤️ for e-leiloes.pt users**

**Versão**: 11.1 | **Data**: Dezembro 2024 | **Status**: 🟢 Ativo
