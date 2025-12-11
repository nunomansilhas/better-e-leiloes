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

    # Galeria e textos descritivos
    imagens: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of URLs
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Informações adicionais (JSON)
    descricao_predial: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    cerimonia_encerramento: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    agente_execucao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    dados_processo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Metadados
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def to_model(self) -> EventData:
        """Converte DB model para Pydantic model"""
        # Deserializa JSON fields
        imagens_list = json.loads(self.imagens) if self.imagens else []

        descricao_predial_obj = None
        if self.descricao_predial:
            data = json.loads(self.descricao_predial)
            descricao_predial_obj = DescricaoPredial(**data)

        cerimonia_obj = None
        if self.cerimonia_encerramento:
            data = json.loads(self.cerimonia_encerramento)
            # Parse datetime se presente
            if data.get('data') and isinstance(data['data'], str):
                data['data'] = datetime.fromisoformat(data['data'])
            cerimonia_obj = CerimoniaEncerramento(**data)

        agente_obj = None
        if self.agente_execucao:
            data = json.loads(self.agente_execucao)
            agente_obj = AgenteExecucao(**data)

        dados_processo_obj = None
        if self.dados_processo:
            data = json.loads(self.dados_processo)
            dados_processo_obj = DadosProcesso(**data)

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
            descricao=self.descricao,
            observacoes=self.observacoes,
            descricaoPredial=descricao_predial_obj,
            cerimoniaEncerramento=cerimonia_obj,
            agenteExecucao=agente_obj,
            dadosProcesso=dados_processo_obj,
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

            # Novos campos
            existing.imagens = json.dumps(event.imagens) if event.imagens else None
            existing.descricao = event.descricao
            existing.observacoes = event.observacoes
            existing.descricao_predial = json.dumps(event.descricaoPredial.dict()) if event.descricaoPredial else None
            existing.cerimonia_encerramento = json.dumps(event.cerimoniaEncerramento.dict(), default=str) if event.cerimoniaEncerramento else None
            existing.agente_execucao = json.dumps(event.agenteExecucao.dict()) if event.agenteExecucao else None
            existing.dados_processo = json.dumps(event.dadosProcesso.dict()) if event.dadosProcesso else None

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
                # Novos campos
                imagens=json.dumps(event.imagens) if event.imagens else None,
                descricao=event.descricao,
                observacoes=event.observacoes,
                descricao_predial=json.dumps(event.descricaoPredial.dict()) if event.descricaoPredial else None,
                cerimonia_encerramento=json.dumps(event.cerimoniaEncerramento.dict(), default=str) if event.cerimoniaEncerramento else None,
                agente_execucao=json.dumps(event.agenteExecucao.dict()) if event.agenteExecucao else None,
                dados_processo=json.dumps(event.dadosProcesso.dict()) if event.dadosProcesso else None,
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
