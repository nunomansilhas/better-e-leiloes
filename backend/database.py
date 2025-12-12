"""
Database layer usando SQLAlchemy + SQLite
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select, func, String, Float, DateTime, Text
from typing import List, Tuple, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import os
import json

from models import (
    EventData, GPSCoordinates, EventDetails, ValoresLeilao,
    DescricaoPredial, CerimoniaEncerramento, AgenteExecucao, DadosProcesso
)

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./eleiloes.db")

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class EventDB(Base):
    """Tabela de eventos"""
    __tablename__ = "events"
    
    reference: Mapped[str] = mapped_column(String, primary_key=True)
    tipo_evento: Mapped[str] = mapped_column(String)  # "imovel" ou "movel"
    
    # Valores do leilão
    valor_base: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valor_abertura: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valor_minimo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lance_atual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # GPS (apenas imóveis)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Detalhes comuns
    tipo: Mapped[str] = mapped_column(String, default="N/A")
    subtipo: Mapped[str] = mapped_column(String, default="N/A")
    
    # Detalhes IMOVEIS
    tipologia: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    area_privativa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    area_dependente: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    area_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    distrito: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    concelho: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    freguesia: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Detalhes MOVEIS
    matricula: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Datas do evento
    data_inicio: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_fim: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Galeria e textos descritivos (HTML)
    imagens: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of URLs
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # HTML
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # HTML
    onuselimitacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # HTML - NOVO

    # Informações adicionais (HTML completo)
    descricao_predial: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # HTML
    cerimonia_encerramento: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # HTML
    agente_execucao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # HTML
    dados_processo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # HTML

    # Metadados
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def to_model(self) -> EventData:
        """Converte DB model para Pydantic model"""
        # Deserializa apenas imagens (JSON)
        imagens_list = json.loads(self.imagens) if self.imagens else []

        return EventData(
            reference=self.reference,
            tipoEvento=self.tipo_evento,
            valores=ValoresLeilao(
                valorBase=self.valor_base,
                valorAbertura=self.valor_abertura,
                valorMinimo=self.valor_minimo,
                lanceAtual=self.lance_atual
            ),
            gps=GPSCoordinates(
                latitude=self.latitude,
                longitude=self.longitude
            ) if self.latitude and self.longitude else None,
            detalhes=EventDetails(
                tipo=self.tipo,
                subtipo=self.subtipo,
                tipologia=self.tipologia,
                areaPrivativa=self.area_privativa,
                areaDependente=self.area_dependente,
                areaTotal=self.area_total,
                distrito=self.distrito,
                concelho=self.concelho,
                freguesia=self.freguesia,
                matricula=self.matricula
            ),
            dataInicio=self.data_inicio,
            dataFim=self.data_fim,
            imagens=imagens_list,
            descricao=self.descricao,  # HTML string
            observacoes=self.observacoes,  # HTML string
            onuselimitacoes=self.onuselimitacoes,  # HTML string - NOVO
            descricaoPredial=self.descricao_predial,  # HTML string
            cerimoniaEncerramento=self.cerimonia_encerramento,  # HTML string
            agenteExecucao=self.agente_execucao,  # HTML string
            dadosProcesso=self.dados_processo,  # HTML string
            scraped_at=self.scraped_at,
            updated_at=self.updated_at
        )


async def init_db():
    """Cria tabelas se não existirem"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database inicializada")


