"""
Database layer for Public API - Read-Only
Connects to remote MySQL on cPanel
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, Text, Integer, Boolean, Numeric, Index
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
import os

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not configured!\n"
        "Set in .env: DATABASE_URL=mysql+aiomysql://user:password@host:3306/database"
    )

# SQLAlchemy setup - read-only, optimized for queries
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600
)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class EventDB(Base):
    """Events table - mirrors the main backend schema"""
    __tablename__ = "events"

    # Identification
    reference: Mapped[str] = mapped_column(String(50), primary_key=True)
    id_api: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Title
    titulo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    capa: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Type/Category
    tipo_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    subtipo_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subtipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tipologia: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Values
    valor_base: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valor_abertura: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valor_minimo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lance_atual: Mapped[float] = mapped_column(Float, default=0)

    # Dates
    data_inicio: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_fim: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status
    cancelado: Mapped[bool] = mapped_column(Boolean, default=False)
    iniciado: Mapped[bool] = mapped_column(Boolean, default=False)
    terminado: Mapped[bool] = mapped_column(Boolean, default=False)

    # Area
    area_privativa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    area_dependente: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    area_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Vehicle
    matricula: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Location
    morada: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    distrito: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    concelho: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    freguesia: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Description
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Morada extra
    morada_cp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Processo (legal case)
    processo_numero: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processo_tribunal: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    processo_comarca: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Cerimonia
    cerimonia_data: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cerimonia_local: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cerimonia_morada: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Gestor/Agente
    gestor_nome: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gestor_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gestor_telefone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gestor_tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gestor_cedula: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Photos (JSON array)
    fotos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    data_atualizacao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PriceHistoryDB(Base):
    """Price history table for tracking bid evolution"""
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Prices
    old_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    new_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Calculated change
    change_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


class PipelineStateDB(Base):
    """Pipeline state table - mirrors backend for read-only access"""
    __tablename__ = "pipeline_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_name: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)
    interval_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    runs_count: Mapped[int] = mapped_column(Integer, default=0)
    last_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class RefreshLogDB(Base):
    """
    Refresh request queue - frontend creates, backend processes
    States: 0=pending, 1=processing, 2=completed, 3=error
    """
    __tablename__ = "refresh_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    refresh_type: Mapped[str] = mapped_column(String(20), default='price')  # 'price' or 'full'
    state: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 0=pending, 1=processing, 2=completed, 3=error
    result_lance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Updated price after refresh
    result_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Error message or success info
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # When backend processed it


class NotificationRuleDB(Base):
    """
    Notification rules - define criteria for notifications
    Types: 'new_event', 'price_change', 'ending_soon', 'event_specific'
    """
    __tablename__ = "notification_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # new_event, price_change, ending_soon, event_specific
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Filters (JSON or comma-separated)
    tipos: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "1,2,3"
    subtipos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # ["Apartamento", "Moradia"]
    distritos: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # e.g., "Lisboa,Porto"
    concelhos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # ["Lisboa", "Sintra"]
    preco_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preco_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    variacao_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Variação mínima (€)

    # For ending_soon rules
    minutos_restantes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Ex: 10 min

    # For event-specific rules
    event_reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # Tracking
    last_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # For price change tracking
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    triggers_count: Mapped[int] = mapped_column(Integer, default=0)  # Quantas vezes disparou
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class NotificationDB(Base):
    """
    Notifications - generated when rules are triggered
    """
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Link to rule that triggered it
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)  # new_event, price_change, ending_soon

    # Event info
    event_reference: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_titulo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    event_tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_subtipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_distrito: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Price info (for price_change notifications)
    preco_anterior: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preco_atual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # State
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class FavoriteDB(Base):
    """
    Favorites - user's watched events with notification preferences
    """
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_reference: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)

    # Cached event info (for quick display without joins)
    event_titulo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    event_tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_subtipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_distrito: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_data_fim: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Price tracking
    price_when_added: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_known_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_min_seen: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_max_seen: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Notification preferences for this favorite
    notify_price_change: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_ending_soon: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_ending_minutes: Mapped[int] = mapped_column(Integer, default=30)  # Alert X minutes before end
    notify_price_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Only alert if change > X%

    # Stats
    price_changes_count: Mapped[int] = mapped_column(Integer, default=0)
    notifications_sent: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Notes (user can add notes about why they're watching this)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class EventAiTipDB(Base):
    """
    AI-generated tips and analysis for auction events.
    Stores insights generated by Ollama for properties and vehicles.
    """
    __tablename__ = "event_ai_tips"
    __table_args__ = (
        Index('idx_ai_tips_reference', 'reference'),
        Index('idx_ai_tips_status', 'status'),
        Index('idx_ai_tips_created', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)

    # Event info snapshot (for display)
    event_titulo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    event_tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_subtipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_distrito: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_valor_base: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # AI Analysis
    tip_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Short summary
    tip_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Full analysis
    tip_pros: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of pros
    tip_cons: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of cons
    tip_recommendation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'buy', 'watch', 'skip'
    tip_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0-1.0

    # Processing status
    status: Mapped[str] = mapped_column(String(20), default='pending')  # pending, processing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Model info
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AiPipelineStateDB(Base):
    """
    State tracking for the AI processing pipeline.
    """
    __tablename__ = "ai_pipeline_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Status
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)
    current_reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_event_titulo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Stats
    total_processed: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)
    total_pending: Mapped[int] = mapped_column(Integer, default=0)

    # Last run info
    last_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


@asynccontextmanager
async def get_session():
    """Get async database session"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database connection and create notification tables if needed"""
    async with engine.begin() as conn:
        # Create notification tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
