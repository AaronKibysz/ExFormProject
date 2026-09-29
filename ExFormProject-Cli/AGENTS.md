# AGENTS.md - PDF to Excel ACM Generator

## Project Overview

Automate the creation of a Market Comparative Analysis (ACM) Excel file from a real estate PDF document, using an existing Excel file as a template.

## Current Project Status: **~70% Complete**

### ✅ Implemented (Backend Core)
- **Models**: `ComparableProperty`, `PropertyToAnalyze`, enums for PropertyType, CaptureStatus, PriceType
- **PDF Parser**: PyMuPDF-based extraction with semantic pattern matching, regex patterns for all fields
- **Normalization**: Number/price/area parsing (handles comma/point decimals, currency symbols, units)
- **Excel Writer**: xlwings COM automation preserving formulas, formatting, merged cells, images
- **Template Mapping**: PASO 1 sheet row mappings, dynamic formula generation for variable comparables
- **Validation**: Property-level and collection-level validation with warnings/errors
- **Services**: ACMService orchestrating full workflow (PDF → Extract → Validate → Excel)

### 🔄 In Progress / Pending
- **UI Components**: Main window, Preview dialog (PySide6)
- **Entry Point**: main.py
- **Requirements**: requirements.txt
- **Documentation**: README.md
- **Tests**: Unit and integration tests

## Core Principles (Unchanged)

1. **Template Preservation**: Use existing Excel as template - preserve structure, formatting, merged cells, formulas, images, sheets
2. **No Data Invention**: If data isn't in PDF, leave empty/null with warning - never guess or default
3. **Formula Integrity**: Write real Excel formulas, not calculated values
4. **Variable Comparables**: Support N comparable properties (not fixed at 4)
5. **Semantic PDF Parsing**: Identify patterns, not fixed positions
6. **User Verification**: Show preview before generating Excel
7. **Data Normalization**: Clean internal model before Excel mapping

## Technology Stack

- Python 3.12+
- PySide6 for GUI
- PyMuPDF (fitz) for PDF extraction
- xlwings for Excel automation (COM on Windows) - preserves formulas, formatting, structure
- pytest for testing

## Architecture (Implemented Structure)

```
/app
    /models          # ✅ Data models (ComparableProperty, PropertyToAnalyze, enums)
    /pdf_parser      # ✅ PDF extraction (extractor.py, patterns.py)
    /excel           # ✅ Excel template manipulation (template.py, writer.py)
    /services        # ✅ Business logic orchestration (acm_service.py)
    /ui              # 🔄 PySide6 GUI components (main_window.py, preview_dialog.py - PENDING)
    /validation      # ✅ Data validation rules (rules.py)
    /utils           # ✅ Helpers (normalization.py, logging.py)
/tests               # 🔄 Unit and integration tests (PENDING)
```

## Key Data Fields (from PDF)

- publication_price, sale_price
- address, property_type, capture_status
- total_area, covered_area, semi_covered_area, land_area
- rooms, bedrooms, bathrooms, garage
- construction_year, age, days_on_market
- apto_credito, financing, professional_use
- amenities, source_page

## Excel Template Mapping (PASO 1 Sheet)

| Row | Field | Column C | D | E | F | G |
|-----|-------|----------|---|---|---|---|
| 116 | Header | A ANALIZAR | COMP 1 | COMP 2 | COMP 3 | COMP 4 |
| 117 | Precio Dolares | | | | | |
| 118 | Dirección | | | | | |
| 119 | Tipo de Propiedad | | | | | |
| 120 | Estado de la Captación | | | | | |
| 121 | Sup. Cubierta (m2) | | | | | |
| 122 | Sup. Total (m2) | | | | | |
| 123 | Año de Construcción | | | | | |
| 124 | Cocina | | | | | |
| 125 | Comedor | | | | | |
| 126 | Dormitorios | | | | | |
| 127 | Baños | | | | | |
| 128 | Cochera | | | | | |

## Critical Formulas (Must Preserve/Generate)

