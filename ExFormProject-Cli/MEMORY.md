# MEMORY.md - Project Context for PDF to Excel ACM Generator

## Project State

**Status**: Initial specification complete. No code implemented yet.
**Location**: `C:\Users\Aaron\Desktop\ExFormProject\ExFormProject-Cli`

## User Requirements Summary

The user wants a Windows desktop application that:
1. Takes a real estate PDF with comparable properties
2. Uses an existing Excel file as a template (preserving ALL formatting, formulas, structure)
3. Extracts property data from PDF using semantic pattern matching
4. Shows editable preview for user verification
5. Generates a NEW Excel file (copy of template) populated with extracted data
6. Supports variable number of comparable properties (1 to N)
7. Maintains real Excel formulas (not static values)
8. Handles missing data gracefully (null + warnings, never invented)

## Key Technical Decisions

### PDF Parsing
- **Library**: PyMuPDF (fitz) - robust text extraction with position info
- **Approach**: Semantic pattern matching with regex, not fixed positions
- **Normalization**: Handle decimals (comma/point), currency symbols, units, accents
- **OCR**: Not in v1 - show clear message if PDF is scanned

### Excel Manipulation
- **Library**: xlwings (Windows COM automation) - ONLY way to truly preserve:
  - Formulas as formulas
  - All formatting/styles/borders/merged cells
  - Images
  - Sheet structure
  - Number formats
- **Alternative considered**: openpyxl - rejected because it doesn't preserve formulas reliably when modifying existing complex templates

### GUI Framework
- **Library**: PySide6 (Qt6) - native look, good Windows support
- **Style**: Basic/functional - no custom styling, no modern UI frameworks

### Data Flow
```
PDF → Parser → Normalized Models → Validation → Preview (editable) → Excel Writer → Output
```
Each layer isolated - parser knows nothing about Excel, writer knows nothing about PDF.

## Critical Implementation Details

### Variable Comparables Handling
- Template has 4 comparable columns (D-G)
- If N > 4: Insert columns, copy format/formulas from column G, adjust references
- If N < 4: Clear data in extra columns, keep structure
- Dynamic formula ranges: `AVERAGE(D201:{col}201)` where {col} = last comparable column

### Formula Preservation Rules
1. NEVER write calculated values to formula cells
2. Homogenization divisor (4) is methodology constant - DON'T change based on N
3. Only AVERAGE range and similar multi-col formulas adapt to N
4. Copy formulas from template reference column when expanding

### Property to Analyze (Col C)
- If PDF has it: Extract
- If PDF doesn't: Show input form
- NEVER default to first comparable

### Price Selection
- Extract BOTH publication_price and sale_price
- Show both in preview
- Let user choose which goes to "Precio Dolares" (row 117)
- Consistent choice across all properties

## Test PDF Data (for verification only - NOT hardcode)

4 comparables with known values:
- Comp 1: Luzuriaga 300, Pub:73000/Sale:60000, Cov:140, Tot:160, Land:300, Rooms:3, Bed:3, Bath:1, Gar:2, Age:26, Days:95
- Comp 2: Pasteur 900, Pub:52000/Sale:47000, Cov:118, Tot:118, Land:150, Rooms:5, Bed:3, Bath:2, Gar:1, Age:66, Days:62
- Comp 3: Juan F. Cobos 1800, Pub:100000/Sale:82000, Cov:134.08, Tot:239.38, Land:239.38, Rooms:4, Bed:3, Bath:1, Gar:1, Age:45, Days:37
- Comp 4: Juan F. Cobos 200, Pub:70000/Sale:70000, Cov:168, Tot:168, Land:252, Rooms:3, Bed:2, Bath:1, Gar:1, Age:53, Days:62

## Development Priority Order

1. PDF reading & extraction
2. Property detection & data extraction
3. Data normalization/model
4. Preview UI
5. Excel template modification
6. Format preservation
7. Formula generation
8. Variable comparables
9. Validation
10. Aesthetics (last)

## Dependencies to Document

- Python 3.12+
- PySide6
- PyMuPDF (fitz)
- xlwings (requires Microsoft Excel installed on Windows)
- pytest

## Files to Create

```
/app
    /models/__init__.py
    /models/property.py
    /pdf_parser/__init__.py
    /pdf_parser/extractor.py
    /pdf_parser/patterns.py
    /excel/__init__.py
    /excel/template.py
    /excel/writer.py
    /services/__init__.py
    /services/acm_service.py
    /ui/__init__.py
    /ui/main_window.py
    /ui/preview_dialog.py
    /validation/__init__.py
    /validation/rules.py
    /utils/__init__.py
    /utils/normalization.py
    /utils/logging.py
    /__init__.py
/main.py
/requirements.txt
/README.md
/tests/
    /test_pdf_parser.py
    /test_excel_writer.py
    /test_normalization.py
    /test_integration.py
```