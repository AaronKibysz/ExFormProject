"""Excel template writer using xlwings (COM automation)."""
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import xlwings as xw

from app.models import ComparableProperty, PropertyToAnalyze, PriceType
from app.excel.template import (
    PASO1_MAPPINGS, FORMULA_ROWS, BASE_COMPARABLE_COL, PROPERTY_COL,
    get_column_for_comparable, get_comparable_count_from_template,
    build_dynamic_formula
)
from app.utils.logging import get_logger


logger = get_logger()
MISSING_FIELD_COLOR = (255, 242, 204)


class ExcelTemplateWriter:
    """Write data to Excel template preserving all formatting and formulas."""
    
    def __init__(self, template_path: str, output_path: str):
        self.template_path = Path(template_path).resolve()
        self.output_path = Path(output_path).resolve()
        self.app: Optional[xw.App] = None
        self.wb: Optional[xw.Book] = None
        self._original_wb: Optional[xw.Book] = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def open(self) -> None:
        """Open template and create a copy for editing."""
        logger.info(f"Opening template: {self.template_path}")
        
        # Start Excel app (invisible)
        self.app = xw.App(visible=False, add_book=False)
        self.app.display_alerts = False
        self.app.screen_updating = False
        
        # Open template
        self._original_wb = self.app.books.open(str(self.template_path))
        
        # Save as new file (creates the copy)
        logger.info(f"Creating output copy: {self.output_path}")
        self._original_wb.save(str(self.output_path))
        self._original_wb.close()
        
        # Open the copy for editing
        self.wb = self.app.books.open(str(self.output_path))
        logger.info("Template copy opened for editing")
    
    def close(self) -> None:
        """Close workbook and Excel app."""
        if self.wb:
            self.wb.save()
            self.wb.close()
            self.wb = None
            logger.info("Workbook saved and closed")
        
        if self.app:
            self.app.quit()
            self.app = None
            logger.info("Excel app closed")
    
    def write_properties(
        self, 
        properties: List[ComparableProperty], 
        property_to_analyze: Optional[PropertyToAnalyze],
        price_type: PriceType,
        num_comparables: int
    ) -> None:
        """
        Write all property data to the Excel template.
        
        Args:
            properties: List of comparable properties
            property_to_analyze: Property being analyzed (column C)
            price_type: Which price to use (publication or sale)
            num_comparables: Number of comparable properties
        """
        if not self.wb:
            raise RuntimeError("Workbook not open. Call open() first.")
        
        logger.info(f"Writing {len(properties)} comparable properties")
        
        # Get PASO 1 sheet
        sheet = self._get_sheet("PASO 1")
        if not sheet:
            # Try alternative names
            for name in ["PASO1", "Paso 1", "Hoja1", "Sheet1"]:
                sheet = self._get_sheet(name)
                if sheet:
                    break
        
        if not sheet:
            raise ValueError("Could not find PASO 1 sheet in template")
        
        # Write property to analyze (Column C)
        if property_to_analyze:
            self._write_property_to_analyze(sheet, property_to_analyze)
        
        # Write comparable properties (Columns D onwards)
        for i, prop in enumerate(properties):
            if i >= num_comparables:
                break
            col = get_column_for_comparable(i)
            self._write_comparable(sheet, prop, col, price_type)
        
        # Clear extra columns if fewer properties than template has
        template_comparables = get_comparable_count_from_template(sheet)
        for i in range(len(properties), template_comparables):
            if i >= num_comparables:
                col = get_column_for_comparable(i)
                self._clear_comparable_column(sheet, col)
        
        # Generate/update formulas for variable comparables
        self._generate_formulas(sheet, num_comparables)
        
        logger.info("Property data written successfully")
    
    def _get_sheet(self, name: str) -> Optional[xw.Sheet]:
        """Get sheet by name (case-insensitive)."""
        try:
            return self.wb.sheets[name]
        except Exception:
            # Try case-insensitive
            for sheet in self.wb.sheets:
                if sheet.name.lower() == name.lower():
                    return sheet
        return None
    
    def _write_property_to_analyze(self, sheet: xw.Sheet, prop: PropertyToAnalyze) -> None:
        """Write property to analyze data to column C."""
        col = PROPERTY_COL
        logger.debug(f"Writing property to analyze to column {col}")
        
        mappings = {
            "address": prop.address,
            "property_type": prop.property_type.value if prop.property_type else None,
            "capture_status": prop.capture_status.value if prop.capture_status else None,
            "covered_area": prop.covered_area,
            "total_area": prop.total_area,
            "construction_year": prop.construction_year,
            "has_kitchen": 1 if prop.has_kitchen else 0 if prop.has_kitchen is not None else None,
            "has_dining_room": 1 if prop.has_dining_room else 0 if prop.has_dining_room is not None else None,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "garage": prop.garage,
        }
        
        for row, (field_name, _) in PASO1_MAPPINGS.items():
            value = mappings.get(field_name)
            if value is not None:
                cell = sheet.range(f"{col}{row}")
                cell.value = value
                logger.debug(f"  {col}{row} ({field_name}) = {value}")
    
    def _write_comparable(
        self, 
        sheet: xw.Sheet, 
        prop: ComparableProperty, 
        col: str,
        price_type: PriceType
    ) -> None:
        """Write a single comparable property to its column."""
        logger.debug(f"Writing comparable {prop.id} to column {col}")
        
        # Get price based on selected type
        price = prop.get_price_for_excel(price_type)
        
        mappings = {
            "price_usd": price,
            "address": prop.address,
            "property_type": prop.property_type.value if prop.property_type else None,
            "capture_status": prop.capture_status.value if prop.capture_status else None,
            "covered_area": prop.covered_area,
            "total_area": prop.total_area,
            "construction_year": prop.construction_year,
            "has_kitchen": 1 if prop.has_kitchen else 0 if prop.has_kitchen is not None else None,
            "has_dining_room": 1 if prop.has_dining_room else 0 if prop.has_dining_room is not None else None,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "garage": prop.garage,
        }
        
        for row, (field_name, _) in PASO1_MAPPINGS.items():
            value = mappings.get(field_name)
            cell = sheet.range(f"{col}{row}")
            if value is not None:
                cell.value = value
                logger.debug(f"  {col}{row} ({field_name}) = {value}")
            elif field_name in {"price_usd", "address", "covered_area", "total_area"}:
                cell.value = None
                cell.color = MISSING_FIELD_COLOR
    
    def _clear_comparable_column(self, sheet: xw.Sheet, col: str) -> None:
        """Clear data from a comparable column (keep formulas)."""
        logger.debug(f"Clearing extra column {col}")
        
        for row, (field_name, _) in PASO1_MAPPINGS.items():
            cell = sheet.range(f"{col}{row}")
            # Only clear if it's not a formula
            if not (cell.formula and cell.formula.startswith("=")):
                cell.value = None
    
    def _generate_formulas(self, sheet: xw.Sheet, num_comparables: int) -> None:
        """Generate/update dynamic formulas based on number of comparables."""
        logger.info(f"Generating formulas for {num_comparables} comparables")
        
        last_col = get_column_for_comparable(num_comparables - 1)
        first_col = BASE_COMPARABLE_COL
        
        # 1. Homogenized Surface formulas (row 181)
        # Formula: =E181+(F181-E181)/4 for each comparable column
        # But wait - the template uses E and F as fixed columns?
        # Let me check: In template, D=Comp1, E=Comp2, F=Comp3, G=Comp4
        # The formula in row 181 for each column should reference that column's covered and total
        
        homog_row = FORMULA_ROWS["homogenized_surface"]["row"]
        covered_row = 121  # Sup. Cubierta
        total_row = 122    # Sup. Total
        
        for i in range(num_comparables):
            col = get_column_for_comparable(i)
            # Formula: Covered + (Total - Covered) / 4
            formula = f"={col}{covered_row}+({col}{total_row}-{col}{covered_row})/4"
            sheet.range(f"{col}{homog_row}").formula = formula
            logger.debug(f"  {col}{homog_row} = {formula}")
        
        # 2. Unit Value formulas (row 188)
        # Formula: Precio / Sup. Homog.
        price_row = 117
        unit_value_row = FORMULA_ROWS["unit_value"]["row"]
        
        for i in range(num_comparables):
            col = get_column_for_comparable(i)
            formula = f"={col}{price_row}/{col}{homog_row}"
            sheet.range(f"{col}{unit_value_row}").formula = formula
            logger.debug(f"  {col}{unit_value_row} = {formula}")
        
        # 3. Weight Product formulas (row 200)
        # Formula: Ubicación × Categoría × Servicios
        weight_rows = [197, 198, 199]
        weight_product_row = FORMULA_ROWS["weight_product"]["row"]
        
        for i in range(num_comparables):
            col = get_column_for_comparable(i)
            formula = f"={col}{weight_rows[0]}*{col}{weight_rows[1]}*{col}{weight_rows[2]}"
            sheet.range(f"{col}{weight_product_row}").formula = formula
            logger.debug(f"  {col}{weight_product_row} = {formula}")
        
        # 4. Result Unit Value formulas (row 201)
        # Formula: Valor Unitario × Producto Ponderación
        result_unit_row = FORMULA_ROWS["result_unit_value"]["row"]
        
        for i in range(num_comparables):
            col = get_column_for_comparable(i)
            formula = f"={col}{unit_value_row}*{col}{weight_product_row}"
            sheet.range(f"{col}{result_unit_row}").formula = formula
            logger.debug(f"  {col}{result_unit_row} = {formula}")
        
        # 5. Average Unit Value (row 206) - DYNAMIC RANGE
        avg_row = FORMULA_ROWS["average_unit_value"]["row"]
        avg_formula = f"=AVERAGE({first_col}{avg_row}:{last_col}{avg_row})"
        # The average is typically in column G or the column after last comparable
        # Let's put it in the column after the last comparable
        avg_col = get_column_for_comparable(num_comparables)
        sheet.range(f"{avg_col}{avg_row}").formula = avg_formula
        logger.debug(f"  {avg_col}{avg_row} = {avg_formula}")
        
        # 6. Property Homogenized Surface (row 209) - Column C
        prop_homog_row = FORMULA_ROWS["property_homogenized"]["row"]
        prop_covered_row = 121
        prop_total_row = 122
        prop_formula = f"=C{prop_covered_row}+(C{prop_total_row}-C{prop_covered_row})/4"
        sheet.range(f"C{prop_homog_row}").formula = prop_formula
        logger.debug(f"  C{prop_homog_row} = {prop_formula}")
        
        # 7. Property Value (row 214) - Column C
        prop_value_row = FORMULA_ROWS["property_value"]["row"]
        prop_value_formula = f"=C{prop_homog_row}*{avg_col}{avg_row}"
        sheet.range(f"C{prop_value_row}").formula = prop_value_formula
        logger.debug(f"  C{prop_value_row} = {prop_value_formula}")
        
        logger.info("All formulas generated successfully")


def write_excel_template(
    template_path: str,
    output_path: str,
    properties: List[ComparableProperty],
    property_to_analyze: Optional[PropertyToAnalyze],
    price_type: PriceType,
    num_comparables: int
) -> None:
    """Convenience function to write Excel template."""
    with ExcelTemplateWriter(template_path, output_path) as writer:
        writer.write_properties(properties, property_to_analyze, price_type, num_comparables)