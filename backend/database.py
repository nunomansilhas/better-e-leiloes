"""
Database layer usando SQLAlchemy + MySQL/MariaDB
Schema v2 - Baseado na API oficial e-leiloes.pt
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select, func, String, Float, DateTime, Text, Integer, Boolean, JSON, text
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

    # ========== VALORES (€) ==========
    valor_base: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valor_abertura: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valor_minimo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lance_atual: Mapped[float] = mapped_column(Float, default=0)
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

        # Por tipo_id
        by_type_result = await self.session.execute(
            select(EventDB.tipo_id, func.count(EventDB.reference))
            .group_by(EventDB.tipo_id)
        )
        by_type = dict(by_type_result.all())

        return {
            "total": total,
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

    async def mark_notification_read(self, notification_id: int) -> bool:
        """Mark a notification as read"""
        result = await self.session.execute(
            select(NotificationDB).where(NotificationDB.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.read = True
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


@asynccontextmanager
async def get_db():
    """Context manager para obter sessão de BD"""
    async with async_session_maker() as session:
        yield DatabaseManager(session)
