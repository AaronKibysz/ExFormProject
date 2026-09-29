"""Tests for validation rules."""
import pytest
from app.models import ComparableProperty, PropertyToAnalyze, PropertyType, CaptureStatus
from app.validation import (
    validate_property, validate_property_to_analyze, 
    validate_collection, validate_price_consistency, ValidationResult
)


class TestValidateProperty:
    """Test comparable property validation."""
    
    def test_valid_property(self):
        prop = ComparableProperty(
            id=1,
            address="Luzuriaga 300",
            publication_price=73000,
            sale_price=60000,
            covered_area=140,
            total_area=160,
            land_area=300,
            rooms=3,
            bedrooms=3,
            bathrooms=1,
            garage=2,
            age=26,
            days_on_market=95,
            capture_status=CaptureStatus.CLOSED,
        )
        result = validate_property(prop, 1)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_missing_address(self):
        prop = ComparableProperty(id=1, publication_price=73000)
        result = validate_property(prop, 1)
        assert result.is_valid is False
        assert any("Falta dirección" in e for e in result.errors)
    
    def test_missing_price(self):
        prop = ComparableProperty(id=1, address="Luzuriaga 300")
        result = validate_property(prop, 1)
        assert result.is_valid is False
        assert any("Falta precio" in e for e in result.errors)
    
    def test_negative_price(self):
        prop = ComparableProperty(
            id=1, address="Luzuriaga 300", publication_price=-1000
        )
        result = validate_property(prop, 1)
        assert result.is_valid is False
        assert any("inválido (<= 0)" in e for e in result.errors)
    
    def test_covered_greater_than_total(self):
        prop = ComparableProperty(
            id=1, address="Luzuriaga 300", publication_price=73000,
            covered_area=200, total_area=160
        )
        result = validate_property(prop, 1)
        assert result.is_valid is True  # Warning, not error
        assert any("cubierta > total" in w for w in result.warnings)
    
    def test_bedrooms_greater_than_rooms(self):
        prop = ComparableProperty(
            id=1, address="Luzuriaga 300", publication_price=73000,
            rooms=3, bedrooms=5
        )
        result = validate_property(prop, 1)
        assert result.is_valid is True
        assert any("Dormitorios > Ambientes" in w for w in result.warnings)
    
    def test_invalid_age(self):
        prop = ComparableProperty(
            id=1, address="Luzuriaga 300", publication_price=73000,
            age=250
        )
        result = validate_property(prop, 1)
        assert result.is_valid is True
        assert any("inusualmente alta" in w for w in result.warnings)


class TestValidatePropertyToAnalyze:
    """Test property to analyze validation."""
    
    def test_valid(self):
        prop = PropertyToAnalyze(
            address="Mi Casa 123",
            covered_area=150,
            total_area=180,
        )
        result = validate_property_to_analyze(prop)
        assert result.is_valid is True
    
    def test_missing_address(self):
        prop = PropertyToAnalyze(covered_area=150)
        result = validate_property_to_analyze(prop)
        assert result.is_valid is False
        assert any("Falta Dirección" in e for e in result.errors)


class TestValidateCollection:
    """Test collection validation."""
    
    def test_count_mismatch(self):
        props = [
            ComparableProperty(id=1, address="A", publication_price=100),
            ComparableProperty(id=2, address="B", publication_price=200),
        ]
        result = validate_collection(props, 4)
        assert result.is_valid is False
        assert any("se esperaban 4" in e for e in result.errors)
    
    def test_duplicate_address(self):
        props = [
            ComparableProperty(id=1, address="Luzuriaga 300", publication_price=100),
            ComparableProperty(id=2, address="Luzuriaga 300", publication_price=200),
        ]
        result = validate_collection(props, 2)
        assert result.is_valid is True
        assert any("duplicada" in w for w in result.warnings)
    
    def test_price_consistency_warning(self):
        props = [
            ComparableProperty(id=1, address="A", publication_price=100, sale_price=90),
            ComparableProperty(id=2, address="B", publication_price=200),  # missing sale
        ]
        result = validate_collection(props, 2)
        assert any("Falta precio de venta" in w for w in result.warnings)


class TestValidatePriceConsistency:
    """Test price consistency check."""
    
    def test_both_prices_present(self):
        props = [
            ComparableProperty(id=1, address="A", publication_price=100, sale_price=90),
            ComparableProperty(id=2, address="B", publication_price=200, sale_price=180),
        ]
        warnings = validate_price_consistency(props)
        assert len(warnings) == 0
    
    def test_mixed_prices(self):
        props = [
            ComparableProperty(id=1, address="A", publication_price=100, sale_price=90),
            ComparableProperty(id=2, address="B", publication_price=200),  # no sale price
        ]
        warnings = validate_price_consistency(props)
        assert any("Falta precio de venta" in w for w in warnings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])