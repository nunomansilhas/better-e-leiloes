"""
Quick test script to verify database statistics
"""
import asyncio
from database import get_db

async def test():
    async with get_db() as db:
        stats = await db.get_stats()

        print("\n📊 Database Statistics:")
        print(f"   Total Events: {stats['total_events']}")
        print(f"   Events with GPS: {stats['events_with_gps']}")
        print(f"\n📋 By Type:")
        for tipo, count in stats['by_type'].items():
            print(f"   {tipo}: {count}")

        # Get sample events
        events, total = await db.list_events(limit=5)
        print(f"\n🔍 Sample Events (showing 5 of {total}):")
        for event in events:
            print(f"   {event.reference} - {event.detalhes.tipo} - {event.valores.lanceAtual or 'N/A'}€")
            if event.dataFim:
                print(f"      Ends: {event.dataFim}")

asyncio.run(test())
