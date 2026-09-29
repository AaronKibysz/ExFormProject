"""PDF text extraction and property parsing."""
import fitz  # PyMuPDF
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from app.models import ComparableProperty, PropertyType, CaptureStatus
from app.utils.normalization import (
    normalize_number, normalize_int, normalize_price, normalize_area,
    normalize_text, clean_extracted_value, find_property_blocks
)
from app.pdf_parser.patterns import (
    FIELD_PATTERNS, VALUE_PATTERNS, get_field_patterns, extract_value_after_label
)
from app.utils.logging import get_logger


logger = get_logger()


@dataclass
class ExtractionResult:
    """Result of PDF extraction."""
    properties: List[ComparableProperty]
    property_to_analyze: Optional[ComparableProperty] = None
    warnings: List[str] = None
    total_pages: int = 0
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class PDFExtractor:
    """Extract comparable properties from real estate PDF."""
    
    def __init__(self):
        self.logger = logger
    
    def extract(self, pdf_path: str, num_comparables: int) -> ExtractionResult:
        """
        Main extraction method.
        
        Args:
            pdf_path: Path to PDF file
            num_comparables: Expected number of comparable properties
            
        Returns:
            ExtractionResult with properties and metadata
        """
        self.logger.info(f"Loading PDF: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        self.logger.info(f"PDF loaded: {total_pages} pages")
        
        # Extract text from all pages with page info
        full_text = ""
        page_texts = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            page_texts.append((page_num + 1, text))
            full_text += f"\n--- PAGE {page_num + 1} ---\n{text}"
        
        doc.close()
        
        # Check if PDF has extractable text
        if not full_text.strip():
            self.logger.warning("PDF appears to be scanned or has no extractable text")
            return ExtractionResult(
                properties=[],
                warnings=["El PDF parece estar escaneado o no contiene texto extraíble."],
                total_pages=total_pages
            )
        
        # Extract property blocks
        properties = self._extract_properties(full_text, page_texts, num_comparables)
        
        # Validate count
        warnings = []
        if len(properties) != num_comparables:
            msg = f"Se solicitaron {num_comparables} propiedades pero se detectaron {len(properties)}."
            warnings.append(msg)
            self.logger.warning(msg)
        
        return ExtractionResult(
            properties=properties,
            warnings=warnings,
            total_pages=total_pages
        )
    
    def _extract_properties(
        self, 
        full_text: str, 
        page_texts: List[tuple], 
        num_comparables: int
    ) -> List[ComparableProperty]:
        """Extract property data from text."""
        properties = []
        
        # Try to find property blocks
        blocks = find_property_blocks(full_text)
        self.logger.info(f"Found {len(blocks)} potential property blocks")
        
        # If we have fewer blocks than expected, try page-based splitting
        if len(blocks) < num_comparables and len(page_texts) >= num_comparables:
            # Use page texts as blocks
            blocks = [text for _, text in page_texts[:num_comparables]]
            self.logger.info(f"Using page-based splitting: {len(blocks)} blocks")
        
        # Limit to requested number
        blocks = blocks[:num_comparables]
        
        for i, block in enumerate(blocks):
            prop = self._parse_property_block(block, i + 1, page_texts)
            properties.append(prop)
        
        return properties
    
    def _parse_property_block(
        self, 
        block: str, 
        prop_id: int, 
        page_texts: List[tuple]
    ) -> ComparableProperty:
        """Parse a single property block into a ComparableProperty."""
        prop = ComparableProperty(id=prop_id)
        prop.raw_data = {}
        warnings = []
        
        # Determine source page
        prop.source_page = self._find_source_page(block, page_texts)
        
        # Extract each field
        field_extractors = {
            "publication_price": self._extract_price,
            "sale_price": self._extract_price,
            "address": self._extract_address,
            "property_type": self._extract_property_type,
            "capture_status": self._extract_capture_status,
            "total_area": self._extract_area,
            "covered_area": self._extract_area,
            "semi_covered_area": self._extract_area,
            "land_area": self._extract_area,
            "rooms": self._extract_int,
            "bedrooms": self._extract_int,
            "bathrooms": self._extract_int,
            "garage": self._extract_int,
            "age": self._extract_int,
            "construction_year": self._extract_int,
            "days_on_market": self._extract_int,
            "apto_credito": self._extract_boolean,
            "financing": self._extract_boolean,
            "professional_use": self._extract_boolean,
        }
        
        for field_name, extractor in field_extractors.items():
            try:
                value = extractor(block, field_name)
                if value is not None:
                    setattr(prop, field_name, value)
                    prop.raw_data[field_name] = value
            except Exception as e:
                warning = f"Error extracting {field_name}: {e}"
                warnings.append(warning)
                self.logger.debug(warning)
        
        # Extract amenities from remaining text
        self._extract_amenities(block, prop)
        
        prop.extraction_warnings = warnings
        return prop
    
    def _find_source_page(self, block: str, page_texts: List[tuple]) -> Optional[int]:
        """Find which page the block came from."""
        # Use first 100 chars as fingerprint
        fingerprint = block[:100]
        for page_num, page_text in page_texts:
            if fingerprint in page_text:
                return page_num
        return None
    
    def _extract_price(self, text: str, field_name: str) -> Optional[float]:
        """Extract price value."""
        patterns = get_field_patterns(field_name)
        value_str = extract_value_after_label(text, patterns, VALUE_PATTERNS["price"])
        if value_str:
            return normalize_price(value_str)
        return None
    
    def _extract_area(self, text: str, field_name: str) -> Optional[float]:
        """Extract area value."""
        patterns = get_field_patterns(field_name)
        value_str = extract_value_after_label(text, patterns, VALUE_PATTERNS["area"])
        if value_str:
            return normalize_area(value_str)
        return None
    
    def _extract_int(self, text: str, field_name: str) -> Optional[int]:
        """Extract integer value."""
        patterns = get_field_patterns(field_name)
        value_str = extract_value_after_label(text, patterns, VALUE_PATTERNS["number"])
        if value_str:
            return normalize_int(value_str)
        return None
    
    def _extract_address(self, text: str, field_name: str) -> Optional[str]:
        """Extract address."""
        patterns = get_field_patterns(field_name)
        value_str = extract_value_after_label(text, patterns, VALUE_PATTERNS["text_line"])
        if value_str:
            return normalize_text(value_str)
        return None
    
    def _extract_property_type(self, text: str, field_name: str) -> Optional[PropertyType]:
        """Extract property type."""
        patterns = get_field_patterns(field_name)
        value_str = extract_value_after_label(text, patterns, VALUE_PATTERNS["text_line"])
        if value_str:
            normalized = normalize_text(value_str).lower()
            if "casa" in normalized:
                return PropertyType.HOUSE
            elif "departamento" in normalized or "dpto" in normalized:
                return PropertyType.APARTMENT
            elif "terreno" in normalized:
                return PropertyType.LAND
            elif "comercial" in normalized or "local" in normalized:
                return PropertyType.COMMERCIAL
            return PropertyType.OTHER
        return None
    
    def _extract_capture_status(self, text: str, field_name: str) -> Optional[CaptureStatus]:
        """Extract capture status."""
        patterns = get_field_patterns(field_name)
        value_str = extract_value_after_label(text, patterns, VALUE_PATTERNS["text_line"])
        if value_str:
            normalized = normalize_text(value_str).lower()
            if "cerrad" in normalized:
                return CaptureStatus.CLOSED
            elif "abierta" in normalized or "abiert" in normalized:
                return CaptureStatus.OPEN
            elif "pendient" in normalized:
                return CaptureStatus.PENDING
            return CaptureStatus.UNKNOWN
        return None
    
    def _extract_boolean(self, text: str, field_name: str) -> Optional[bool]:
        """Extract boolean value."""
        patterns = get_field_patterns(field_name)
        value_str = extract_value_after_label(text, patterns, VALUE_PATTERNS["text_line"])
        if value_str:
            normalized = normalize_text(value_str).lower()
            if VALUE_PATTERNS["boolean_yes"].search(normalized):
                return True
            elif VALUE_PATTERNS["boolean_no"].search(normalized):
                return False
        return None
    
    def _extract_amenities(self, text: str, prop: ComparableProperty) -> None:
        """Extract amenities and features from text."""
        # Look for common amenities in the text
        text_lower = text.lower()
        
        amenity_keywords = {
            "cocina": "Cocina",
            "comedor": "Comedor",
            "living": "Living",
            "quincho": "Quincho",
            "pileta": "Pileta",
            "piscina": "Piscina",
            "parrilla": "Parrilla",
            "jardín": "Jardín",
            "jardin": "Jardín",
            "patio": "Patio",
            "balcón": "Balcón",
            "balcon": "Balcón",
            "terraza": "Terraza",
            "lavadero": "Lavadero",
            "baulera": "Baulera",
            "calefacción": "Calefacción",
            "calefaccion": "Calefacción",
            "aire acondicionado": "Aire Acondicionado",
            "seguridad": "Seguridad",
        }
        
        for keyword, display in amenity_keywords.items():
            if keyword in text_lower:
                prop.amenities.append(display)
                # Set specific boolean flags
                if keyword == "cocina":
                    prop.has_kitchen = True
                elif keyword == "comedor":
                    prop.has_dining_room = True


def extract_pdf(pdf_path: str, num_comparables: int) -> ExtractionResult:
    """Convenience function for PDF extraction."""
    extractor = PDFExtractor()
    return extractor.extract(pdf_path, num_comparables)