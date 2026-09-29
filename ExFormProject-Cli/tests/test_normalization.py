"""Tests for normalization utilities."""
import pytest
from app.utils.normalization import (
    normalize_number, normalize_int, normalize_price, 
    normalize_area, normalize_text, clean_extracted_value
)


class TestNormalizeNumber:
    """Test number normalization."""
    
    def test_integer(self):
        assert normalize_number("160") == 160.0
        assert normalize_number("160.00") == 160.0
    
    def test_decimal_point(self):
        assert normalize_number("239.38") == 239.38
        assert normalize_number("0.5") == 0.5
    
    def test_decimal_comma(self):
        assert normalize_number("239,38") == 239.38
        assert normalize_number("0,5") == 0.5
    
    def test_thousands_separator_dot(self):
        assert normalize_number("1.234,56") == 1234.56
        assert normalize_number("10.000") == 10000.0
    
    def test_thousands_separator_comma(self):
        assert normalize_number("1,234.56") == 1234.56
        assert normalize_number("10,000") == 10000.0
    
    def test_with_currency(self):
        assert normalize_number("U$S 73,000") == 73000.0
        assert normalize_number("USD 73000") == 73000.0
        assert normalize_number("$ 73,000") == 73000.0
    
    def test_with_units(self):
        assert normalize_number("160 m²") == 160.0
        assert normalize_number("160m2") == 160.0
    
    def test_invalid(self):
        assert normalize_number("") is None
        assert normalize_number("abc") is None
        assert normalize_number(None) is None


class TestNormalizeInt:
    """Test integer normalization."""
    
    def test_basic(self):
        assert normalize_int("5") == 5
        assert normalize_int("5.0") == 5
        assert normalize_int("5,0") == 5
    
    def test_from_price(self):
        assert normalize_int("73,000") == 73000


class TestNormalizePrice:
    """Test price extraction."""
    
    def test_with_currency_symbols(self):
        assert normalize_price("U$S 73,000") == 73000.0
        assert normalize_price("USD 73000") == 73000.0
        assert normalize_price("$ 73000") == 73000.0
    
    def test_without_symbol(self):
        assert normalize_price("73000") == 73000.0
    
    def test_decimal(self):
        assert normalize_price("U$S 73,000.50") == 73000.50


class TestNormalizeArea:
    """Test area extraction."""
    
    def test_with_units(self):
        assert normalize_area("160 m²") == 160.0
        assert normalize_area("140m2") == 140.0
        assert normalize_area("239.38 m²") == 239.38
    
    def test_without_units(self):
        assert normalize_area("160") == 160.0


class TestNormalizeText:
    """Test text normalization."""
    
    def test_basic(self):
        assert normalize_text("  Luzuriaga 300  ") == "Luzuriaga 300"
        assert normalize_text("Luzuriaga\n300") == "Luzuriaga 300"
        assert normalize_text("Luzuriaga\t300") == "Luzuriaga 300"
    
    def test_empty(self):
        assert normalize_text("") is None
        assert normalize_text("   ") is None
        assert normalize_text(None) is None


class TestCleanExtractedValue:
    """Test field-specific cleaning."""
    
    def test_price(self):
        assert clean_extracted_value("U$S 73,000", "price") == 73000.0
    
    def test_area(self):
        assert clean_extracted_value("160 m²", "total_area") == 160.0
    
    def test_int_field(self):
        assert clean_extracted_value("3", "rooms") == 3
        assert clean_extracted_value("3", "bedrooms") == 3
    
    def test_text_field(self):
        assert clean_extracted_value("Luzuriaga 300", "address") == "Luzuriaga 300"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])