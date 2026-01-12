"""
Database layer usando SQLAlchemy + MySQL/MariaDB
Schema v2 - Baseado na API oficial e-leiloes.pt
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select, func, String, Float, DateTime, Text, Integer, Boolean, JSON, text, Numeric, Index
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from typing import List, Tuple, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import os
import json

from models import EventData, FotoItem, OnusItem, DescPredialItem, ArtigoItem, ExecutadoItem

# Database URL - MUST be set in .env file
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "❌ DATABASE_URL not configured!\n"
        "Create a .env file with:\n"
        "DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/eleiloes"
    )

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class EventDB(Base):
    """
    Tabela de eventos - Schema v2
    Baseado na API oficial e-leiloes.pt
    """
    __tablename__ = "events"
    __table_args__ = (
        Index('idx_events_active', 'terminado', 'cancelado', 'data_fim'),
        Index('idx_events_tipo', 'tipo_id'),
        Index('idx_events_distrito', 'distrito'),
    )

    # ========== IDENTIFICAÇÃO ==========
    reference: Mapped[str] = mapped_column(String(50), primary_key=True)
    id_api: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    origem: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verba_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== TÍTULO E CAPA ==========
    titulo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    capa: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ========== TIPO/CATEGORIA ==========
    tipo_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    subtipo_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tipologia_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subtipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tipologia: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    modalidade_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== VALORES (€) - DECIMAL for precision ==========
    valor_base: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    valor_abertura: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    valor_minimo: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    lance_atual: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    lance_atual_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== IVA ==========
    iva_cobrar: Mapped[bool] = mapped_column(Boolean, default=False)
    iva_percentagem: Mapped[int] = mapped_column(Integer, default=23)

    # ========== DATAS ==========
    data_inicio: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_fim_inicial: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_fim: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ========== STATUS ==========
    cancelado: Mapped[bool] = mapped_column(Boolean, default=False)
    iniciado: Mapped[bool] = mapped_column(Boolean, default=False)
    terminado: Mapped[bool] = mapped_column(Boolean, default=False)
    ultimos_5m: Mapped[bool] = mapped_column(Boolean, default=False)

    # ========== ÁREAS (m²) ==========
    area_privativa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    area_dependente: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    area_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ========== MORADA COMPLETA ==========
    morada: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    morada_numero: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    morada_andar: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    morada_cp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    distrito: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    concelho: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    freguesia: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # ========== GPS ==========
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ========== VEÍCULOS ==========
    matricula: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    osae360: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ========== DESCRIÇÕES (texto) ==========
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ========== PROCESSO JUDICIAL ==========
    processo_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processo_numero: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processo_comarca: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    processo_comarca_codigo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    processo_tribunal: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # ========== EXECUTADOS (JSON) ==========
    executados: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ========== CERIMÓNIA ==========
    cerimonia_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cerimonia_data: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cerimonia_local: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cerimonia_morada: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ========== AGENTE/GESTOR ==========
    gestor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gestor_tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gestor_tipo_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gestor_cedula: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gestor_nome: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gestor_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gestor_comarca: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gestor_tribunal: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gestor_telefone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gestor_fax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gestor_morada: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gestor_horario: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ========== ARRAYS JSON ==========
    fotos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    onus: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    desc_predial: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visitas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anexos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ========== METADADOS ==========
    data_servidor: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_atualizacao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_model(self) -> EventData:
        """Converte DB model para Pydantic model"""

        # Parse JSON arrays
        fotos_list = None
        if self.fotos:
            try:
                fotos_raw = json.loads(self.fotos)
                fotos_list = [FotoItem(**f) for f in fotos_raw] if fotos_raw else None
            except:
                pass

        onus_list = None
        if self.onus:
            try:
                onus_raw = json.loads(self.onus)
                onus_list = [OnusItem(**o) for o in onus_raw] if onus_raw else None
            except:
                pass

        desc_predial_list = None
        if self.desc_predial:
            try:
                dp_raw = json.loads(self.desc_predial)
                desc_predial_list = []
                for dp in dp_raw:
                    artigos = [ArtigoItem(**a) for a in dp.get('artigos', [])]
                    desc_predial_list.append(DescPredialItem(
                        id=dp.get('id'),
                        numero=dp.get('numero'),
                        fracao=dp.get('fracao'),
                        distritoDesc=dp.get('distritoDesc'),
                        concelhoDesc=dp.get('concelhoDesc'),
                        freguesiaDesc=dp.get('freguesiaDesc'),
                        artigos=artigos
                    ))
            except:
                pass

        executados_list = None
        if self.executados:
            try:
                exec_raw = json.loads(self.executados)
                executados_list = [ExecutadoItem(**e) for e in exec_raw] if exec_raw else None
            except:
                pass

        visitas_list = None
        if self.visitas:
            try:
                visitas_list = json.loads(self.visitas)
            except:
                pass

        anexos_list = None
        if self.anexos:
            try:
                anexos_list = json.loads(self.anexos)
            except:
                pass

        return EventData(
            reference=self.reference,
            id_api=self.id_api,
            origem=self.origem,
            verba_id=self.verba_id,
            titulo=self.titulo,
            capa=self.capa,
            tipo_id=self.tipo_id,
            subtipo_id=self.subtipo_id,
            tipologia_id=self.tipologia_id,
            tipo=self.tipo,
            subtipo=self.subtipo,
            tipologia=self.tipologia,
            modalidade_id=self.modalidade_id,
            valor_base=self.valor_base,
            valor_abertura=self.valor_abertura,
            valor_minimo=self.valor_minimo,
            lance_atual=self.lance_atual or 0,
            lance_atual_id=self.lance_atual_id,
            iva_cobrar=self.iva_cobrar or False,
            iva_percentagem=self.iva_percentagem or 23,
            data_inicio=self.data_inicio,
            data_fim_inicial=self.data_fim_inicial,
            data_fim=self.data_fim,
            cancelado=self.cancelado or False,
            iniciado=self.iniciado or False,
            terminado=self.terminado or False,
            ultimos_5m=self.ultimos_5m or False,
            area_privativa=self.area_privativa,
            area_dependente=self.area_dependente,
            area_total=self.area_total,
            morada=self.morada,
            morada_numero=self.morada_numero,
            morada_andar=self.morada_andar,
            morada_cp=self.morada_cp,
            distrito=self.distrito,
            concelho=self.concelho,
            freguesia=self.freguesia,
            latitude=self.latitude,
            longitude=self.longitude,
            matricula=self.matricula,
            osae360=self.osae360,
            descricao=self.descricao,
            observacoes=self.observacoes,
            processo_id=self.processo_id,
            processo_numero=self.processo_numero,
            processo_comarca=self.processo_comarca,
            processo_comarca_codigo=self.processo_comarca_codigo,
            processo_tribunal=self.processo_tribunal,
            executados=executados_list,
            cerimonia_id=self.cerimonia_id,
            cerimonia_data=self.cerimonia_data,
            cerimonia_local=self.cerimonia_local,
            cerimonia_morada=self.cerimonia_morada,
            gestor_id=self.gestor_id,
            gestor_tipo=self.gestor_tipo,
            gestor_tipo_id=self.gestor_tipo_id,
            gestor_cedula=self.gestor_cedula,
            gestor_nome=self.gestor_nome,
            gestor_email=self.gestor_email,
            gestor_comarca=self.gestor_comarca,
            gestor_tribunal=self.gestor_tribunal,
            gestor_telefone=self.gestor_telefone,
            gestor_fax=self.gestor_fax,
            gestor_morada=self.gestor_morada,
            gestor_horario=self.gestor_horario,
            fotos=fotos_list,
            onus=onus_list,
            desc_predial=desc_predial_list,
            visitas=visitas_list,
            anexos=anexos_list,
            data_servidor=self.data_servidor,
            data_atualizacao=self.data_atualizacao,
            scraped_at=self.scraped_at,
            updated_at=self.updated_at,
            ativo=self.ativo if self.ativo is not None else True
        )


# ========== NOTIFICATION TABLES ==========

class PriceHistoryDB(Base):
    """
    Histórico de preços de todos os eventos.
    Guarda cada mudança de preço para análise e treino de AI.
    """
    __tablename__ = "price_history"
    __table_args__ = (
        Index('idx_price_history_ref_time', 'reference', 'recorded_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Preços - DECIMAL for precision
    old_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)  # Null no primeiro registo
    new_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Variação calculada
    change_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)  # new_price - old_price
    change_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Percentagem de variação

    # Metadados
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'xmonitor', 'ysync', 'zwatch', 'manual'


class NotificationRuleDB(Base):
    """
    Regras de notificação configuráveis pelo utilizador
    """
    __tablename__ = "notification_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # new_event, price_change, ending_soon
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Filtros (JSON)
    tipos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # ["imoveis", "veiculos"]
    subtipos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # ["Apartamento", "Moradia"]
    distritos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # ["Lisboa", "Porto"]
    concelhos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # ["Sintra", "Cascais"]

    # Filtros de preço
    preco_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preco_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Para regras de price_change
    variacao_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Variação mínima (€)

    # Para regras de ending_soon
    minutos_restantes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Ex: 10 min

    # Para notificações de evento específico
    event_reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadados
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    triggers_count: Mapped[int] = mapped_column(Integer, default=0)  # Quantas vezes disparou


class NotificationDB(Base):
    """
    Notificações geradas pelo sistema
    """
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Regra que gerou (se aplicável)

    # Tipo de notificação
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)  # new_event, price_change, ending_soon

    # Evento relacionado
    event_reference: Mapped[str] = mapped_column(String(50), nullable=False)
    event_titulo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    event_tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_subtipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_distrito: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Dados específicos do tipo
    preco_anterior: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preco_atual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preco_variacao: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Estado
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PipelineStateDB(Base):
    """
    Estado persistente das pipelines automáticas (X-Monitor, Y-Sync, Z-Watch)
    """
    __tablename__ = "pipeline_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # xmonitor, ysync, zwatch

    # Estado
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)

    # Configuração
    interval_hours: Mapped[float] = mapped_column(Float, default=1.0)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Estatísticas
    runs_count: Mapped[int] = mapped_column(Integer, default=0)
    last_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON with last run stats

    # Timestamps de controlo
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RefreshLogDB(Base):
    """
    Refresh request queue - frontend creates, backend processes
    States: 0=pending, 1=processing, 2=completed, 3=error
    """
    __tablename__ = "refresh_logs"
    __table_args__ = (
        Index('idx_refresh_logs_state_time', 'state', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    refresh_type: Mapped[str] = mapped_column(String(20), default='price')  # 'price' or 'full'
    state: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 0=pending, 1=processing, 2=completed, 3=error
    result_lance: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)  # Updated price after refresh
    result_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Error message or success info
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # When backend processed it


async def init_db():
    """Cria tabelas se não existirem"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run migrations for new columns
    async with engine.begin() as conn:
        # Check if event_reference column exists in notification_rules
        try:
            result = await conn.execute(
                text("SELECT event_reference FROM notification_rules LIMIT 1")
            )
        except Exception:
            # Column doesn't exist, add it
            try:
                await conn.execute(
                    text("ALTER TABLE notification_rules ADD COLUMN event_reference VARCHAR(50) NULL")
                )
                print("✅ Added event_reference column to notification_rules")
            except Exception as e:
                print(f"⚠️ Migration note: {e}")

    # Initialize default pipeline states
    async with async_session_maker() as session:
        db = DatabaseManager(session)
        await db.init_default_pipelines()

    print("✅ Database inicializada")


