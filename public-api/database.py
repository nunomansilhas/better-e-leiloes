"""
Database layer for Public API - Read-Only
Connects to remote MySQL on cPanel
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, Text, Integer, Boolean
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
    area_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Location
    morada: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    distrito: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    concelho: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    freguesia: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Description
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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


@asynccontextmanager
async def get_session():
    """Get async database session"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database connection (tables already exist)"""
    # Just verify connection works
    async with engine.begin() as conn:
        pass
