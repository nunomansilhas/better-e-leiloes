"""
Data Models para E-Leiloes API
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class GPSCoordinates(BaseModel):
    """Coordenadas GPS do imóvel"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ValoresLeilao(BaseModel):
    """Valores do leilão (extraídos da listagem e confirmados na página individual)"""
    valorBase: Optional[float] = None
    valorAbertura: Optional[float] = None
    valorMinimo: Optional[float] = None
    lanceAtual: Optional[float] = None


class EventDetails(BaseModel):
    """Detalhes do evento (IMOVEL ou MOVEL)"""
    tipo: str = "N/A"
    subtipo: str = "N/A"

    # Campos específicos de IMOVEIS
    tipologia: Optional[str] = None
    areaPrivativa: Optional[float] = None  # em m²
    areaDependente: Optional[float] = None  # em m²
    areaTotal: Optional[float] = None  # em m²
    distrito: Optional[str] = None
    concelho: Optional[str] = None
    freguesia: Optional[str] = None

    # Campos específicos de MOVEIS (automóveis)
    matricula: Optional[str] = None


class DescricaoPredial(BaseModel):
    """Informação da descrição predial"""
    numeroDescricao: Optional[str] = None
    fracao: Optional[str] = None
    distritoCode: Optional[str] = None
    concelhoCode: Optional[str] = None
    freguesiaCode: Optional[str] = None
    artigos: List[dict] = []  # Lista de artigos matriciais


class CerimoniaEncerramento(BaseModel):
    """Dados da cerimónia de encerramento"""
    data: Optional[datetime] = None
    local: Optional[str] = None
    morada: Optional[str] = None


class AgenteExecucao(BaseModel):
    """Dados do agente de execução"""
    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None


class DadosProcesso(BaseModel):
    """Dados do processo judicial"""
    processo: Optional[str] = None
    tribunal: Optional[str] = None
    unidadeOrganica: Optional[str] = None
    requerentes: List[str] = []


class EventData(BaseModel):
    """Dados completos de um evento"""
    reference: str = Field(..., description="Referência única (NP-XXXX ou LO-XXXX)")
    tipoEvento: str = Field(..., description="'imovel' ou 'movel'")

    # Valores do leilão
    valores: ValoresLeilao

    # GPS (apenas para imóveis)
    gps: Optional[GPSCoordinates] = None

    # Detalhes
    detalhes: EventDetails

    # Datas do evento
    dataInicio: Optional[datetime] = None
    dataFim: Optional[datetime] = None

    # Galeria de imagens
    imagens: List[str] = []

    # Textos descritivos
    descricao: Optional[str] = None
    observacoes: Optional[str] = None

    # Informações adicionais
    descricaoPredial: Optional[DescricaoPredial] = None
    cerimoniaEncerramento: Optional[CerimoniaEncerramento] = None
    agenteExecucao: Optional[AgenteExecucao] = None
    dadosProcesso: Optional[DadosProcesso] = None

    # Metadados
    scraped_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "reference": "NP-2024-12345",
                "gps": {
                    "latitude": 38.7223,
                    "longitude": -9.1393
                },
                "detalhes": {
                    "tipo": "Apartamento",
                    "subtipo": "Apartamento T2",
                    "tipologia": "T2",
                    "areaPrivativa": 85.5,
                    "areaDependente": 10.0,
                    "areaTotal": 95.5,
                    "distrito": "Lisboa",
                    "concelho": "Lisboa",
                    "freguesia": "Avenidas Novas"
                },
                "scraped_at": "2024-12-05T10:30:00Z"
            }
        }


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