class DatabaseManager:
    """Manager para operações de BD"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_event(self, event: EventData):
        """Guarda ou atualiza um evento (schema v2)"""

        # Serializa arrays para JSON
        fotos_json = None
        if event.fotos:
            fotos_json = json.dumps([f.model_dump() for f in event.fotos])

        onus_json = None
        if event.onus:
            onus_json = json.dumps([o.model_dump() for o in event.onus])

        desc_predial_json = None
        if event.desc_predial:
            desc_predial_json = json.dumps([dp.model_dump() for dp in event.desc_predial])

        executados_json = None
        if event.executados:
            executados_json = json.dumps([e.model_dump() for e in event.executados])

        visitas_json = None
        if event.visitas:
            visitas_json = json.dumps(event.visitas)

        anexos_json = None
        if event.anexos:
            anexos_json = json.dumps(event.anexos)

        # Verifica se já existe
        result = await self.session.execute(
            select(EventDB).where(EventDB.reference == event.reference)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Atualiza todos os campos
            existing.id_api = event.id_api
            existing.origem = event.origem
            existing.verba_id = event.verba_id
            existing.titulo = event.titulo
            existing.capa = event.capa
            existing.tipo_id = event.tipo_id
            existing.subtipo_id = event.subtipo_id
            existing.tipologia_id = event.tipologia_id
            existing.tipo = event.tipo
            existing.subtipo = event.subtipo
            existing.tipologia = event.tipologia
            existing.modalidade_id = event.modalidade_id
            existing.valor_base = event.valor_base
            existing.valor_abertura = event.valor_abertura
            existing.valor_minimo = event.valor_minimo
            existing.lance_atual = event.lance_atual or 0
            existing.lance_atual_id = event.lance_atual_id
            existing.iva_cobrar = event.iva_cobrar
            existing.iva_percentagem = event.iva_percentagem
            existing.data_inicio = event.data_inicio
            existing.data_fim_inicial = event.data_fim_inicial
            existing.data_fim = event.data_fim
            existing.cancelado = event.cancelado
            existing.iniciado = event.iniciado
            existing.terminado = event.terminado
            existing.ultimos_5m = event.ultimos_5m
            existing.area_privativa = event.area_privativa
            existing.area_dependente = event.area_dependente
            existing.area_total = event.area_total
            existing.morada = event.morada
            existing.morada_numero = event.morada_numero
            existing.morada_andar = event.morada_andar
            existing.morada_cp = event.morada_cp
            existing.distrito = event.distrito
            existing.concelho = event.concelho
            existing.freguesia = event.freguesia
            existing.latitude = event.latitude
            existing.longitude = event.longitude
            existing.matricula = event.matricula
            existing.osae360 = event.osae360
            existing.descricao = event.descricao
            existing.observacoes = event.observacoes
            existing.processo_id = event.processo_id
            existing.processo_numero = event.processo_numero
            existing.processo_comarca = event.processo_comarca
            existing.processo_comarca_codigo = event.processo_comarca_codigo
            existing.processo_tribunal = event.processo_tribunal
            existing.executados = executados_json
            existing.cerimonia_id = event.cerimonia_id
            existing.cerimonia_data = event.cerimonia_data
            existing.cerimonia_local = event.cerimonia_local
            existing.cerimonia_morada = event.cerimonia_morada
            existing.gestor_id = event.gestor_id
            existing.gestor_tipo = event.gestor_tipo
            existing.gestor_tipo_id = event.gestor_tipo_id
            existing.gestor_cedula = event.gestor_cedula
            existing.gestor_nome = event.gestor_nome
            existing.gestor_email = event.gestor_email
            existing.gestor_comarca = event.gestor_comarca
            existing.gestor_tribunal = event.gestor_tribunal
            existing.gestor_telefone = event.gestor_telefone
            existing.gestor_fax = event.gestor_fax
            existing.gestor_morada = event.gestor_morada
            existing.gestor_horario = event.gestor_horario
            existing.fotos = fotos_json
            existing.onus = onus_json
            existing.desc_predial = desc_predial_json
            existing.visitas = visitas_json
            existing.anexos = anexos_json
            existing.data_servidor = event.data_servidor
            existing.data_atualizacao = event.data_atualizacao
            existing.ativo = event.ativo
            existing.updated_at = datetime.utcnow()
        else:
            # Insere novo
            new_event = EventDB(
                reference=event.reference,
                id_api=event.id_api,
                origem=event.origem,
                verba_id=event.verba_id,
                titulo=event.titulo,
                capa=event.capa,
                tipo_id=event.tipo_id,
                subtipo_id=event.subtipo_id,
                tipologia_id=event.tipologia_id,
                tipo=event.tipo,
                subtipo=event.subtipo,
                tipologia=event.tipologia,
                modalidade_id=event.modalidade_id,
                valor_base=event.valor_base,
                valor_abertura=event.valor_abertura,
                valor_minimo=event.valor_minimo,
                lance_atual=event.lance_atual or 0,
                lance_atual_id=event.lance_atual_id,
                iva_cobrar=event.iva_cobrar,
                iva_percentagem=event.iva_percentagem,
                data_inicio=event.data_inicio,
                data_fim_inicial=event.data_fim_inicial,
                data_fim=event.data_fim,
                cancelado=event.cancelado,
                iniciado=event.iniciado,
                terminado=event.terminado,
                ultimos_5m=event.ultimos_5m,
                area_privativa=event.area_privativa,
                area_dependente=event.area_dependente,
                area_total=event.area_total,
                morada=event.morada,
                morada_numero=event.morada_numero,
                morada_andar=event.morada_andar,
                morada_cp=event.morada_cp,
                distrito=event.distrito,
                concelho=event.concelho,
                freguesia=event.freguesia,
                latitude=event.latitude,
                longitude=event.longitude,
                matricula=event.matricula,
                osae360=event.osae360,
                descricao=event.descricao,
                observacoes=event.observacoes,
                processo_id=event.processo_id,
                processo_numero=event.processo_numero,
                processo_comarca=event.processo_comarca,
                processo_comarca_codigo=event.processo_comarca_codigo,
                processo_tribunal=event.processo_tribunal,
                executados=executados_json,
                cerimonia_id=event.cerimonia_id,
                cerimonia_data=event.cerimonia_data,
                cerimonia_local=event.cerimonia_local,
                cerimonia_morada=event.cerimonia_morada,
                gestor_id=event.gestor_id,
                gestor_tipo=event.gestor_tipo,
                gestor_tipo_id=event.gestor_tipo_id,
                gestor_cedula=event.gestor_cedula,
                gestor_nome=event.gestor_nome,
                gestor_email=event.gestor_email,
                gestor_comarca=event.gestor_comarca,
                gestor_tribunal=event.gestor_tribunal,
                gestor_telefone=event.gestor_telefone,
                gestor_fax=event.gestor_fax,
                gestor_morada=event.gestor_morada,
                gestor_horario=event.gestor_horario,
                fotos=fotos_json,
                onus=onus_json,
                desc_predial=desc_predial_json,
                visitas=visitas_json,
                anexos=anexos_json,
                data_servidor=event.data_servidor,
                data_atualizacao=event.data_atualizacao,
                scraped_at=event.scraped_at,
                ativo=event.ativo
            )
            self.session.add(new_event)

        await self.session.commit()

    async def insert_event_stub(self, reference: str, tipo_id: int = 1):
        """Insere evento básico (apenas reference + tipo) se não existir"""
        result = await self.session.execute(
            select(EventDB).where(EventDB.reference == reference)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            new_event = EventDB(
                reference=reference,
                tipo_id=tipo_id,
                lance_atual=0,
                scraped_at=datetime.utcnow()
            )
            self.session.add(new_event)
            await self.session.commit()
            return True
        return False

    async def insert_event_stubs_batch(self, items: list, chunk_size: int = 200) -> int:
        """
        Insere múltiplos eventos básicos em chunks (evita timeouts).

        Args:
            items: Lista de dicts com {reference, tipo_id}
            chunk_size: Tamanho de cada chunk

        Returns:
            Número de novos eventos inseridos
        """
        if not items:
            return 0

        total_new = 0

        # Processar em chunks
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            refs = [item['reference'] for item in chunk]

            result = await self.session.execute(
                select(EventDB.reference).where(EventDB.reference.in_(refs))
            )
            existing_refs = set(row[0] for row in result.fetchall())

            new_items = [item for item in chunk if item['reference'] not in existing_refs]

            if new_items:
                new_events = [
                    EventDB(
                        reference=item['reference'],
                        tipo_id=item.get('tipo_id', 1),
                        lance_atual=0,
                        scraped_at=datetime.utcnow()
                    )
                    for item in new_items
                ]
                self.session.add_all(new_events)
                await self.session.commit()
                total_new += len(new_events)

        return total_new

    async def save_events_batch(self, events: list, chunk_size: int = 50, on_progress=None) -> tuple:
        """
        Guarda múltiplos eventos em chunks (evita timeouts).

        Args:
            events: Lista de EventData
            chunk_size: Tamanho de cada chunk (default 50)
            on_progress: Callback async(processed, total) para progresso

        Returns:
            Tuple (inserted_count, updated_count)
        """
        if not events:
            return 0, 0

        total_inserted = 0
        total_updated = 0
        total_events = len(events)

        # Processar em chunks
        for i in range(0, len(events), chunk_size):
            chunk = events[i:i + chunk_size]
            refs = [e.reference for e in chunk]

            result = await self.session.execute(
                select(EventDB).where(EventDB.reference.in_(refs))
            )
            existing_map = {e.reference: e for e in result.scalars().all()}

            for event in chunk:
                # Serializa arrays
                fotos_json = json.dumps([f.model_dump() for f in event.fotos]) if event.fotos else None
                onus_json = json.dumps([o.model_dump() for o in event.onus]) if event.onus else None
                desc_predial_json = json.dumps([dp.model_dump() for dp in event.desc_predial]) if event.desc_predial else None
                executados_json = json.dumps([e.model_dump() for e in event.executados]) if event.executados else None
                visitas_json = json.dumps(event.visitas) if event.visitas else None
                anexos_json = json.dumps(event.anexos) if event.anexos else None

                existing = existing_map.get(event.reference)

                if existing:
                    existing.id_api = event.id_api
                    existing.origem = event.origem
                    existing.verba_id = event.verba_id
                    existing.titulo = event.titulo
                    existing.capa = event.capa
                    existing.tipo_id = event.tipo_id
                    existing.subtipo_id = event.subtipo_id
                    existing.tipologia_id = event.tipologia_id
                    existing.tipo = event.tipo
                    existing.subtipo = event.subtipo
                    existing.tipologia = event.tipologia
                    existing.modalidade_id = event.modalidade_id
                    existing.valor_base = event.valor_base
                    existing.valor_abertura = event.valor_abertura
                    existing.valor_minimo = event.valor_minimo
                    existing.lance_atual = event.lance_atual or 0
                    existing.lance_atual_id = event.lance_atual_id
                    existing.iva_cobrar = event.iva_cobrar
                    existing.iva_percentagem = event.iva_percentagem
                    existing.data_inicio = event.data_inicio
                    existing.data_fim_inicial = event.data_fim_inicial
                    existing.data_fim = event.data_fim
                    existing.cancelado = event.cancelado
                    existing.iniciado = event.iniciado
                    existing.terminado = event.terminado
                    existing.ultimos_5m = event.ultimos_5m
                    existing.area_privativa = event.area_privativa
                    existing.area_dependente = event.area_dependente
                    existing.area_total = event.area_total
                    existing.morada = event.morada
                    existing.morada_numero = event.morada_numero
                    existing.morada_andar = event.morada_andar
                    existing.morada_cp = event.morada_cp
                    existing.distrito = event.distrito
                    existing.concelho = event.concelho
                    existing.freguesia = event.freguesia
                    existing.latitude = event.latitude
                    existing.longitude = event.longitude
                    existing.matricula = event.matricula
                    existing.osae360 = event.osae360
                    existing.descricao = event.descricao
                    existing.observacoes = event.observacoes
                    existing.processo_id = event.processo_id
                    existing.processo_numero = event.processo_numero
                    existing.processo_comarca = event.processo_comarca
                    existing.processo_comarca_codigo = event.processo_comarca_codigo
                    existing.processo_tribunal = event.processo_tribunal
                    existing.cerimonia_id = event.cerimonia_id
                    existing.cerimonia_data = event.cerimonia_data
                    existing.cerimonia_local = event.cerimonia_local
                    existing.cerimonia_morada = event.cerimonia_morada
                    existing.gestor_id = event.gestor_id
                    existing.gestor_tipo = event.gestor_tipo
                    existing.gestor_tipo_id = event.gestor_tipo_id
                    existing.gestor_cedula = event.gestor_cedula
                    existing.gestor_nome = event.gestor_nome
                    existing.gestor_email = event.gestor_email
                    existing.gestor_comarca = event.gestor_comarca
                    existing.gestor_tribunal = event.gestor_tribunal
                    existing.gestor_telefone = event.gestor_telefone
                    existing.gestor_fax = event.gestor_fax
                    existing.gestor_morada = event.gestor_morada
                    existing.gestor_horario = event.gestor_horario
                    existing.fotos = fotos_json
                    existing.onus = onus_json
                    existing.desc_predial = desc_predial_json
                    existing.executados = executados_json
                    existing.visitas = visitas_json
                    existing.anexos = anexos_json
                    existing.data_servidor = event.data_servidor
                    existing.data_atualizacao = event.data_atualizacao
                    existing.scraped_at = event.scraped_at or datetime.utcnow()
                    existing.ativo = event.ativo if event.ativo is not None else True
                    total_updated += 1
                else:
                    new_event = EventDB(
                        reference=event.reference,
                        id_api=event.id_api,
                        origem=event.origem,
                        verba_id=event.verba_id,
                        titulo=event.titulo,
                        capa=event.capa,
                        tipo_id=event.tipo_id,
                        subtipo_id=event.subtipo_id,
                        tipologia_id=event.tipologia_id,
                        tipo=event.tipo,
                        subtipo=event.subtipo,
                        tipologia=event.tipologia,
                        modalidade_id=event.modalidade_id,
                        valor_base=event.valor_base,
                        valor_abertura=event.valor_abertura,
                        valor_minimo=event.valor_minimo,
                        lance_atual=event.lance_atual or 0,
                        lance_atual_id=event.lance_atual_id,
                        iva_cobrar=event.iva_cobrar,
                        iva_percentagem=event.iva_percentagem,
                        data_inicio=event.data_inicio,
                        data_fim_inicial=event.data_fim_inicial,
                        data_fim=event.data_fim,
                        cancelado=event.cancelado,
                        iniciado=event.iniciado,
                        terminado=event.terminado,
                        ultimos_5m=event.ultimos_5m,
                        area_privativa=event.area_privativa,
                        area_dependente=event.area_dependente,
                        area_total=event.area_total,
                        morada=event.morada,
                        morada_numero=event.morada_numero,
                        morada_andar=event.morada_andar,
                        morada_cp=event.morada_cp,
                        distrito=event.distrito,
                        concelho=event.concelho,
                        freguesia=event.freguesia,
                        latitude=event.latitude,
                        longitude=event.longitude,
                        matricula=event.matricula,
                        osae360=event.osae360,
                        descricao=event.descricao,
                        observacoes=event.observacoes,
                        processo_id=event.processo_id,
                        processo_numero=event.processo_numero,
                        processo_comarca=event.processo_comarca,
                        processo_comarca_codigo=event.processo_comarca_codigo,
                        processo_tribunal=event.processo_tribunal,
                        cerimonia_id=event.cerimonia_id,
                        cerimonia_data=event.cerimonia_data,
                        cerimonia_local=event.cerimonia_local,
                        cerimonia_morada=event.cerimonia_morada,
                        gestor_id=event.gestor_id,
                        gestor_tipo=event.gestor_tipo,
                        gestor_tipo_id=event.gestor_tipo_id,
                        gestor_cedula=event.gestor_cedula,
                        gestor_nome=event.gestor_nome,
                        gestor_email=event.gestor_email,
                        gestor_comarca=event.gestor_comarca,
                        gestor_tribunal=event.gestor_tribunal,
                        gestor_telefone=event.gestor_telefone,
                        gestor_fax=event.gestor_fax,
                        gestor_morada=event.gestor_morada,
                        gestor_horario=event.gestor_horario,
                        fotos=fotos_json,
                        onus=onus_json,
                        desc_predial=desc_predial_json,
                        executados=executados_json,
                        visitas=visitas_json,
                        anexos=anexos_json,
                        data_servidor=event.data_servidor,
                        data_atualizacao=event.data_atualizacao,
                        scraped_at=event.scraped_at or datetime.utcnow(),
                        ativo=event.ativo if event.ativo is not None else True
                    )
                    self.session.add(new_event)
                    total_inserted += 1

            # Commit cada chunk
            await self.session.commit()

            # Callback de progresso
            processed = min(i + chunk_size, total_events)
            if on_progress:
                await on_progress(processed, total_events)

        return total_inserted, total_updated

    async def get_event(self, reference: str) -> Optional[EventData]:
        """Busca um evento por referência"""
        result = await self.session.execute(
            select(EventDB).where(EventDB.reference == reference)
        )
        event_db = result.scalar_one_or_none()
        return event_db.to_model() if event_db else None

    async def update_event_fields(self, reference: str, fields: dict) -> bool:
        """
        Update only specific fields of an event (partial update).
        This prevents overwriting other fields with stale data.

        Args:
            reference: Event reference
            fields: Dict of field names and values to update

        Returns:
            True if event was updated, False if not found
        """
        result = await self.session.execute(
            select(EventDB).where(EventDB.reference == reference)
        )
        event_db = result.scalar_one_or_none()

        if not event_db:
            return False

        # Only update the specified fields
        for field_name, value in fields.items():
            if hasattr(event_db, field_name):
                setattr(event_db, field_name, value)

        event_db.updated_at = datetime.utcnow()
        await self.session.commit()
        return True

    async def list_events(
        self,
        page: int = 1,
        limit: int = 50,
        tipo_id: Optional[int] = None,
        tipo: Optional[str] = None,  # Legacy: filter by tipo name (Imóvel, Apartamento)
        tipo_evento: Optional[str] = None,  # Legacy: filter by tipo_evento string
        distrito: Optional[str] = None,
        cancelado: Optional[bool] = None
    ) -> Tuple[List[EventData], int]:
        """Lista eventos com paginação e filtros"""
        query = select(EventDB)

        # tipo_id takes priority
        if tipo_id:
            query = query.where(EventDB.tipo_id == tipo_id)
        elif tipo_evento:
            # Legacy: convert tipo_evento string to tipo_id
            tipo_str_to_id = {
                'imoveis': 1, 'veiculos': 2, 'equipamentos': 3,
                'mobiliario': 4, 'maquinas': 5, 'direitos': 6,
                'imovel': 1, 'movel': 2  # Old format
            }
            mapped_id = tipo_str_to_id.get(tipo_evento.lower())
            if mapped_id:
                query = query.where(EventDB.tipo_id == mapped_id)

        # Filter by tipo name (Imóvel, Apartamento, etc)
        if tipo:
            query = query.where(EventDB.tipo == tipo)
        if distrito:
            query = query.where(EventDB.distrito == distrito)
        if cancelado is not None:
            query = query.where(EventDB.cancelado == cancelado)

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Ordenar por data_fim e paginar
        query = query.order_by(EventDB.data_fim.asc())
        query = query.offset((page - 1) * limit).limit(limit)

        result = await self.session.execute(query)
        events_db = result.scalars().all()

        events = [event.to_model() for event in events_db]
        return events, total

    async def get_upcoming_events(self, hours: int = 24) -> List[EventData]:
        """Get events ending within the next X hours"""
        from datetime import timedelta

        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)

        query = (
            select(EventDB)
            .where(EventDB.data_fim.isnot(None))
            .where(EventDB.data_fim > now)
            .where(EventDB.data_fim <= cutoff)
            .where(EventDB.cancelado == False)
            .order_by(EventDB.data_fim.asc())
        )

        result = await self.session.execute(query)
        events_db = result.scalars().all()
        return [event.to_model() for event in events_db]

    async def get_stats(self) -> dict:
        """Estatísticas gerais"""
        total_result = await self.session.execute(select(func.count(EventDB.reference)))
        total = total_result.scalar()

        # Com GPS
        gps_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.latitude.isnot(None))
        )
        with_gps = gps_result.scalar()

        # Cancelados
        cancelados_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.cancelado == True)
        )
        cancelados = cancelados_result.scalar()

        # Por tipo
        tipos_result = await self.session.execute(
            select(EventDB.tipo_id, func.count(EventDB.reference))
            .group_by(EventDB.tipo_id)
        )
        tipos = dict(tipos_result.all())

        return {
            "total_events": total,
            "events_with_gps": with_gps,
            "events_cancelados": cancelados,
            "by_type_id": tipos
        }

    async def get_all_references(self) -> List[str]:
        """Retorna todas as referências de eventos"""
        result = await self.session.execute(select(EventDB.reference))
        return list(result.scalars().all())

    async def get_subtypes_by_tipo(self, tipo_id: int) -> List[str]:
        """Get distinct subtypes for a given tipo_id"""
        result = await self.session.execute(
            select(EventDB.subtipo)
            .where(EventDB.tipo_id == tipo_id)
            .where(EventDB.subtipo.isnot(None))
            .where(EventDB.cancelado == False)
            .distinct()
            .order_by(EventDB.subtipo)
        )
        return [s for s in result.scalars().all() if s and s != 'N/A']

    async def get_distritos_by_tipo(self, tipo_id: int) -> List[str]:
        """Get distinct distritos for a given tipo_id"""
        result = await self.session.execute(
            select(EventDB.distrito)
            .where(EventDB.tipo_id == tipo_id)
            .where(EventDB.distrito.isnot(None))
            .where(EventDB.cancelado == False)
            .distinct()
            .order_by(EventDB.distrito)
        )
        return [d for d in result.scalars().all() if d]

    async def delete_all_events(self) -> int:
        """Apaga TODOS os eventos"""
        from sqlalchemy import delete

        count_result = await self.session.execute(select(func.count(EventDB.reference)))
        count = count_result.scalar()

        await self.session.execute(delete(EventDB))
        await self.session.commit()
        return count

    async def get_extended_stats(self) -> dict:
        """Extended statistics for maintenance dashboard"""
        from sqlalchemy import and_, or_

        total_result = await self.session.execute(select(func.count(EventDB.reference)))
        total = total_result.scalar()

        # Com descricao
        with_content_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.descricao.isnot(None))
        )
        with_content = with_content_result.scalar()

        # Com fotos
        with_images_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.fotos.isnot(None))
            .where(EventDB.fotos != '[]')
            .where(EventDB.fotos != '')
        )
        with_images = with_images_result.scalar()

        # Cancelados
        cancelados_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.cancelado == True)
        )
        cancelados = cancelados_result.scalar()

        # Inativos (ativo = False)
        inativos_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.ativo == False)
        )
        inativos = inativos_result.scalar()

        # Ativos
        ativos_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.ativo == True)
        )
        ativos = ativos_result.scalar()

        # Por tipo_id
        by_type_result = await self.session.execute(
            select(EventDB.tipo_id, func.count(EventDB.reference))
            .group_by(EventDB.tipo_id)
        )
        by_type = dict(by_type_result.all())

        return {
            "total": total,
            "ativos": ativos,
            "inativos": inativos,
            "with_content": with_content,
            "with_images": with_images,
            "cancelados": cancelados,
            "incomplete": total - with_content,
            "by_type": by_type
        }

    async def update_event_price(self, reference: str, lance_atual: float, data_fim: Optional[datetime] = None):
        """Update only price and optionally data_fim"""
        result = await self.session.execute(
            select(EventDB).where(EventDB.reference == reference)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.lance_atual = lance_atual if lance_atual is not None else 0
            if data_fim is not None:
                existing.data_fim = data_fim
            existing.updated_at = datetime.utcnow()
            await self.session.commit()
            return True
        return False

    async def get_references_without_content(self) -> List[str]:
        """Get references of events without content"""
        result = await self.session.execute(
            select(EventDB.reference)
            .where(EventDB.descricao.is_(None))
        )
        return list(result.scalars().all())

    async def get_events_ending_soon(self, hours: int = 24, limit: int = 1000, include_terminated: bool = True, terminated_hours: int = 120) -> List[dict]:
        """Get events ending within the next X hours + recently terminated events"""
        from datetime import timedelta
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours)

        # Get active events ending soon
        result = await self.session.execute(
            select(EventDB)
            .where(EventDB.data_fim.isnot(None))
            .where(EventDB.data_fim >= now)
            .where(EventDB.data_fim <= end_time)
            .where(EventDB.terminado == 0)  # Use 0 for MySQL tinyint
            .where(EventDB.cancelado == 0)
            .order_by(EventDB.data_fim.asc())
            .limit(limit)
        )
        active_events = result.scalars().all()

        # Get recently terminated events
        terminated_events = []
        if include_terminated:
            terminated_cutoff = now - timedelta(hours=terminated_hours)
            terminated_result = await self.session.execute(
                select(EventDB)
                .where(EventDB.data_fim.isnot(None))
                .where(EventDB.data_fim >= terminated_cutoff)
                .where(EventDB.data_fim <= now)
                .where(EventDB.terminado == 1)  # Use 1 for MySQL tinyint
                .where(EventDB.cancelado == 0)
                .order_by(EventDB.data_fim.desc())
                .limit(limit)
            )
            terminated_events = terminated_result.scalars().all()

        modalidades = {1: 'LO', 2: 'NP'}

        def format_event(e, is_terminated=False):
            return {
                "reference": e.reference,
                "titulo": e.titulo,
                "tipo_id": e.tipo_id,
                "tipo": e.tipo,
                "subtipo": e.subtipo,
                "distrito": e.distrito,
                "lance_atual": e.lance_atual,
                "valor_base": e.valor_base,
                "valor_abertura": e.valor_abertura,
                "valor_minimo": e.valor_minimo,
                "data_fim": e.data_fim.isoformat() if e.data_fim else None,
                "modalidade": modalidades.get(e.modalidade_id, ''),
                "terminado": is_terminated
            }

        # Return active first, then terminated
        result_list = [format_event(e, False) for e in active_events]
        result_list.extend([format_event(e, True) for e in terminated_events])
        return result_list

    async def get_stats_by_distrito(self, limit: int = 10) -> List[dict]:
        """Get event counts by distrito with breakdown by tipo"""
        from sqlalchemy import case

        # Get top distritos by total count
        result = await self.session.execute(
            select(
                EventDB.distrito,
                func.count(EventDB.reference).label('total'),
                func.sum(case((EventDB.tipo_id == 1, 1), else_=0)).label('imoveis'),
                func.sum(case((EventDB.tipo_id == 2, 1), else_=0)).label('veiculos'),
                func.sum(case((EventDB.tipo_id == 3, 1), else_=0)).label('direitos'),
                func.sum(case((EventDB.tipo_id == 4, 1), else_=0)).label('equipamentos'),
                func.sum(case((EventDB.tipo_id == 5, 1), else_=0)).label('mobiliario'),
                func.sum(case((EventDB.tipo_id == 6, 1), else_=0)).label('maquinas')
            )
            .where(EventDB.distrito.isnot(None))
            .where(EventDB.cancelado == False)
            .group_by(EventDB.distrito)
            .order_by(func.count(EventDB.reference).desc())
            .limit(limit)
        )

        return [
            {
                "distrito": row.distrito,
                "total": int(row.total),
                "imoveis": int(row.imoveis or 0),
                "veiculos": int(row.veiculos or 0),
                "direitos": int(row.direitos or 0),
                "equipamentos": int(row.equipamentos or 0),
                "mobiliario": int(row.mobiliario or 0),
                "maquinas": int(row.maquinas or 0)
            }
            for row in result.fetchall()
        ]

    async def get_recent_activity(self) -> dict:
        """Get recent activity stats for dashboard"""
        from datetime import timedelta
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)

        # New events in last 24h (using scraped_at)
        new_events_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.scraped_at >= last_24h)
        )
        new_events = new_events_result.scalar() or 0

        # Events that ended in last 24h
        ended_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.data_fim.isnot(None))
            .where(EventDB.data_fim >= last_24h)
            .where(EventDB.data_fim <= now)
        )
        ended_events = ended_result.scalar() or 0

        # Notifications triggered in last 24h
        notifications_result = await self.session.execute(
            select(func.count(NotificationDB.id))
            .where(NotificationDB.created_at >= last_24h)
        )
        notifications = notifications_result.scalar() or 0

        # Price updates (events updated in last 24h - approximation)
        updated_result = await self.session.execute(
            select(func.count(EventDB.reference))
            .where(EventDB.updated_at >= last_24h)
            .where(EventDB.scraped_at < last_24h)  # Exclude new events
        )
        price_updates = updated_result.scalar() or 0

        return {
            "new_events": new_events,
            "ended_events": ended_events,
            "notifications": notifications,
            "price_updates": price_updates
        }

    async def get_recent_price_changes(self, limit: int = 20) -> List[dict]:
        """Get recent price change notifications for dashboard"""
        result = await self.session.execute(
            select(NotificationDB)
            .where(NotificationDB.notification_type == 'price_change')
            .where(NotificationDB.preco_anterior.isnot(None))
            .where(NotificationDB.preco_atual.isnot(None))
            .order_by(NotificationDB.created_at.desc())
            .limit(limit)
        )
        notifications = result.scalars().all()

        return [{
            "reference": n.event_reference,
            "preco_anterior": n.preco_anterior,
            "preco_atual": n.preco_atual,
            "variacao": n.preco_variacao,
            "created_at": n.created_at.isoformat() if n.created_at else None
        } for n in notifications]

    # ========== NOTIFICATION RULES ==========

    async def get_notification_rules(self, active_only: bool = False) -> List[dict]:
        """Get all notification rules"""
        query = select(NotificationRuleDB)
        if active_only:
            query = query.where(NotificationRuleDB.active == True)
        query = query.order_by(NotificationRuleDB.created_at.desc())

        result = await self.session.execute(query)
        rules = result.scalars().all()

        return [{
            "id": r.id,
            "name": r.name,
            "rule_type": r.rule_type,
            "active": r.active,
            "tipos": json.loads(r.tipos) if r.tipos else None,
            "subtipos": json.loads(r.subtipos) if r.subtipos else None,
            "distritos": json.loads(r.distritos) if r.distritos else None,
            "concelhos": json.loads(r.concelhos) if r.concelhos else None,
            "preco_min": r.preco_min,
            "preco_max": r.preco_max,
            "variacao_min": r.variacao_min,
            "minutos_restantes": r.minutos_restantes,
            "event_reference": r.event_reference,
            "triggers_count": r.triggers_count,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in rules]

    async def create_notification_rule(self, rule_data: dict) -> int:
        """Create a new notification rule"""
        rule = NotificationRuleDB(
            name=rule_data["name"],
            rule_type=rule_data["rule_type"],
            active=rule_data.get("active", True),
            tipos=json.dumps(rule_data.get("tipos")) if rule_data.get("tipos") else None,
            subtipos=json.dumps(rule_data.get("subtipos")) if rule_data.get("subtipos") else None,
            distritos=json.dumps(rule_data.get("distritos")) if rule_data.get("distritos") else None,
            concelhos=json.dumps(rule_data.get("concelhos")) if rule_data.get("concelhos") else None,
            preco_min=rule_data.get("preco_min"),
            preco_max=rule_data.get("preco_max"),
            variacao_min=rule_data.get("variacao_min"),
            minutos_restantes=rule_data.get("minutos_restantes"),
            event_reference=rule_data.get("event_reference")
        )
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule.id

    async def update_notification_rule(self, rule_id: int, updates: dict) -> bool:
        """Update a notification rule"""
        result = await self.session.execute(
            select(NotificationRuleDB).where(NotificationRuleDB.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            return False

        if "name" in updates:
            rule.name = updates["name"]
        if "active" in updates:
            rule.active = updates["active"]
        if "tipos" in updates:
            rule.tipos = json.dumps(updates["tipos"]) if updates["tipos"] else None
        if "subtipos" in updates:
            rule.subtipos = json.dumps(updates["subtipos"]) if updates["subtipos"] else None
        if "distritos" in updates:
            rule.distritos = json.dumps(updates["distritos"]) if updates["distritos"] else None
        if "concelhos" in updates:
            rule.concelhos = json.dumps(updates["concelhos"]) if updates["concelhos"] else None
        if "preco_min" in updates:
            rule.preco_min = updates["preco_min"]
        if "preco_max" in updates:
            rule.preco_max = updates["preco_max"]
        if "variacao_min" in updates:
            rule.variacao_min = updates["variacao_min"]
        if "minutos_restantes" in updates:
            rule.minutos_restantes = updates["minutos_restantes"]

        rule.updated_at = datetime.utcnow()
        await self.session.commit()
        return True

    async def delete_notification_rule(self, rule_id: int) -> bool:
        """Delete a notification rule"""
        from sqlalchemy import delete
        result = await self.session.execute(
            delete(NotificationRuleDB).where(NotificationRuleDB.id == rule_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def increment_rule_triggers(self, rule_id: int):
        """Increment the triggers count for a rule"""
        result = await self.session.execute(
            select(NotificationRuleDB).where(NotificationRuleDB.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule:
            rule.triggers_count += 1
            await self.session.commit()

    # ========== NOTIFICATIONS ==========

    async def create_notification(self, notification_data: dict) -> int:
        """Create a new notification"""
        notification = NotificationDB(
            rule_id=notification_data.get("rule_id"),
            notification_type=notification_data["notification_type"],
            event_reference=notification_data["event_reference"],
            event_titulo=notification_data.get("event_titulo"),
            event_tipo=notification_data.get("event_tipo"),
            event_subtipo=notification_data.get("event_subtipo"),
            event_distrito=notification_data.get("event_distrito"),
            preco_anterior=notification_data.get("preco_anterior"),
            preco_atual=notification_data.get("preco_atual"),
            preco_variacao=notification_data.get("preco_variacao")
        )
        self.session.add(notification)
        await self.session.commit()
        await self.session.refresh(notification)
        return notification.id

    async def notification_exists(
        self,
        rule_id: Optional[int],
        event_reference: str,
        notification_type: str,
        hours: int = 24
    ) -> bool:
        """
        Check if a similar notification was already created recently.
        Prevents duplicate notifications within the specified time window.
        """
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        conditions = [
            NotificationDB.event_reference == event_reference,
            NotificationDB.notification_type == notification_type,
            NotificationDB.created_at > cutoff
        ]

        # Handle None rule_id (system notifications)
        if rule_id is None:
            conditions.append(NotificationDB.rule_id.is_(None))
        else:
            conditions.append(NotificationDB.rule_id == rule_id)

        result = await self.session.execute(
            select(func.count(NotificationDB.id)).where(*conditions)
        )
        count = result.scalar() or 0
        return count > 0

    async def get_notification_rules_by_type(
        self,
        rule_type: str,
        active_only: bool = True
    ) -> List[dict]:
        """Get notification rules filtered by type (more efficient than filtering in Python)"""
        query = select(NotificationRuleDB).where(NotificationRuleDB.rule_type == rule_type)
        if active_only:
            query = query.where(NotificationRuleDB.active == True)

        result = await self.session.execute(query)
        rules = result.scalars().all()

        return [{
            "id": r.id,
            "name": r.name,
            "rule_type": r.rule_type,
            "tipos": json.loads(r.tipos) if r.tipos else None,
            "subtipos": json.loads(r.subtipos) if r.subtipos else None,
            "distritos": json.loads(r.distritos) if r.distritos else None,
            "concelhos": json.loads(r.concelhos) if r.concelhos else None,
            "preco_min": r.preco_min,
            "preco_max": r.preco_max,
            "variacao_min": r.variacao_min,
            "minutos_restantes": r.minutos_restantes,
            "event_reference": r.event_reference,
            "active": r.active,
            "triggers_count": r.triggers_count,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in rules]

    async def get_notifications(self, limit: int = 50, unread_only: bool = False) -> List[dict]:
        """Get notifications"""
        query = select(NotificationDB).order_by(NotificationDB.created_at.desc())
        if unread_only:
            query = query.where(NotificationDB.read == False)
        query = query.limit(limit)

        result = await self.session.execute(query)
        notifications = result.scalars().all()

        return [{
            "id": n.id,
            "rule_id": n.rule_id,
            "notification_type": n.notification_type,
            "event_reference": n.event_reference,
            "event_titulo": n.event_titulo,
            "event_tipo": n.event_tipo,
            "event_subtipo": n.event_subtipo,
            "event_distrito": n.event_distrito,
            "preco_anterior": n.preco_anterior,
            "preco_atual": n.preco_atual,
            "preco_variacao": n.preco_variacao,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        } for n in notifications]

    async def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        result = await self.session.execute(
            select(func.count(NotificationDB.id)).where(NotificationDB.read == False)
        )
        return result.scalar() or 0

    async def mark_notification_read(self, notification_id: int, read: bool = True) -> bool:
        """Mark a notification as read or unread"""
        result = await self.session.execute(
            select(NotificationDB).where(NotificationDB.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.read = read
            await self.session.commit()
            return True
        return False

    async def mark_all_notifications_read(self) -> int:
        """Mark all notifications as read"""
        from sqlalchemy import update
        result = await self.session.execute(
            update(NotificationDB).where(NotificationDB.read == False).values(read=True)
        )
        await self.session.commit()
        return result.rowcount

    async def delete_old_notifications(self, days: int = 30) -> int:
        """Delete notifications older than X days"""
        from sqlalchemy import delete
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            delete(NotificationDB).where(NotificationDB.created_at < cutoff)
        )
        await self.session.commit()
        return result.rowcount

    async def delete_all_notifications(self) -> int:
        """Delete all notifications"""
        from sqlalchemy import delete
        result = await self.session.execute(
            delete(NotificationDB)
        )
        await self.session.commit()
        return result.rowcount

    # ========== PRICE HISTORY ==========

    async def record_price_change(
        self,
        reference: str,
        new_price: float,
        old_price: Optional[float] = None,
        source: Optional[str] = None
    ) -> Optional[int]:
        """
        Regista uma mudança de preço.
        Se old_price não for fornecido, tenta buscar o último preço registado.
        Só regista se o preço for diferente do último.

        Returns:
            ID do registo criado, ou None se não houve mudança
        """
        # Se old_price não foi fornecido, buscar o último preço registado
        if old_price is None:
            result = await self.session.execute(
                select(PriceHistoryDB)
                .where(PriceHistoryDB.reference == reference)
                .order_by(PriceHistoryDB.recorded_at.desc())
                .limit(1)
            )
            last_record = result.scalar_one_or_none()
            if last_record:
                old_price = last_record.new_price

        # Se o preço não mudou, não registar
        if old_price is not None and old_price == new_price:
            return None

        # Calcular variação
        change_amount = None
        change_percent = None
        if old_price is not None and old_price > 0:
            change_amount = new_price - old_price
            change_percent = (change_amount / old_price) * 100

        record = PriceHistoryDB(
            reference=reference,
            old_price=old_price,
            new_price=new_price,
            change_amount=change_amount,
            change_percent=change_percent,
            source=source
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record.id

    async def get_event_price_history(self, reference: str) -> List[dict]:
        """
        Retorna o histórico completo de preços de um evento.
        Ordenado do mais antigo para o mais recente.
        """
        result = await self.session.execute(
            select(PriceHistoryDB)
            .where(PriceHistoryDB.reference == reference)
            .order_by(PriceHistoryDB.recorded_at.asc())
        )
        records = result.scalars().all()

        return [{
            "id": r.id,
            "old_price": r.old_price,
            "new_price": r.new_price,
            "change_amount": r.change_amount,
            "change_percent": r.change_percent,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            "source": r.source
        } for r in records]

    async def get_recent_price_changes(self, limit: int = 30, hours: int = 24) -> List[dict]:
        """
        Retorna as mudanças de preço mais recentes (apenas onde houve mudança real).
        Retorna apenas a última mudança por evento (sem duplicados).
        """
        from datetime import timedelta
        from sqlalchemy import and_

        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Subquery para encontrar o registo mais recente por referência
        subquery = (
            select(
                PriceHistoryDB.reference,
                func.max(PriceHistoryDB.id).label('max_id')
            )
            .where(PriceHistoryDB.recorded_at >= cutoff)
            .where(PriceHistoryDB.old_price.isnot(None))  # Só mudanças reais
            .group_by(PriceHistoryDB.reference)
            .subquery()
        )

        # Query principal
        result = await self.session.execute(
            select(PriceHistoryDB)
            .join(subquery, and_(
                PriceHistoryDB.reference == subquery.c.reference,
                PriceHistoryDB.id == subquery.c.max_id
            ))
            .order_by(PriceHistoryDB.recorded_at.desc())
            .limit(limit)
        )
        records = result.scalars().all()

        return [{
            "reference": r.reference,
            "preco_anterior": r.old_price,
            "preco_atual": r.new_price,
            "variacao": r.change_amount,
            "variacao_percent": r.change_percent,
            "timestamp": r.recorded_at.isoformat() if r.recorded_at else None,
            "source": r.source
        } for r in records]

    async def get_price_history_stats(self) -> dict:
        """
        Estatísticas do histórico de preços.
        """
        # Total de registos
        total_result = await self.session.execute(
            select(func.count(PriceHistoryDB.id))
        )
        total_records = total_result.scalar() or 0

        # Eventos únicos
        unique_result = await self.session.execute(
            select(func.count(func.distinct(PriceHistoryDB.reference)))
        )
        unique_events = unique_result.scalar() or 0

        # Mudanças reais (onde old_price não é null)
        changes_result = await self.session.execute(
            select(func.count(PriceHistoryDB.id))
            .where(PriceHistoryDB.old_price.isnot(None))
        )
        real_changes = changes_result.scalar() or 0

        # Eventos com pelo menos uma mudança
        events_with_changes_result = await self.session.execute(
            select(func.count(func.distinct(PriceHistoryDB.reference)))
            .where(PriceHistoryDB.old_price.isnot(None))
        )
        events_with_changes = events_with_changes_result.scalar() or 0

        # Registos por source
        by_source_result = await self.session.execute(
            select(PriceHistoryDB.source, func.count(PriceHistoryDB.id))
            .group_by(PriceHistoryDB.source)
        )
        by_source = {source or 'unknown': count for source, count in by_source_result.all()}

        return {
            "total_records": total_records,
            "unique_events": unique_events,
            "real_changes": real_changes,
            "events_with_changes": events_with_changes,
            "by_source": by_source
        }

    async def get_all_price_history_references(self) -> List[str]:
        """
        Retorna todas as referências com histórico de preços.
        """
        result = await self.session.execute(
            select(func.distinct(PriceHistoryDB.reference))
        )
        return list(result.scalars().all())

    async def bulk_import_price_history(self, data: dict) -> int:
        """
        Importa histórico de preços em bulk (para migração do JSON).
        data é um dict com reference como key e lista de {preco, timestamp} como value.

        Returns:
            Número de registos importados
        """
        count = 0
        for reference, prices in data.items():
            prev_price = None
            for entry in prices:
                price = entry.get("preco")
                timestamp_str = entry.get("timestamp")

                # Parse timestamp
                try:
                    if timestamp_str:
                        recorded_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        recorded_at = datetime.utcnow()
                except:
                    recorded_at = datetime.utcnow()

                # Calcular variação
                change_amount = None
                change_percent = None
                if prev_price is not None and prev_price > 0:
                    change_amount = price - prev_price
                    change_percent = (change_amount / prev_price) * 100

                record = PriceHistoryDB(
                    reference=reference,
                    old_price=prev_price,
                    new_price=price,
                    change_amount=change_amount,
                    change_percent=change_percent,
                    recorded_at=recorded_at,
                    source='migration'
                )
                self.session.add(record)
                count += 1
                prev_price = price

        await self.session.commit()
        return count

    # ========== PIPELINE STATE METHODS ==========

    async def get_pipeline_state(self, pipeline_name: str) -> Optional[PipelineStateDB]:
        """Get pipeline state by name"""
        result = await self.session.execute(
            select(PipelineStateDB).where(PipelineStateDB.pipeline_name == pipeline_name)
        )
        return result.scalar_one_or_none()

    async def get_all_pipeline_states(self) -> list:
        """Get all pipeline states"""
        result = await self.session.execute(
            select(PipelineStateDB).order_by(PipelineStateDB.pipeline_name)
        )
        return list(result.scalars().all())

    async def save_pipeline_state(
        self,
        pipeline_name: str,
        enabled: bool = None,
        is_running: bool = None,
        interval_hours: float = None,
        description: str = None,
        last_run: datetime = None,
        next_run: datetime = None,
        runs_count: int = None,
        last_result: str = None
    ) -> PipelineStateDB:
        """Save or update pipeline state"""
        result = await self.session.execute(
            select(PipelineStateDB).where(PipelineStateDB.pipeline_name == pipeline_name)
        )
        existing = result.scalar_one_or_none()

        if existing:
            if enabled is not None:
                existing.enabled = enabled
            if is_running is not None:
                existing.is_running = is_running
            if interval_hours is not None:
                existing.interval_hours = interval_hours
            if description is not None:
                existing.description = description
            if last_run is not None:
                existing.last_run = last_run
            if next_run is not None:
                existing.next_run = next_run
            if runs_count is not None:
                existing.runs_count = runs_count
            if last_result is not None:
                existing.last_result = last_result
            existing.updated_at = datetime.utcnow()
            await self.session.commit()
            return existing
        else:
            # Create new
            new_state = PipelineStateDB(
                pipeline_name=pipeline_name,
                enabled=enabled or False,
                is_running=is_running or False,
                interval_hours=interval_hours or 1.0,
                description=description,
                last_run=last_run,
                next_run=next_run,
                runs_count=runs_count or 0,
                last_result=last_result
            )
            self.session.add(new_state)
            await self.session.commit()
            return new_state

    async def get_refresh_stats(self) -> dict:
        """Get refresh request statistics"""
        from datetime import timedelta
        try:
            now = datetime.utcnow()
            cutoff_24h = now - timedelta(hours=24)

            # Count ALL requests in last 24h
            total_24h = await self.session.scalar(
                select(func.count()).select_from(RefreshLogDB).where(
                    RefreshLogDB.created_at >= cutoff_24h
                )
            )

            # Count pending (state=0) or processing (state=1)
            pending = await self.session.scalar(
                select(func.count()).select_from(RefreshLogDB).where(
                    RefreshLogDB.state.in_([0, 1])
                )
            )

            # Total all-time
            total_all = await self.session.scalar(
                select(func.count()).select_from(RefreshLogDB)
            )

            return {
                "total_24h": total_24h or 0,
                "pending": pending or 0,
                "total_all_time": total_all or 0
            }
        except Exception as e:
            print(f"Error getting refresh stats: {e}")
            return {"total_24h": 0, "pending": 0, "total_all_time": 0}

    async def init_default_pipelines(self):
        """Initialize default pipeline states if they don't exist"""
        defaults = {
            "xmonitor": {
                "description": "Monitoriza eventos nas próximas 24h - atualiza lance_atual e data_fim",
                "interval_hours": 5/3600  # 5 seconds
            },
            "ysync": {
                "description": "Sincronização completa: todos os IDs + marca terminados",
                "interval_hours": 2.0  # 2 hours
            },
            "zwatch": {
                "description": "Monitoriza EventosMaisRecentes API a cada 10 minutos",
                "interval_hours": 10/60  # 10 minutes
            }
        }

        for name, config in defaults.items():
            existing = await self.get_pipeline_state(name)
            if not existing:
                await self.save_pipeline_state(
                    pipeline_name=name,
                    enabled=False,
                    interval_hours=config["interval_hours"],
                    description=config["description"]
                )
                print(f"✨ Created default pipeline state: {name}")


@asynccontextmanager
async def get_db():
    """Context manager para obter sessão de BD"""
    async with async_session_maker() as session:
        yield DatabaseManager(session)
