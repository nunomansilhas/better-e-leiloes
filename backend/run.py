"""
Wrapper de inicialização para Windows
Configura asyncio ANTES de qualquer import
"""

import sys
import os

# CRÍTICO: Configurar event loop policy ANTES de qualquer outra coisa
if sys.platform == 'win32':
    import asyncio
    # Força WindowsProactorEventLoopPolicy para suportar subprocessos
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✅ Windows event loop policy configurado: WindowsProactorEventLoopPolicy")

# Agora sim, importa e executa o main
if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    
    load_dotenv()
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    print(f"🚀 Iniciando servidor em {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Sem reload no Windows
        log_level="info"
    )