class DatabaseManager:
    """Manager para operações de BD"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_event(self, event: EventData):
        """Guarda ou atualiza um evento"""
        # Verifica se já existe
        result = await self.session.execute(
            select(EventDB).where(EventDB.reference == event.reference)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Atualiza
            existing.tipo_evento = event.tipoEvento
            existing.valor_base = event.valores.valorBase
            existing.valor_abertura = event.valores.valorAbertura
            existing.valor_minimo = event.valores.valorMinimo
            existing.lance_atual = event.valores.lanceAtual
            existing.latitude = event.gps.latitude if event.gps else None
            existing.longitude = event.gps.longitude if event.gps else None
            existing.tipo = event.detalhes.tipo
            existing.subtipo = event.detalhes.subtipo
            existing.tipologia = event.detalhes.tipologia
            existing.area_privativa = event.detalhes.areaPrivativa
            existing.area_dependente = event.detalhes.areaDependente
            existing.area_total = event.detalhes.areaTotal
            existing.distrito = event.detalhes.distrito
            existing.concelho = event.detalhes.concelho
            existing.freguesia = event.detalhes.freguesia
            existing.matricula = event.detalhes.matricula
            existing.data_inicio = event.dataInicio
            existing.data_fim = event.dataFim

            # Campos de conteúdo
            existing.imagens = json.dumps(event.imagens) if event.imagens else None
            existing.descricao = event.descricao  # HTML string
            existing.observacoes = event.observacoes  # HTML string
            existing.onuselimitacoes = event.onuselimitacoes  # HTML string - NOVO
            existing.descricao_predial = event.descricaoPredial  # HTML string
            existing.cerimonia_encerramento = event.cerimoniaEncerramento  # HTML string
            existing.agente_execucao = event.agenteExecucao  # HTML string
            existing.dados_processo = event.dadosProcesso  # HTML string

            existing.updated_at = datetime.utcnow()
        else:
            # Insere novo
            new_event = EventDB(
                reference=event.reference,
                tipo_evento=event.tipoEvento,
                valor_base=event.valores.valorBase,
                valor_abertura=event.valores.valorAbertura,
                valor_minimo=event.valores.valorMinimo,
                lance_atual=event.valores.lanceAtual,
                latitude=event.gps.latitude if event.gps else None,
                longitude=event.gps.longitude if event.gps else None,
                tipo=event.detalhes.tipo,
                subtipo=event.detalhes.subtipo,
                tipologia=event.detalhes.tipologia,
                area_privativa=event.detalhes.areaPrivativa,
                area_dependente=event.detalhes.areaDependente,
                area_total=event.detalhes.areaTotal,
                distrito=event.detalhes.distrito,
                concelho=event.detalhes.concelho,
                freguesia=event.detalhes.freguesia,
                matricula=event.detalhes.matricula,
                data_inicio=event.dataInicio,
                data_fim=event.dataFim,
                # Campos de conteúdo
                imagens=json.dumps(event.imagens) if event.imagens else None,
                descricao=event.descricao,  # HTML string
                observacoes=event.observacoes,  # HTML string
                onuselimitacoes=event.onuselimitacoes,  # HTML string - NOVO
                descricao_predial=event.descricaoPredial,  # HTML string
                cerimonia_encerramento=event.cerimoniaEncerramento,  # HTML string
                agente_execucao=event.agenteExecucao,  # HTML string
                dados_processo=event.dadosProcesso,  # HTML string
                scraped_at=event.scraped_at
            )
            self.session.add(new_event)
        
        await self.session.commit()
    
    async def get_event(self, reference: str) -> Optional[EventData]:
        """Busca um evento por referência"""
        result = await self.session.execute(
            select(EventDB).where(EventDB.reference == reference)
        )
        event_db = result.scalar_one_or_none()
        
        return event_db.to_model() if event_db else None
    
    async def list_events(
        self,
        page: int = 1,
        limit: int = 50,
        tipo: Optional[str] = None,
        tipo_evento: Optional[str] = None,
        distrito: Optional[str] = None
    ) -> Tuple[List[EventData], int]:
        """Lista eventos com paginação e filtros"""
        query = select(EventDB)
        
        # Filtros
        if tipo:
            query = query.where(EventDB.tipo == tipo)
        if tipo_evento:
            query = query.where(EventDB.tipo_evento == tipo_evento)
        if distrito:
            query = query.where(EventDB.distrito == distrito)
        
        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Paginação
        query = query.offset((page - 1) * limit).limit(limit)
        
        result = await self.session.execute(query)
        events_db = result.scalars().all()
        
        events = [event.to_model() for event in events_db]
        
        return events, total
    
    async def get_stats(self) -> dict:
        """Estatísticas gerais"""
        # Total eventos
        total_result = await self.session.execute(select(func.count(EventDB.reference)))
        total = total_result.scalar()
        
        # Com GPS
        gps_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.latitude.isnot(None))
        )
        with_gps = gps_result.scalar()
        
        # Por tipo
        tipos_result = await self.session.execute(
            select(EventDB.tipo, func.count(EventDB.reference))
            .group_by(EventDB.tipo)
        )
        tipos = dict(tipos_result.all())
        
        return {
            "total_events": total,
            "events_with_gps": with_gps,
            "by_type": tipos
        }
    
    async def get_all_references(self) -> List[str]:
        """
        Retorna todas as referências de eventos já armazenadas na BD.
        Útil para comparar com novos scrapes e identificar eventos novos.

        Returns:
            Lista de referências (e.g., ["NP-2024-12345", "LO-2024-67890"])
        """
        result = await self.session.execute(
            select(EventDB.reference)
        )
        references = result.scalars().all()
        return list(references)

    async def delete_all_events(self) -> int:
        """
        Apaga TODOS os eventos da base de dados.
        ATENÇÃO: Esta operação é irreversível!

        Returns:
            Número de eventos apagados
        """
        from sqlalchemy import delete

        # Conta quantos eventos existem
        count_result = await self.session.execute(select(func.count(EventDB.reference)))
        count = count_result.scalar()

        # Apaga todos
        await self.session.execute(delete(EventDB))
        await self.session.commit()

        return count


@asynccontextmanager
async def get_db():
    """Context manager para obter sessão de BD"""
    async with async_session_maker() as session:
        yield DatabaseManager(session)
