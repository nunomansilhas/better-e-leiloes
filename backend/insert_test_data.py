"""
Script to insert test data into the database
"""
import asyncio
from database import init_db, get_db
from models import EventData, ValoresLeilao, EventDetails, GPSCoordinates
from datetime import datetime, timedelta

async def insert_test_events():
    """Insert some test events into the database"""
    await init_db()

    # Create test event 1 - Imóvel
    event1 = EventData(
        reference="LO1421072025",
        tipoEvento="imovel",
        valores=ValoresLeilao(
            valorBase=134380.00,
            valorAbertura=None,
            valorMinimo=114223.00,
            lanceAtual=67861.90
        ),
        gps=GPSCoordinates(
            latitude=40.5518,
            longitude=-8.4229
        ),
        detalhes=EventDetails(
            tipo="Moradia",
            subtipo="",
            tipologia="T3",
            areaPrivativa=150.0,
            areaDependente=50.0,
            areaTotal=200.0,
            distrito="Aveiro",
            concelho="Santa Maria da Feira",
            freguesia="Gualtar",
            matricula=""
        ),
        imagens=[
            "https://www.e-leiloes.pt/api/files/Verbas_Fotos/verba_119204/11072025134623_800sm.jpg",
            "https://www.e-leiloes.pt/api/files/Verbas_Fotos/verba_119204/11072025134624_800sm.jpg"
        ],
        dataInicio=datetime(2025, 11, 8),
        dataFim=datetime(2025, 12, 16, 10, 0, 0),
        descricao="<p>Moradia T3 em Gualtar</p>",
        observacoes=None,
        onuselimitacoes=None,
        descricaoPredial=None,
        cerimoniaEncerramento=None,
        agenteExecucao=None,
        dadosProcesso=None
    )

    # Create test event 2 - Imóvel
    event2 = EventData(
        reference="LO1411062025",
        tipoEvento="imovel",
        valores=ValoresLeilao(
            valorBase=470588.50,
            valorAbertura=None,
            valorMinimo=400000.23,
            lanceAtual=277750.00
        ),
        gps=GPSCoordinates(
            latitude=40.5659,
            longitude=-8.7491
        ),
        detalhes=EventDetails(
            tipo="Moradia",
            subtipo="Moderna",
            tipologia="T4",
            areaPrivativa=250.0,
            areaDependente=100.0,
            areaTotal=350.0,
            distrito="Aveiro",
            concelho="Vagos",
            freguesia="",
            matricula=""
        ),
        imagens=[
            "https://www.e-leiloes.pt/api/files/Verbas_Fotos/verba_120906/13102025162059_800sm.jpg"
        ],
        dataInicio=datetime(2025, 11, 8),
        dataFim=datetime(2025, 12, 16, 10, 0, 0),
        descricao="<p>MORADIA MODERNA TIPO T4 - Benfeitorias</p>",
        observacoes=None,
        onuselimitacoes=None,
        descricaoPredial=None,
        cerimoniaEncerramento=None,
        agenteExecucao=None,
        dadosProcesso=None
    )

    # Create test event 3 - Garagem
    event3 = EventData(
        reference="LO1418412025",
        tipoEvento="imovel",
        valores=ValoresLeilao(
            valorBase=64700.00,
            valorAbertura=None,
            valorMinimo=54995.00,
            lanceAtual=32350.00
        ),
        gps=GPSCoordinates(
            latitude=41.5032,
            longitude=-8.1843
        ),
        detalhes=EventDetails(
            tipo="Garagem / Arrumos",
            subtipo="",
            tipologia="",
            areaPrivativa=100.0,
            areaDependente=None,
            areaTotal=100.0,
            distrito="Braga",
            concelho="Fafe",
            freguesia="Golães",
            matricula=""
        ),
        imagens=[
            "https://www.e-leiloes.pt/api/files/Verbas_Fotos/verba_121512/27102025114814_800sm.jpg"
        ],
        dataInicio=datetime(2025, 11, 8),
        dataFim=datetime(2025, 12, 16, 10, 0, 0),
        descricao="<p>*GARAGEM / ARMAZÉM EM GOLÃES - FAFE*</p>",
        observacoes=None,
        onuselimitacoes=None,
        descricaoPredial=None,
        cerimoniaEncerramento=None,
        agenteExecucao=None,
        dadosProcesso=None
    )

    # Save events to database
    async with get_db() as db:
        await db.save_event(event1)
        await db.save_event(event2)
        await db.save_event(event3)
        print("✅ 3 test events inserted successfully!")

        # Verify
        events, total = await db.list_events(page=1, limit=10)
        print(f"📊 Total events in DB: {total}")
        for event in events:
            print(f"  - {event.reference}: {event.detalhes.tipo} em {event.detalhes.distrito}")

if __name__ == "__main__":
    asyncio.run(insert_test_events())
