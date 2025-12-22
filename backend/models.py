"""
Data Models para E-Leiloes API - Schema Completo v2
Baseado na API oficial: https://www.e-leiloes.pt/api/eventos/{reference}
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# Mapeamento de tipos de evento (API)
TIPO_EVENTO_MAP = {
    1: "imoveis",
    2: "veiculos",
    3: "equipamentos",
    4: "mobiliario",
    5: "maquinas",
    6: "direitos"
}

TIPO_EVENTO_NAMES = {
    1: "Imóveis",
    2: "Veículos",
    3: "Equipamentos",
    4: "Mobiliário",
    5: "Máquinas",
    6: "Direitos"
}

# Reverso: string -> código
TIPO_EVENTO_CODES = {v: k for k, v in TIPO_EVENTO_MAP.items()}

# Mapeamento interno -> URL do website
TIPO_TO_WEBSITE = {
    1: 1,  # imoveis -> tipo=1
    2: 2,  # veiculos -> tipo=2
    3: 6,  # direitos -> tipo=6
    4: 3,  # equipamentos -> tipo=3
    5: 4,  # mobiliario -> tipo=4
    6: 5,  # maquinas -> tipo=5
}

# Reverso: URL do website -> interno
WEBSITE_TO_TIPO = {v: k for k, v in TIPO_TO_WEBSITE.items()}


# ============================================================
# SUB-MODELOS (para arrays JSON)
# ============================================================

class FotoItem(BaseModel):
    """Item de foto da galeria"""
    legenda: Optional[str] = None
    image: Optional[str] = None
    thumbnail: Optional[str] = None


class OnusItem(BaseModel):
    """Item de ónus/limitação"""
    tipo: Optional[int] = None
    descricao: Optional[str] = None
    tipoDesc: Optional[str] = None


class ArtigoItem(BaseModel):
    """Artigo matricial"""
    numero: Optional[str] = None
    tipo: Optional[str] = None
    fracao: Optional[str] = None
    distritoDesc: Optional[str] = None
    concelhoDesc: Optional[str] = None
    freguesiaDesc: Optional[str] = None


class DescPredialItem(BaseModel):
    """Descrição predial"""
    id: Optional[int] = None
    numero: Optional[str] = None
    fracao: Optional[str] = None
    distritoDesc: Optional[str] = None
    concelhoDesc: Optional[str] = None
    freguesiaDesc: Optional[str] = None
    artigos: List[ArtigoItem] = Field(default_factory=list)


class ExecutadoItem(BaseModel):
    """Executado (devedor)"""
    nif: Optional[str] = None
    nome: Optional[str] = None
    requerido: Optional[str] = None


# ============================================================
# MODELO PRINCIPAL - EventData
# ============================================================

class EventData(BaseModel):
    """
    Dados completos de um evento - Schema v2
    Baseado na API oficial e-leiloes.pt
    """
    # ========== IDENTIFICAÇÃO ==========
    reference: str = Field(..., description="Referência única (LO1427992025)")
    id_api: Optional[int] = Field(None, description="ID interno da API")
    origem: Optional[int] = Field(None, description="ID origem")
    verba_id: Optional[int] = Field(None, description="ID da verba")

    # ========== TÍTULO E CAPA ==========
    titulo: Optional[str] = Field(None, description="Título do evento")
    capa: Optional[str] = Field(None, description="URL imagem de capa")

    # ========== TIPO/CATEGORIA ==========
    tipo_id: Optional[int] = Field(None, description="1=Imóvel, 2=Veículo, etc")
    subtipo_id: Optional[int] = None
    tipologia_id: Optional[int] = None
    tipo: Optional[str] = Field(None, description="Nome do tipo: Imóvel, Veículo...")
    subtipo: Optional[str] = Field(None, description="Apartamento, Moradia...")
    tipologia: Optional[str] = Field(None, description="T0, T1, T2...")
    modalidade_id: Optional[int] = None

    # ========== VALORES (€) ==========
    valor_base: Optional[float] = None
    valor_abertura: Optional[float] = None
    valor_minimo: Optional[float] = None
    lance_atual: float = Field(default=0, description="Lance atual (PMA)")
    lance_atual_id: Optional[int] = None

    # ========== IVA ==========
    iva_cobrar: bool = False
    iva_percentagem: int = 23

    # ========== DATAS ==========
    data_inicio: Optional[datetime] = None
    data_fim_inicial: Optional[datetime] = None
    data_fim: Optional[datetime] = None

    # ========== STATUS ==========
    cancelado: bool = False
    iniciado: bool = False
    terminado: bool = False
    ultimos_5m: bool = False

    # ========== ÁREAS (m²) ==========
    area_privativa: Optional[float] = None
    area_dependente: Optional[float] = None
    area_total: Optional[float] = None

    # ========== MORADA COMPLETA ==========
    morada: Optional[str] = None
    morada_numero: Optional[str] = None
    morada_andar: Optional[str] = None
    morada_cp: Optional[str] = None
    distrito: Optional[str] = None
    concelho: Optional[str] = None
    freguesia: Optional[str] = None

    # ========== GPS ==========
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # ========== VEÍCULOS ==========
    matricula: Optional[str] = None
    osae360: Optional[str] = None

    # ========== DESCRIÇÕES ==========
    descricao: Optional[str] = None
    observacoes: Optional[str] = None

    # ========== PROCESSO JUDICIAL ==========
    processo_id: Optional[int] = None
    processo_numero: Optional[str] = None
    processo_comarca: Optional[str] = None
    processo_comarca_codigo: Optional[str] = None
    processo_tribunal: Optional[str] = None

    # ========== EXECUTADOS ==========
    executados: Optional[List[ExecutadoItem]] = None

    # ========== CERIMÓNIA ==========
    cerimonia_id: Optional[int] = None
    cerimonia_data: Optional[datetime] = None
    cerimonia_local: Optional[str] = None
    cerimonia_morada: Optional[str] = None

    # ========== AGENTE/GESTOR ==========
    gestor_id: Optional[int] = None
    gestor_tipo: Optional[str] = None
    gestor_tipo_id: Optional[int] = None
    gestor_cedula: Optional[str] = None
    gestor_nome: Optional[str] = None
    gestor_email: Optional[str] = None
    gestor_comarca: Optional[str] = None
    gestor_tribunal: Optional[str] = None
    gestor_telefone: Optional[str] = None
    gestor_fax: Optional[str] = None
    gestor_morada: Optional[str] = None
    gestor_horario: Optional[str] = None

    # ========== ARRAYS (JSON) ==========
    fotos: Optional[List[FotoItem]] = None
    onus: Optional[List[OnusItem]] = None
    desc_predial: Optional[List[DescPredialItem]] = None
    visitas: Optional[List[Any]] = None
    anexos: Optional[List[Any]] = None

    # ========== METADADOS ==========
    data_servidor: Optional[datetime] = None
    data_atualizacao: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    ativo: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "reference": "LO1427992025",
                "titulo": "Apartamento sito em Caparica",
                "tipo": "Imóvel",
                "subtipo": "Apartamento",
                "tipologia": "T2",
                "valor_base": 180000.00,
                "lance_atual": 126121.20,
                "distrito": "Setúbal",
                "concelho": "Almada"
            }
        }


# ============================================================
# MODELOS AUXILIARES
# ============================================================

class EventListResponse(BaseModel):
    """Resposta paginada de eventos"""
    events: List[EventData]
    total: int
    page: int
    limit: int
    pages: int


class ScraperStatus(BaseModel):
    """Status do scraper"""
    is_running: bool
    events_processed: int
    events_failed: int
    current_page: Optional[int] = None
    started_at: Optional[datetime] = None
    last_update: Optional[datetime] = None


# ============================================================
# MODELOS LEGADOS (compatibilidade)
# ============================================================

class GPSCoordinates(BaseModel):
    """Coordenadas GPS do imóvel (LEGADO)"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ValoresLeilao(BaseModel):
    """Valores do leilão (LEGADO - para compatibilidade com scraper antigo)"""
    valorBase: Optional[float] = None
    valorAbertura: Optional[float] = None
    valorMinimo: Optional[float] = None
    lanceAtual: Optional[float] = None


class EventDetails(BaseModel):
    """Detalhes do evento (LEGADO - para compatibilidade com scraper antigo)"""
    tipo: str = "N/A"
    subtipo: str = "N/A"
    tipologia: Optional[str] = None
    areaPrivativa: Optional[float] = None
    areaDependente: Optional[float] = None
    areaTotal: Optional[float] = None
    distrito: Optional[str] = None
    concelho: Optional[str] = None
    freguesia: Optional[str] = None
    matricula: Optional[str] = None