- **Homogenized Surface**: `={col}121+({col}122-{col}121)/4` (divisor 4 is methodology constant)
- **Unit Value**: `={col}117/{col}181` (Precio / Sup. Homog.)
- **Weighting Factors**: Rows 197, 198, 199 (Ubicación, Categoría, Servicios)
- **Weight Product**: `={col}197*{col}198*{col}199` (Row 200)
- **Result Unit Value**: `={col}188*{col}200` (Row 201)
- **Average Unit Value**: `=AVERAGE(D201:{last_col}201)` - **DYNAMIC** based on N comparables
- **Property Homogenized**: `=C121+(C122-C121)/4` (Row 209, Column C)
- **Property Value**: `=C209*{avg_col}206` (Row 214)

## GUI Requirements (To Implement)

Minimal but functional:
- Select PDF button + path display
- Select Excel template button + path display
- Number of comparables input (spinbox)
- "Analyze PDF" button
- Preview table (editable) - opens in dialog
- "Generate Excel" button
- Log/messages area (QTextEdit)
- Progress bar (QProgressBar)

### UI Flow
1. Select PDF → 2. Select Excel Template → 3. Enter N comparables → 4. Analyze → 5. Preview/Edit → 6. Confirm → 7. Generate

## Remaining Implementation Tasks

### 1. UI Components (Priority: HIGH)
- [ ] `app/ui/main_window.py` - Main application window
- [ ] `app/ui/preview_dialog.py` - Editable property preview table dialog
- [ ] Wire UI to ACMService

### 2. Entry Point (Priority: HIGH)
- [ ] `main.py` - Application entry point with QApplication setup

### 3. Configuration (Priority: MEDIUM)
- [ ] `requirements.txt` - Python dependencies
- [ ] `README.md` - Installation and usage instructions

### 4. Tests (Priority: MEDIUM)
- [ ] `tests/test_normalization.py` - Number/price/area parsing
- [ ] `tests/test_pdf_parser.py` - PDF extraction with sample PDFs
- [ ] `tests/test_excel_writer.py` - Formula generation, template preservation
- [ ] `tests/test_validation.py` - Validation rules
- [ ] `tests/test_integration.py` - End-to-end workflow

## Testing Requirements

- PDF with 4, <4, >4 properties
- Missing fields
- Decimal formats (comma/point)
- Both prices present
- Missing garage, semi-covered area
- Ambiguous data
- Formula preservation verification
- Original file unchanged verification

## Output

- Generated file: `{original_name}_GENERADO.xlsx`
- Never overwrite original
- Selectable output folder

## Logging

Basic logging: INFO/WARNING/ERROR for each step

## Implementation Notes for UI

### Main Window Layout
```
+----------------------------------------------------------+
| ACM Generator                                            |
+----------------------------------------------------------+
| [PDF File:]  [________________________] [Browse...]      |
| [Excel Template:] [_______________] [Browse...]          |
| [Comparables:]  [ 4 ▼ ]                                    |
|                                                          |
| [Analyze PDF]                    [Generate Excel]        |
|                                                          |
| Log:                                                     |
| [____________________________________________________]   |
|                                                          |
| Progress: [##########                    ] 45%          |
+----------------------------------------------------------+
```

### Preview Dialog
- QTableWidget with editable cells
- Columns: ID, Dirección, Precio Pub., Precio Venta, Sup. Cub., Sup. Tot., Sup. Ter., Amb., Dorm., Baños, Cochera, Días, Estado, Advertencias
- Rows: One per comparable + optional "Propiedad a Analizar" row
- Buttons: [Cancel] [Confirm & Generate]

### Key Integration Points
- `ACMService.analyze_pdf()` → returns `ExtractionResult`
- `ACMService.validate_data()` → returns (is_valid, errors, warnings)
- `ACMService.generate_excel()` → returns `ACMGenerationResult`
- Preview dialog receives `List[ComparableProperty]` and `PropertyToAnalyze`
- On confirm, preview dialog returns edited data back to main window