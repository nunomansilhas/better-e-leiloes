"""
Teste rápido para verificar se o scraper consegue extrair GPS
"""
import asyncio
import sys

# Fix Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from scraper import EventScraper

async def test():
    print("🧪 Testando extração de GPS...")
    
    scraper = EventScraper()
    await scraper.init_browser()
    
    try:
        # Testa com evento que sabemos ter GPS
        from models import ValoresLeilao
        
        preview = {
            'reference': 'NP1133692025',
            'valores': ValoresLeilao()
        }
        
        print(f"📍 Testando evento: {preview['reference']}")
        
        event_data = await scraper._scrape_event_details(preview, "imovel")
        
        print(f"\n✅ Resultado:")
        print(f"   Referência: {event_data.reference}")
        print(f"   Tipo: {event_data.detalhes.tipo}")
        print(f"   Subtipo: {event_data.detalhes.subtipo}")
        print(f"   Distrito: {event_data.detalhes.distrito}")
        print(f"   Concelho: {event_data.detalhes.concelho}")
        
        if event_data.gps and event_data.gps.latitude:
            print(f"\n🎯 GPS ENCONTRADO!")
            print(f"   Latitude: {event_data.gps.latitude}")
            print(f"   Longitude: {event_data.gps.longitude}")
        else:
            print(f"\n❌ GPS NÃO ENCONTRADO")
            
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(test())
