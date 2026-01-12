"""
Input Validation Module
Pydantic models and validators for API inputs
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
import re


# ============== Request Models ==============

class PaginationParams(BaseModel):
    """Common pagination parameters"""
    page: int = Field(default=1, ge=1, le=10000, description="Page number")
    limit: int = Field(default=50, ge=1, le=500, description="Items per page")


class EventFilterParams(BaseModel):
    """Event listing filter parameters"""
    tipo_id: Optional[int] = Field(default=None, ge=1, le=10, description="Tipo ID (1-6)")
    distrito: Optional[str] = Field(default=None, max_length=100, description="Distrito name")
    cancelado: Optional[bool] = Field(default=None, description="Filter by cancelado status")

    @field_validator('distrito')
    @classmethod
    def sanitize_distrito(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # Remove any potentially dangerous characters
        v = v.strip()
        # Only allow letters, spaces, hyphens, and Portuguese accents
        if not re.match(r'^[\w\sÀ-ÿ-]+$', v, re.UNICODE):
            raise ValueError('Invalid distrito format')
        return v


class RefreshRequest(BaseModel):
    """Refresh request for a single event"""
    reference: str = Field(..., min_length=5, max_length=50, description="Event reference")
    refresh_type: str = Field(default='price', pattern='^(price|full)$', description="Type of refresh")

    @field_validator('reference')
    @classmethod
    def validate_reference(cls, v: str) -> str:
        v = v.strip().upper()
        # Reference format: typically like "LO-123456" or "NP-123456"
        if not re.match(r'^[A-Z]{2,3}-?\d+$', v):
            raise ValueError('Invalid reference format')
        return v


class BatchRefreshRequest(BaseModel):
    """Batch refresh request for multiple events"""
    references: List[str] = Field(..., min_length=1, max_length=100, description="List of references")
    refresh_type: str = Field(default='price', pattern='^(price|full)$')

    @field_validator('references')
    @classmethod
    def validate_references(cls, v: List[str]) -> List[str]:
        result = []
        for ref in v:
            ref = ref.strip().upper()
            if not re.match(r'^[A-Z]{2,3}-?\d+$', ref):
                raise ValueError(f'Invalid reference format: {ref}')
            result.append(ref)
        return result


class NotificationRuleRequest(BaseModel):
    """Create/Update notification rule"""
    name: str = Field(..., min_length=1, max_length=100, description="Rule name")
    rule_type: str = Field(..., pattern='^(new_event|price_change|ending_soon|watch_event)$')
    active: bool = Field(default=True)
    tipos: Optional[List[int]] = Field(default=None, max_length=6)
    subtipos: Optional[List[str]] = Field(default=None, max_length=50)
    distritos: Optional[List[str]] = Field(default=None, max_length=20)
    concelhos: Optional[List[str]] = Field(default=None, max_length=50)
    preco_min: Optional[float] = Field(default=None, ge=0, le=100000000)
    preco_max: Optional[float] = Field(default=None, ge=0, le=100000000)
    variacao_min: Optional[float] = Field(default=None, ge=0, le=100000000)
    minutos_restantes: Optional[int] = Field(default=None, ge=1, le=1440)
    event_reference: Optional[str] = Field(default=None, max_length=50)

    @model_validator(mode='after')
    def validate_price_range(self):
        if self.preco_min is not None and self.preco_max is not None:
            if self.preco_min > self.preco_max:
                raise ValueError('preco_min cannot be greater than preco_max')
        return self

    @field_validator('name')
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        # Remove any HTML/script tags
        v = re.sub(r'<[^>]+>', '', v)
        return v


class ScrapeRequest(BaseModel):
    """Request to scrape events"""
    tipo_id: int = Field(..., ge=1, le=6, description="Tipo ID to scrape")
    limit: Optional[int] = Field(default=None, ge=1, le=10000, description="Max events to scrape")
    force: bool = Field(default=False, description="Force re-scrape of existing events")


class PipelineConfigRequest(BaseModel):
    """Pipeline configuration update"""
    enabled: Optional[bool] = Field(default=None)
    interval_hours: Optional[float] = Field(default=None, ge=0.001, le=24)


# ============== Response Models ==============

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str
    data: Optional[dict] = None


# ============== Utility Functions ==============

def validate_reference(reference: str) -> str:
    """Validate and normalize a reference string"""
    reference = reference.strip().upper()
    if not re.match(r'^[A-Z]{2,3}-?\d+$', reference):
        raise ValueError('Invalid reference format')
    return reference


def validate_tipo_id(tipo_id: int) -> int:
    """Validate tipo_id is in valid range"""
    if tipo_id < 1 or tipo_id > 6:
        raise ValueError('tipo_id must be between 1 and 6')
    return tipo_id


def sanitize_string(value: str, max_length: int = 200) -> str:
    """Sanitize a string input"""
    if not value:
        return value
    value = value.strip()
    # Remove HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]
    return value
