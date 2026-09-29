"""Normalization utilities for data extraction."""
import re
from typing import Optional, Union


# Regex patterns for extraction
PRICE_PATTERN = re.compile(
    r'(?:U\$?S|USD|\$)\s*([\d.,]+)',
    re.IGNORECASE
)

AREA_PATTERN = re.compile(
    r'([\d.,]+)\s*m?²?',
    re.IGNORECASE
)

NUMBER_PATTERN = re.compile(
    r'([\d.,]+)'
)

YEAR_PATTERN = re.compile(
    r'(?:año|antigüedad|construcción)[^\d]*(\d{2,4})',
    re.IGNORECASE
)

DAYS_PATTERN = re.compile(
    r'(?:días?\s*(?:en\s*)?mercado)[^\d]*(\d+)',
    re.IGNORECASE
)

ROOMS_PATTERN = re.compile(
    r'(?:ambientes?|habitaciones?)[^\d]*(\d+)',
    re.IGNORECASE
)

BEDROOMS_PATTERN = re.compile(
    r'(?:dormitorios?)[^\d]*(\d+)',
    re.IGNORECASE
)

BATHROOMS_PATTERN = re.compile(
    r'(?:baños?|bañeras?)[^\d]*(\d+)',
    re.IGNORECASE
)

GARAGE_PATTERN = re.compile(
    r'(?:cochera|garage|garaje)[^\d]*(\d+)',
    re.IGNORECASE
)


def normalize_number(value: str) -> Optional[float]:
    """
    Normalize a numeric string to float.
    Handles: 160, 160.00, 160,00, 239.38, 239,38
    """
    if not value:
        return None
    
    # Remove currency symbols, spaces, units
    # Remove USD, U$S, U$D, $, m², m2, m2, etc.
    cleaned = re.sub(r'(?:USD|U\$?S|U\$?D|\$|m\s*[²2])', '', value, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', '', cleaned).strip()
    
    # Handle thousands separators and decimal
    # If both . and , present, last one is decimal separator
    if '.' in cleaned and ',' in cleaned:
        # Determine which is decimal separator (last one)
        last_dot = cleaned.rfind('.')
        last_comma = cleaned.rfind(',')
        if last_comma > last_dot:
            # Comma is decimal separator
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # Dot is decimal separator
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Only comma - could be decimal or thousands
        # If 1 or 2 digits after comma, it's decimal
        parts = cleaned.split(',')
        if len(parts[-1]) <= 2 and len(parts) == 2:
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif '.' in cleaned:
        # Only dot - similar logic
        parts = cleaned.split('.')
        if len(parts[-1]) <= 2 and len(parts) == 2:
            pass  # Already decimal
        else:
            cleaned = cleaned.replace('.', '')
    
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_int(value: str) -> Optional[int]:
    """Normalize to integer."""
    num = normalize_number(value)
    if num is not None:
        return int(num)
    return None


def normalize_price(text: str) -> Optional[float]:
    """Extract and normalize price from text."""
    if not text:
        return None
    match = PRICE_PATTERN.search(text)
    if match:
        return normalize_number(match.group(1))
    # Try to find any number in the text
    match = NUMBER_PATTERN.search(text)
    if match:
        return normalize_number(match.group(1))
    return None


def normalize_area(text: str) -> Optional[float]:
    """Extract and normalize area from text."""
    if not text:
        return None
    match = AREA_PATTERN.search(text)
    if match:
        return normalize_number(match.group(1))
    match = NUMBER_PATTERN.search(text)
    if match:
        return normalize_number(match.group(1))
    return None


def normalize_text(text: Optional[str]) -> Optional[str]:
    """Normalize text: strip, collapse whitespace, handle None."""
    if not text:
        return None
    # Replace multiple whitespace with single space
    normalized = re.sub(r'\s+', ' ', text.strip())
    return normalized if normalized else None


def extract_field_value(text: str, field_patterns: list) -> Optional[str]:
    """Extract value after a field label using multiple possible patterns."""
    for pattern in field_patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def find_property_blocks(text: str) -> list:
    """
    Split text into potential property blocks.
    Looks for patterns that indicate start of a property listing.
    """
    # Common property start patterns
    start_patterns = [
        r'venta\s+casa',
        r'venta\s+departamento',
        r'casa\s+cerrada',
        r'departamento',
        r'propiedad',
        r'comparable\s+\d+',
        r'comparable\s+n[º°]?\s*\d+',
    ]
    
    combined_pattern = '|'.join(f'({p})' for p in start_patterns)
    regex = re.compile(combined_pattern, re.IGNORECASE)
    
    matches = list(regex.finditer(text))
    if not matches:
        return [text]  # Return whole text as one block
    
    blocks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append(text[start:end])
    
    return blocks


def clean_extracted_value(value: str, field_type: str) -> Union[str, float, int, None]:
    """Clean and type-convert extracted value based on field type."""
    if not value:
        return None
    
    value = normalize_text(value)
    if not value:
        return None
    
    if field_type in ('price', 'publication_price', 'sale_price'):
        return normalize_price(value)
    elif field_type in ('total_area', 'covered_area', 'semi_covered_area', 'land_area'):
        return normalize_area(value)
    elif field_type in ('rooms', 'bedrooms', 'bathrooms', 'garage', 'age', 'days_on_market', 'construction_year'):
        return normalize_int(value)
    elif field_type == 'address':
        return value
    else:
        return value