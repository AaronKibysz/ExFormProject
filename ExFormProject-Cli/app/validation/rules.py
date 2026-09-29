"""Validation rules for extracted data."""
from typing import List, Tuple, Optional
from dataclasses import dataclass

from app.models import ComparableProperty, PropertyToAnalyze, PropertyType, CaptureStatus


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __bool__(self) -> bool:
        return self.is_valid


def validate_property(prop: ComparableProperty, index: int) -> ValidationResult:
    """Validate a single comparable property."""
    errors = []
    warnings = []
    prefix = f"Comparable {index}"
    
    # Essential fields
    if not prop.address:
        errors.append(f"{prefix}: Falta dirección")
    elif len(prop.address.strip()) < 3:
        warnings.append(f"{prefix}: Dirección muy corta")
    
    if prop.publication_price is None and prop.sale_price is None:
        errors.append(f"{prefix}: Falta precio (publicación y venta)")
    else:
        if prop.publication_price is not None and prop.publication_price <= 0:
            errors.append(f"{prefix}: Precio de publicación inválido (<= 0)")
        if prop.sale_price is not None and prop.sale_price <= 0:
            errors.append(f"{prefix}: Precio de venta inválido (<= 0)")
    
    # Surface areas
    for field_name, field_label in [
        ("total_area", "Superficie total"),
        ("covered_area", "Superficie cubierta"),
        ("land_area", "Superficie terreno"),
    ]:
        value = getattr(prop, field_name)
        if value is not None:
            if value <= 0:
                errors.append(f"{prefix}: {field_label} inválida (<= 0)")
            elif value > 10000:
                warnings.append(f"{prefix}: {field_label} inusualmente alta ({value})")
        else:
            warnings.append(f"{prefix}: Falta {field_label.lower()}")
    
    # Logical consistency
    if prop.covered_area and prop.total_area:
        if prop.covered_area > prop.total_area:
            warnings.append(f"{prefix}: Superficie cubierta > total ({prop.covered_area} > {prop.total_area})")
    
    if prop.semi_covered_area and prop.total_area:
        if prop.semi_covered_area > prop.total_area:
            warnings.append(f"{prefix}: Superficie semicubierta > total")
    
    if prop.land_area and prop.total_area:
        if prop.land_area < prop.total_area:
            warnings.append(f"{prefix}: Superficie terreno < total (posible error)")
    
    # Rooms
    for field_name, field_label in [
        ("rooms", "Ambientes"),
        ("bedrooms", "Dormitorios"),
        ("bathrooms", "Baños"),
        ("garage", "Cochera"),
    ]:
        value = getattr(prop, field_name)
        if value is not None:
            if value < 0:
                errors.append(f"{prefix}: {field_label} negativo")
            elif value > 20:
                warnings.append(f"{prefix}: {field_label} inusualmente alto ({value})")
    
    if prop.bedrooms and prop.rooms:
        if prop.bedrooms > prop.rooms:
            warnings.append(f"{prefix}: Dormitorios > Ambientes ({prop.bedrooms} > {prop.rooms})")
    
    # Age
    if prop.age is not None:
        if prop.age < 0:
            errors.append(f"{prefix}: Antigüedad negativa")
        elif prop.age > 200:
            warnings.append(f"{prefix}: Antigüedad inusualmente alta ({prop.age} años)")
    
    if prop.construction_year is not None:
        if prop.construction_year < 1800 or prop.construction_year > 2030:
            warnings.append(f"{prefix}: Año de construcción fuera de rango ({prop.construction_year})")
    
    # Days on market
    if prop.days_on_market is not None:
        if prop.days_on_market < 0:
            errors.append(f"{prefix}: Días en mercado negativo")
        elif prop.days_on_market > 3650:
            warnings.append(f"{prefix}: Días en mercado inusualmente alto ({prop.days_on_market})")
    
    # Duplicates check (by address) - done at collection level
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_property_to_analyze(prop: PropertyToAnalyze) -> ValidationResult:
    """Validate property to analyze."""
    errors = []
    warnings = []
    
    missing = prop.missing_essential_fields()
    for field in missing:
        errors.append(f"Propiedad a analizar: Falta {field}")
    
    if prop.covered_area is not None and prop.covered_area <= 0:
        errors.append("Propiedad a analizar: Superficie cubierta inválida")
    
    if prop.total_area is not None and prop.total_area <= 0:
        errors.append("Propiedad a analizar: Superficie total inválida")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_collection(
    properties: List[ComparableProperty], 
    expected_count: int,
    property_to_analyze: Optional[PropertyToAnalyze] = None
) -> ValidationResult:
    """Validate entire collection of properties."""
    errors = []
    warnings = []
    
    # Count validation
    if len(properties) != expected_count:
        errors.append(
            f"Cantidad de propiedades: se esperaban {expected_count}, "
            f"se detectaron {len(properties)}"
        )
    
    # Individual validation
    for i, prop in enumerate(properties):
        result = validate_property(prop, i + 1)
        errors.extend(result.errors)
        warnings.extend(result.warnings)
    
    # Duplicate detection
    addresses = []
    for prop in properties:
        if prop.address:
            normalized = prop.address.strip().lower()
            if normalized in addresses:
                warnings.append(f"Dirección duplicada detectada: {prop.address}")
            addresses.append(normalized)
    
    # Property to analyze validation
    if property_to_analyze:
        result = validate_property_to_analyze(property_to_analyze)
        errors.extend(result.errors)
        warnings.extend(result.warnings)
    
    # Price consistency check
    price_warnings = validate_price_consistency(properties)
    warnings.extend(price_warnings)
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_price_consistency(properties: List[ComparableProperty]) -> List[str]:
    """Check if price types are consistent across properties."""
    warnings = []
    has_pub = any(p.publication_price is not None for p in properties)
    has_sale = any(p.sale_price is not None for p in properties)
    
    if has_pub and has_sale:
        # Check if all have both
        for i, prop in enumerate(properties):
            if prop.publication_price is None:
                warnings.append(f"Comparable {i+1}: Falta precio de publicación")
            if prop.sale_price is None:
                warnings.append(f"Comparable {i+1}: Falta precio de venta")
    
    return warnings