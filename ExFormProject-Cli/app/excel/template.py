"""Excel template structure and mapping definitions."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from string import ascii_uppercase


@dataclass
class CellMapping:
    """Mapping of a data field to Excel cell position."""
    row: int
    col_letter: str  # Base column (e.g., 'D' for first comparable)
    field_name: str
    is_formula: bool = False
    formula_template: Optional[str] = None


# Column letters for comparables (D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z)
# We'll generate dynamically based on number of comparables
def get_comparable_columns(num_comparables: int) -> List[str]:
    """Get column letters for comparable properties starting from D."""
    # D is column 4 (A=1, B=2, C=3, D=4)
    columns = []
    for i in range(num_comparables):
        col_idx = 3 + i  # 0-indexed: D=3
        columns.append(_col_idx_to_letter(col_idx))
    return columns


def _col_idx_to_letter(idx: int) -> str:
    """Convert 0-based column index to Excel letter (A=0, B=1, ...)."""
    result = ""
    while idx >= 0:
        result = chr(ord('A') + (idx % 26)) + result
        idx = idx // 26 - 1
    return result


def _col_letter_to_idx(letter: str) -> int:
    """Convert Excel column letter to 0-based index."""
    result = 0
    for ch in letter:
        result = result * 26 + (ord(ch.upper()) - ord('A') + 1)
    return result - 1


# PASO 1 Sheet - Row mappings (row numbers from template)
PASO1_MAPPINGS = {
    # Row: (field_name, description)
    117: ("price_usd", "Precio Dolares"),
    118: ("address", "Dirección"),
    119: ("property_type", "Tipo de Propiedad"),
    120: ("capture_status", "Estado de la Captación"),
    121: ("covered_area", "Sup. Cubierta (m2)"),
    122: ("total_area", "Sup. Total (m2)"),
    123: ("construction_year", "Año de Construcción"),
    124: ("has_kitchen", "Cocina"),
    125: ("has_dining_room", "Comedor"),
    126: ("bedrooms", "Dormitorios"),
    127: ("bathrooms", "Baños"),
    128: ("garage", "Cochera"),
}

# Formula rows in PASO 1 (these contain formulas that must be preserved/generated)
FORMULA_ROWS = {
    # Homogenized surface: Sup. Cubierta + (Sup. Total - Sup. Cubierta) / 4
    # Row 181 in template (adjust based on actual template)
    "homogenized_surface": {
        "row": 181,
        "formula_template": "={col}{row}+(F{row}-E{row})/4",  # Will be adjusted per column
        "description": "Sup. Homog."
    },
    # Unit value: Precio / Sup. Homog.
    "unit_value": {
        "row": 188,
        "formula_template": "={col}{row}/F{row}",  # Adjusted
        "description": "Valor Unitario"
    },
    # Weighting factors
    "weight_location": {"row": 197, "description": "Ubicación"},
    "weight_category": {"row": 198, "description": "Categoría"},
    "weight_services": {"row": 199, "description": "Servicios"},
    # Weight product: Ubicación × Categoría × Servicios
    "weight_product": {
        "row": 200,
        "formula_template": "={col}{row}*{col}{row_next}*{col}{row_next2}",
        "description": "Producto ponderación"
    },
    # Result unit value: Valor Unitario × Producto ponderación
    "result_unit_value": {
        "row": 201,
        "formula_template": "={col}{price_row}*{col}{weight_row}",
        "description": "Valor Unitario Resultante"
    },
    # Average of result unit values (DYNAMIC range)
    "average_unit_value": {
        "row": 206,
        "formula_template": "=AVERAGE(D{row}:{last_col}{row})",
        "description": "Valor Unitario del m2"
    },
    # Property to analyze - homogenized surface
    "property_homogenized": {
        "row": 209,
        "formula_template": "=C{row}+(D{row}-C{row})/4",  # Column C for property to analyze
        "description": "Sup. Homog. Propiedad"
    },
    # Property value: Sup. Homog. Propiedad × Valor Unitario m2
    "property_value": {
        "row": 214,
        "formula_template": "=C{row}*{avg_col}{avg_row}",
        "description": "Valor de la Propiedad"
    },
}

# Columns in template: C = Property to Analyze, D-G = Comparables 1-4
BASE_COMPARABLE_COL = 'D'  # First comparable column
PROPERTY_COL = 'C'  # Property to analyze column


def get_column_for_comparable(index: int) -> str:
    """Get column letter for comparable at index (0-based)."""
    return chr(ord(BASE_COMPARABLE_COL) + index)


def get_comparable_count_from_template(sheet) -> int:
    """Detect number of comparable columns in template by checking headers."""
    # Check row 116 for headers
    count = 0
    for i in range(20):  # Check up to 20 columns
        col = get_column_for_comparable(i)
        cell_value = sheet.range(f"{col}116").value
        if cell_value and str(cell_value).strip():
            count += 1
        else:
            break
    return max(count, 4)  # At least 4


def build_dynamic_formula(template: str, col: str, row: int, **kwargs) -> str:
    """Build a formula from template with column/row substitutions."""
    return template.format(
        col=col,
        row=row,
        last_col=kwargs.get('last_col', col),
        price_row=kwargs.get('price_row', row),
        weight_row=kwargs.get('weight_row', row),
        avg_col=kwargs.get('avg_col', 'G'),
        avg_row=kwargs.get('avg_row', 206),
        row_next=kwargs.get('row_next', row + 1),
        row_next2=kwargs.get('row_next2', row + 2),
    )