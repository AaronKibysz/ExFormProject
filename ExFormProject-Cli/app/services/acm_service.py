"""Main service orchestrating the ACM generation workflow."""
from typing import List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from app.models import (
    ComparableProperty, PropertyToAnalyze, PriceType, PropertyType, CaptureStatus
)
from app.pdf_parser import PDFExtractor, ExtractionResult
from app.excel import ExcelTemplateWriter, write_excel_template
from app.validation import validate_collection, validate_price_consistency
from app.utils.logging import get_logger, setup_logging


logger = get_logger()


@dataclass
class ACMGenerationResult:
    """Result of ACM generation process."""
    success: bool
    output_path: Optional[str] = None
    properties: List[ComparableProperty] = None
    property_to_analyze: Optional[PropertyToAnalyze] = None
    price_type: PriceType = PriceType.SALE
    validation_errors: List[str] = None
    validation_warnings: List[str] = None
    extraction_warnings: List[str] = None
    message: str = ""
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = []
        if self.validation_errors is None:
            self.validation_errors = []
        if self.validation_warnings is None:
            self.validation_warnings = []
        if self.extraction_warnings is None:
            self.extraction_warnings = []


class ACMService:
    """Main service for ACM generation workflow."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.pdf_extractor = PDFExtractor()
        self.logger = get_logger()
        if log_file:
            setup_logging(Path(log_file))
    
    def analyze_pdf(self, pdf_path: str, num_comparables: int) -> ExtractionResult:
        """
        Analyze PDF and extract comparable properties.
        
        Args:
            pdf_path: Path to PDF file
            num_comparables: Number of comparable properties expected
            
        Returns:
            ExtractionResult with properties and warnings
        """
        logger.info(f"Analyzing PDF: {pdf_path} for {num_comparables} comparables")
        return self.pdf_extractor.extract(pdf_path, num_comparables)
    
    def create_property_to_analyze_form(self) -> PropertyToAnalyze:
        """Create empty property to analyze for manual entry."""
        return PropertyToAnalyze()
    
    def validate_data(
        self, 
        properties: List[ComparableProperty], 
        num_comparables: int,
        property_to_analyze: Optional[PropertyToAnalyze] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate extracted data.
        
        Returns:
            (is_valid, errors, warnings)
        """
        result = validate_collection(properties, num_comparables, property_to_analyze)
        
        # Additional price consistency check
        price_warnings = validate_price_consistency(properties)
        result.warnings.extend(price_warnings)
        
        return result.is_valid, result.errors, result.warnings
    
    def generate_excel(
        self,
        template_path: str,
        output_path: str,
        properties: List[ComparableProperty],
        property_to_analyze: Optional[PropertyToAnalyze],
        price_type: PriceType,
        num_comparables: int
    ) -> ACMGenerationResult:
        """
        Generate the final Excel file from template.
        
        Args:
            template_path: Path to Excel template
            output_path: Path for output file
            properties: List of comparable properties
            property_to_analyze: Property to analyze (column C)
            price_type: Which price to use
            num_comparables: Number of comparables
            
        Returns:
            ACMGenerationResult
        """
        logger.info(f"Generating Excel: {output_path}")
        
        try:
            write_excel_template(
                template_path=template_path,
                output_path=output_path,
                properties=properties,
                property_to_analyze=property_to_analyze,
                price_type=price_type,
                num_comparables=num_comparables
            )
            
            logger.info("Excel generated successfully")
            return ACMGenerationResult(
                success=True,
                output_path=output_path,
                properties=properties,
                property_to_analyze=property_to_analyze,
                price_type=price_type,
                message="Excel generado correctamente"
            )
            
        except Exception as e:
            logger.error(f"Error generating Excel: {e}")
            return ACMGenerationResult(
                success=False,
                message=f"Error generando Excel: {str(e)}"
            )
    
    def run_full_workflow(
        self,
        pdf_path: str,
        template_path: str,
        output_path: str,
        num_comparables: int,
        price_type: PriceType = PriceType.SALE,
        property_to_analyze: Optional[PropertyToAnalyze] = None
    ) -> ACMGenerationResult:
        """
        Run the complete workflow: PDF -> Extract -> Validate -> Excel.
        
        Note: In production, this should be split into steps with user confirmation
        between extraction and Excel generation.
        """
        logger.info("Starting full ACM generation workflow")
        
        # Step 1: Extract from PDF
        extraction_result = self.analyze_pdf(pdf_path, num_comparables)
        
        if not extraction_result.properties:
            return ACMGenerationResult(
                success=False,
                extraction_warnings=extraction_result.warnings,
                message="No se pudieron extraer propiedades del PDF"
            )
        
        # Step 2: Validate
        is_valid, errors, warnings = self.validate_data(
            extraction_result.properties, 
            num_comparables, 
            property_to_analyze
        )
        
        if not is_valid:
            return ACMGenerationResult(
                success=False,
                properties=extraction_result.properties,
                property_to_analyze=property_to_analyze,
                price_type=price_type,
                validation_errors=errors,
                validation_warnings=warnings,
                extraction_warnings=extraction_result.warnings,
                message="Validación fallida: " + "; ".join(errors)
            )
        
        # Step 3: Generate Excel
        result = self.generate_excel(
            template_path=template_path,
            output_path=output_path,
            properties=extraction_result.properties,
            property_to_analyze=property_to_analyze,
            price_type=price_type,
            num_comparables=num_comparables
        )
        
        result.extraction_warnings = extraction_result.warnings
        result.validation_warnings = warnings
        
        return result


def create_default_output_path(template_path: str) -> str:
    """Create default output path from template path."""
    template = Path(template_path)
    stem = template.stem
    suffix = template.suffix
    output = template.parent / f"{stem}_GENERADO{suffix}"
    
    # If file exists, add number
    counter = 1
    while output.exists():
        output = template.parent / f"{stem}_GENERADO_{counter}{suffix}"
        counter += 1
    
    return str(output)