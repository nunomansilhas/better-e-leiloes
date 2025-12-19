"""
Data Models para E-Leiloes API
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Mapeamento de tipos de evento (interno)
TIPO_EVENTO_MAP = {
    1: "imoveis",
    2: "veiculos",
    3: "direitos",
    4: "equipamentos",
    5: "mobiliario",
    6: "maquinas"
}

TIPO_EVENTO_NAMES = {
    1: "Imóveis",
    2: "Veículos",
    3: "Direitos",
    4: "Equipamentos",
    5: "Mobiliário",
    6: "Máquinas"
}

# Reverso: string -> código
TIPO_EVENTO_CODES = {v: k for k, v in TIPO_EVENTO_MAP.items()}

# Mapeamento interno -> URL do website
# Website usa: tipo=1 (Imóveis), tipo=2 (Veículos), tipo=3 (Equipamentos),
#              tipo=4 (Mobiliário), tipo=5 (Máquinas), tipo=6 (Direitos)
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
    artigos: List[dict] = Field(default_factory=list)  # Lista de artigos matriciais


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
    requerentes: List[str] = Field(default_factory=list)


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
    imagens: List[str] = Field(default_factory=list)

    # Textos descritivos e secções completas (HTML)
    descricao: Optional[str] = None
    observacoes: Optional[str] = None
    onuselimitacoes: Optional[str] = None  # Novo campo

    # Informações adicionais (HTML completo das secções)
    descricaoPredial: Optional[str] = None  # Alterado: era DescricaoPredial
    cerimoniaEncerramento: Optional[str] = None  # Alterado: era CerimoniaEncerramento
    agenteExecucao: Optional[str] = None  # Alterado: era AgenteExecucao
    dadosProcesso: Optional[str] = None  # Alterado: era DadosProcesso

    # Metadados
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
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
