# Better E-Leilões - Extensão Chrome

Extensão Chrome nativa para melhorar a experiência do site E-Leilões.pt, com integração ao dashboard Better E-Leilões.

## Funcionalidades

- **Carrossel de Imagens**: Navega por todas as fotos do evento diretamente nos cards
- **Lightbox**: Clica numa imagem para ver em tamanho completo
- **Preços Detalhados**: Mostra VB, VA, VM e Lance atual de forma clara
- **Detalhes por Tipo**: Informação específica para imóveis (área, tipologia) e veículos (matrícula, marca, modelo)
- **Contagem Regressiva**: Timer em tempo real até ao fim do leilão
- **Integração GPS**: Abre localização no Google Maps
- **Botão Sync**: Atualiza dados do evento via API oficial
- **Dashboard Button**: Acesso rápido ao dashboard

## Instalação

### Modo Desenvolvedor (Chrome)

1. Abre `chrome://extensions/` no Chrome
2. Ativa o **Modo de programador** (canto superior direito)
3. Clica em **Carregar sem compactação**
4. Seleciona a pasta `chrome-extension`
5. A extensão está pronta a usar!

### Modo Desenvolvedor (Edge)

1. Abre `edge://extensions/` no Edge
2. Ativa o **Modo de desenvolvedor** (canto inferior esquerdo)
3. Clica em **Carregar descompactado**
4. Seleciona a pasta `chrome-extension`

## Configuração

Clica no ícone da extensão na barra de ferramentas para aceder às configurações:

- **URL da API**: Endereço do servidor backend (default: `http://localhost:8000/api`)
- **URL do Dashboard**: Endereço do dashboard (default: `http://localhost:8000`)
- **Enriquecimento via API**: Ativa/desativa a obtenção de dados extra
- **Máx. Imagens**: Número máximo de imagens no carrossel
- **Timeouts**: Tempos limite para pedidos à API

## Requisitos

- **Backend Better E-Leilões**: O servidor deve estar a correr em `localhost:8000` (ou o endereço configurado)
- **Chrome/Edge**: Versão 88 ou superior (Manifest V3)

## Estrutura

```
chrome-extension/
├── manifest.json      # Configuração da extensão
├── background.js      # Service worker para pedidos API
├── content.js         # Script que melhora os cards
├── content.css        # Estilos dos cards melhorados
├── popup.html         # Interface de configurações
├── popup.js           # Lógica do popup
└── icons/             # Ícones da extensão
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

## Desenvolvimento

Para fazer alterações:

1. Edita os ficheiros necessários
2. Vai a `chrome://extensions/`
3. Clica no botão de reload (↻) da extensão
4. Recarrega a página do E-Leilões

## Diferenças do Userscript

| Funcionalidade | Userscript | Extensão Chrome |
|---------------|------------|-----------------|
| Instalação | Requer Tampermonkey | Nativa do browser |
| Configuração | Editar código | Interface gráfica |
| Permissões | GM_xmlhttpRequest | Fetch API nativa |
| Armazenamento | N/A | chrome.storage.sync |
| Atualizações | Manual | Pode ser automático |

## Autor

**Nuno Mansilhas** - [GitHub](https://github.com/nunomansilhas)

## Licença

MIT License
