"""Regex patterns for PDF field extraction."""
import re
from typing import Dict, List, Optional, Pattern


# Field label patterns (Spanish variations)
FIELD_PATTERNS: Dict[str, List[Pattern]] = {
    "publication_price": [
        re.compile(r'precio\s*(?:de\s*)?publicaci[oó]n[:\s]*', re.IGNORECASE),
        re.compile(r'precio\s*publicado[:\s]*', re.IGNORECASE),
        re.compile(r'precio\s*lista[:\s]*', re.IGNORECASE),
    ],
    "sale_price": [
        re.compile(r'precio\s*(?:de\s*)?venta[:\s]*', re.IGNORECASE),
        re.compile(r'precio\s*vendido[:\s]*', re.IGNORECASE),
        re.compile(r'precio\s*final[:\s]*', re.IGNORECASE),
    ],
    "address": [
        re.compile(r'direcci[oó]n[:\s]*', re.IGNORECASE),
        re.compile(r'ubicaci[oó]n[:\s]*', re.IGNORECASE),
        re.compile(r'domicilio[:\s]*', re.IGNORECASE),
    ],
    "property_type": [
        re.compile(r'tipo\s*(?:de\s*)?propiedad[:\s]*', re.IGNORECASE),
        re.compile(r'tipo\s*(?:de\s*)?inmueble[:\s]*', re.IGNORECASE),
    ],
    "capture_status": [
        re.compile(r'estado\s*(?:de\s*)?(?:la\s*)?captaci[oó]n[:\s]*', re.IGNORECASE),
        re.compile(r'estado[:\s]*', re.IGNORECASE),
    ],
    "total_area": [
        re.compile(r'superficie\s*(?:total|terreno)?[:\s]*', re.IGNORECASE),
        re.compile(r'sup\.?\s*total[:\s]*', re.IGNORECASE),
        re.compile(r'metros\s*totales[:\s]*', re.IGNORECASE),
    ],
    "covered_area": [
        re.compile(r'superficie\s*cubierta[:\s]*', re.IGNORECASE),
        re.compile(r'sup\.?\s*cubierta[:\s]*', re.IGNORECASE),
        re.compile(r'metros\s*cubiertos[:\s]*', re.IGNORECASE),
    ],
    "semi_covered_area": [
        re.compile(r'superficie\s*semicubierta[:\s]*', re.IGNORECASE),
        re.compile(r'sup\.?\s*semicubierta[:\s]*', re.IGNORECASE),
        re.compile(r'semicubierta[:\s]*', re.IGNORECASE),
    ],
    "land_area": [
        re.compile(r'superficie\s*terreno[:\s]*', re.IGNORECASE),
        re.compile(r'sup\.?\s*terreno[:\s]*', re.IGNORECASE),
        re.compile(r'terreno[:\s]*', re.IGNORECASE),
    ],
    "rooms": [
        re.compile(r'ambientes?[:\s]*', re.IGNORECASE),
        re.compile(r'habitaciones?[:\s]*', re.IGNORECASE),
    ],
    "bedrooms": [
        re.compile(r'dormitorios?[:\s]*', re.IGNORECASE),
    ],
    "bathrooms": [
        re.compile(r'baños?[:\s]*', re.IGNORECASE),
        re.compile(r'bañeras?[:\s]*', re.IGNORECASE),
    ],
    "garage": [
        re.compile(r'cochera[:\s]*', re.IGNORECASE),
        re.compile(r'garage[:\s]*', re.IGNORECASE),
        re.compile(r'garaje[:\s]*', re.IGNORECASE),
    ],
    "age": [
        re.compile(r'antig[üu]edad[:\s]*', re.IGNORECASE),
        re.compile(r'años?\s*(?:de\s*)?antig[üu]edad[:\s]*', re.IGNORECASE),
    ],
    "construction_year": [
        re.compile(r'a[ñn]o\s*(?:de\s*)?construcci[oó]n[:\s]*', re.IGNORECASE),
        re.compile(r'a[ñn]o\s*construcci[oó]n[:\s]*', re.IGNORECASE),
    ],
    "days_on_market": [
        re.compile(r'd[ií]as?\s*(?:en\s*)?mercado[:\s]*', re.IGNORECASE),
        re.compile(r'd[ií]as?\s*publicado[:\s]*', re.IGNORECASE),
    ],
    "apto_credito": [
        re.compile(r'apt[oó]\s*cr[eé]dito[:\s]*', re.IGNORECASE),
        re.compile(r'apto\s*para\s*cr[eé]dito[:\s]*', re.IGNORECASE),
    ],
    "financing": [
        re.compile(r'ofrece\s*financiamiento[:\s]*', re.IGNORECASE),
        re.compile(r'financiamiento[:\s]*', re.IGNORECASE),
    ],
    "professional_use": [
        re.compile(r'apt[oó]\s*profesional[:\s]*', re.IGNORECASE),
        re.compile(r'profesional[:\s]*', re.IGNORECASE),
    ],
    "price_per_m2": [
        re.compile(r'precio\s*m[²2]\s*(?:total)?[:\s]*', re.IGNORECASE),
        re.compile(r'valor\s*m[²2][:\s]*', re.IGNORECASE),
        re.compile(r'u\$s\s*/\s*m[²2][:\s]*', re.IGNORECASE),
    ],
}


# Value extraction patterns (what comes after the label)
VALUE_PATTERNS: Dict[str, Pattern] = {
    "price": re.compile(r'(?:U\$?S|USD|\$)\s*([\d.,]+)', re.IGNORECASE),
    "area": re.compile(r'([\d.,]+)\s*m?²?', re.IGNORECASE),
    "number": re.compile(r'([\d.,]+)'),
    "boolean_yes": re.compile(r'^(s[ií]|yes|true|1)\b', re.IGNORECASE),
    "boolean_no": re.compile(r'^(no|false|0)\b', re.IGNORECASE),
    "text_line": re.compile(r'([^\n\r]+)'),
}


def get_field_patterns(field_name: str) -> List[Pattern]:
    """Get regex patterns for a field name."""
    return FIELD_PATTERNS.get(field_name, [])


def extract_value_after_label(text: str, label_patterns: List[Pattern], value_pattern: Pattern) -> Optional[str]:
    """Extract value that appears after a label using value pattern."""
    for label_pattern in label_patterns:
        match = label_pattern.search(text)
        if match:
            # Get text after the label
            after_label = text[match.end():]
            # Find value pattern in the remaining text
            val_match = value_pattern.search(after_label)
            if val_match:
                return val_match.group(1).strip()
            # Fallback: take first line
            line_match = VALUE_PATTERNS["text_line"].search(after_label)
            if line_match:
                return line_match.group(1).strip()
    return None


def find_all_occurrences(text: str, patterns: List[Pattern]) -> List[tuple]:
    """Find all occurrences of patterns in text, returning (position, matched_text)."""
    results = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            results.append((match.start(), match.group()))
    results.sort(key=lambda x: x[0])
    return results