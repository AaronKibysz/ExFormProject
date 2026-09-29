"""Data models for the ACM Generator."""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class PropertyType(str, Enum):
    """Property type enumeration."""
    HOUSE = "Casa"
    APARTMENT = "Departamento"
    LAND = "Terreno"
    COMMERCIAL = "Comercial"
    OTHER = "Otro"


class CaptureStatus(str, Enum):
    """Capture status enumeration."""
    CLOSED = "Cerrada"
    OPEN = "Abierta"
    PENDING = "Pendiente"
    UNKNOWN = "Desconocido"


class PriceType(str, Enum):
    """Price type for Excel mapping."""
    PUBLICATION = "publication_price"
    SALE = "sale_price"


@dataclass
class ComparableProperty:
    """Represents a comparable property extracted from PDF."""
    # Identification
    id: int = 0
    source_page: Optional[int] = None
    
    # Core fields from PDF
    publication_price: Optional[float] = None
    sale_price: Optional[float] = None
    address: Optional[str] = None
    property_type: Optional[PropertyType] = None
    capture_status: Optional[CaptureStatus] = None
    
    # Surface areas (m²)
    total_area: Optional[float] = None
    covered_area: Optional[float] = None
    semi_covered_area: Optional[float] = None
    land_area: Optional[float] = None
    
    # Rooms & facilities
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    garage: Optional[int] = None
    
    # Construction & age
    construction_year: Optional[int] = None
    age: Optional[int] = None  # years
    
    # Market data
    days_on_market: Optional[int] = None
    
    # Boolean features
    apto_credito: Optional[bool] = None
    financing: Optional[bool] = None
    professional_use: Optional[bool] = None
    
    # Amenities & features (from description)
    has_kitchen: Optional[bool] = None
    has_dining_room: Optional[bool] = None
    amenities: List[str] = field(default_factory=list)
    
    # Extraction metadata
    extraction_warnings: List[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    
    def get_price_for_excel(self, price_type: PriceType) -> Optional[float]:
        """Get the selected price type for Excel output."""
        if price_type == PriceType.PUBLICATION:
            return self.publication_price
        return self.sale_price
    
    def has_essential_data(self) -> bool:
        """Check if property has minimum required data."""
        return self.address is not None and (
            self.publication_price is not None or self.sale_price is not None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for preview display."""
        return {
            "id": self.id,
            "address": self.address or "",
            "publication_price": self.publication_price or "",
            "sale_price": self.sale_price or "",
            "total_area": self.total_area or "",
            "covered_area": self.covered_area or "",
            "land_area": self.land_area or "",
            "rooms": self.rooms or "",
            "bedrooms": self.bedrooms or "",
            "bathrooms": self.bathrooms or "",
            "garage": self.garage or "",
            "age": self.age or "",
            "days_on_market": self.days_on_market or "",
            "capture_status": self.capture_status.value if self.capture_status else "",
            "warnings": "; ".join(self.extraction_warnings) if self.extraction_warnings else "",
        }


@dataclass
class PropertyToAnalyze:
    """Property being analyzed (column C in template)."""
    address: Optional[str] = None
    property_type: Optional[PropertyType] = None
    capture_status: Optional[CaptureStatus] = None
    covered_area: Optional[float] = None
    total_area: Optional[float] = None
    construction_year: Optional[int] = None
    has_kitchen: Optional[bool] = None
    has_dining_room: Optional[bool] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    garage: Optional[int] = None
    extraction_warnings: List[str] = field(default_factory=list)
    
    def has_essential_data(self) -> bool:
        return self.address is not None
    
    def missing_essential_fields(self) -> List[str]:
        """Return list of missing essential field names."""
        missing = []
        if not self.address:
            missing.append("Dirección")
        return missing