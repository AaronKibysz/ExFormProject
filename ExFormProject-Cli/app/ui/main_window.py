"""Main application window for ACM Generator."""
import sys
import os
import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QTextEdit,
    QProgressBar, QFileDialog, QMessageBox, QGroupBox,
    QFormLayout, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont

from app.models import ComparableProperty, PropertyToAnalyze, PriceType
from app.services import ACMService, ACMGenerationResult, create_default_output_path
from app.utils.logging import setup_logging, get_logger


logger = get_logger()


class WorkerThread(QThread):
    """Background thread for long-running operations."""
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int, str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            def progress_callback(pct: int, msg: str):
                self.progress.emit(pct, msg)
            
            # Add progress callback to kwargs if the function supports it
            self.kwargs['progress_callback'] = progress_callback
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            logger.exception("Worker thread error")
            self.error.emit(str(e))


class PreviewDialog(QWidget):
    """Dialog for previewing and editing extracted properties."""
    
    def __init__(self, properties: List[ComparableProperty], 
                 property_to_analyze: Optional[PropertyToAnalyze],
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vista Previa - Propiedades Detectadas")
        self.resize(1000, 500)
        self.setWindowFlags(Qt.Window)
        
        self.properties = properties
        self.property_to_analyze = property_to_analyze
        self.confirmed = False
        self.edited_properties = []
        self.edited_property_to_analyze = None
        
        self._setup_ui()
        self._populate_table()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        info_label = QLabel(
            "Verifique y edite los datos extraídos. "
            "Haga doble clic en una celda para modificarla."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)
        
        # Table
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "ID", "Dirección", "Precio Pub.", "Precio Venta",
            "Sup. Cub.", "Sup. Tot.", "Sup. Ter.", "Amb.",
            "Dorm.", "Baños", "Cochera", "Días", "Estado", "Advertencias"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.cancel_btn)
        
        self.confirm_btn = QPushButton("Confirmar y Generar")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(btn_layout)
    
    def _populate_table(self):
        """Fill table with property data."""
        all_props = []
        if self.property_to_analyze and self.property_to_analyze.has_essential_data():
            all_props.append(("ANALIZAR", self.property_to_analyze))
        
        for i, prop in enumerate(self.properties):
            all_props.append((f"COMP {i+1}", prop))
        
        self.table.setRowCount(len(all_props))
        
        for row, (prefix, prop) in enumerate(all_props):
            # ID column
            id_item = QTableWidgetItem(f"{prefix} ({prop.id})")
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, id_item)
            
            # Data columns
            data = [
                prop.address or "",
                str(prop.publication_price) if prop.publication_price else "",
                str(prop.sale_price) if prop.sale_price else "",
                str(prop.covered_area) if prop.covered_area else "",
                str(prop.total_area) if prop.total_area else "",
                str(prop.land_area) if prop.land_area else "",
                str(prop.rooms) if prop.rooms else "",
                str(prop.bedrooms) if prop.bedrooms else "",
                str(prop.bathrooms) if prop.bathrooms else "",
                str(prop.garage) if prop.garage else "",
                str(prop.days_on_market) if prop.days_on_market else "",
                prop.capture_status.value if prop.capture_status else "",
                "; ".join(prop.extraction_warnings) if prop.extraction_warnings else "",
            ]
            
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))
                if col == 13:  # Warnings column - read only
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col + 1, item)
    
    def _on_confirm(self):
        """Extract edited data and confirm."""
        self.edited_properties = []
        self.edited_property_to_analyze = None
        
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 0)
            if not id_item:
                continue
            
            prefix = id_item.text().split(" ")[0]
            
            # Extract values from table
            def get_val(col):
                item = self.table.item(row, col)
                return item.text().strip() if item else ""
            
            addr = get_val(1)
            pub_price = get_val(2)
            sale_price = get_val(3)
            cov_area = get_val(4)
            tot_area = get_val(5)
            land_area = get_val(6)
            rooms = get_val(7)
            bedrooms = get_val(8)
            bathrooms = get_val(9)
            garage = get_val(10)
            days = get_val(11)
            status = get_val(12)
            
            if prefix == "ANALIZAR":
                prop = PropertyToAnalyze(
                    address=addr or None,
                    covered_area=float(cov_area) if cov_area else None,
                    total_area=float(tot_area) if tot_area else None,
                    bedrooms=int(bedrooms) if bedrooms else None,
                    bathrooms=int(bathrooms) if bathrooms else None,
                    garage=int(garage) if garage else None,
                )
                self.edited_property_to_analyze = prop
            else:
                prop = ComparableProperty(
                    id=int(id_item.text().split("(")[-1].rstrip(")")),
                    address=addr or None,
                    publication_price=float(pub_price) if pub_price else None,
                    sale_price=float(sale_price) if sale_price else None,
                    covered_area=float(cov_area) if cov_area else None,
                    total_area=float(tot_area) if tot_area else None,
                    land_area=float(land_area) if land_area else None,
                    rooms=int(rooms) if rooms else None,
                    bedrooms=int(bedrooms) if bedrooms else None,
                    bathrooms=int(bathrooms) if bathrooms else None,
                    garage=int(garage) if garage else None,
                    days_on_market=int(days) if days else None,
                    capture_status=type('obj', (object,), {'value': status})() if status else None,
                )
                self.edited_properties.append(prop)
        
        self.confirmed = True
        self.close()
    
    def get_results(self):
        """Return edited data if confirmed."""
        if self.confirmed:
            return self.edited_properties, self.edited_property_to_analyze
        return None, None


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ACM Generator - Análisis Comparativo de Mercado")
        self.resize(700, 600)
        
        self.pdf_path = ""
        self.template_path = ""
        self.service = ACMService()
        self.extraction_result = None
        self.price_type = PriceType.SALE
        
        self._setup_ui()
        self._setup_logging()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Generador de ACM - Análisis Comparativo de Mercado")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # File selection group
        file_group = QGroupBox("Archivos")
        file_layout = QFormLayout(file_group)
        
        # PDF
        pdf_layout = QHBoxLayout()
        self.pdf_edit = QLineEdit()
        self.pdf_edit.setReadOnly(True)
        self.pdf_edit.setPlaceholderText("Seleccione un archivo PDF...")
        pdf_btn = QPushButton("Seleccionar PDF")
        pdf_btn.clicked.connect(self._select_pdf)
        pdf_layout.addWidget(self.pdf_edit)
        pdf_layout.addWidget(pdf_btn)
        file_layout.addRow("PDF:", pdf_layout)
        
        # Excel Template
        excel_layout = QHBoxLayout()
        self.excel_edit = QLineEdit()
        self.excel_edit.setReadOnly(True)
        self.excel_edit.setPlaceholderText("Seleccione plantilla Excel...")
        excel_btn = QPushButton("Seleccionar Excel")
        excel_btn.clicked.connect(self._select_excel)
        excel_layout.addWidget(self.excel_edit)
        excel_layout.addWidget(excel_btn)
        file_layout.addRow("Plantilla:", excel_layout)
        
        layout.addWidget(file_group)
        
        # Options group
        options_group = QGroupBox("Opciones")
        options_layout = QFormLayout(options_group)
        
        # Number of comparables
        self.comparables_spin = QSpinBox()
        self.comparables_spin.setRange(1, 20)
        self.comparables_spin.setValue(4)
        options_layout.addRow("N° Comparables:", self.comparables_spin)
        
        # Price type
        self.price_combo = QComboBox()
        self.price_combo.addItems(["Precio de Venta", "Precio de Publicación"])
        self.price_combo.setCurrentIndex(0)
        self.price_combo.currentIndexChanged.connect(self._on_price_type_changed)
        options_layout.addRow("Precio a usar:", self.price_combo)
        
        layout.addWidget(options_group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("Analizar PDF")
        self.analyze_btn.setMinimumHeight(40)
        self.analyze_btn.clicked.connect(self._analyze_pdf)
        self.analyze_btn.setEnabled(False)
        btn_layout.addWidget(self.analyze_btn)
        
        self.generate_btn = QPushButton("Generar Excel")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.clicked.connect(self._generate_excel)
        self.generate_btn.setEnabled(False)
        btn_layout.addWidget(self.generate_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log area
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # Status bar
        self.statusBar().showMessage("Listo")
    
    def _setup_logging(self):
        """Set up logging to UI."""
        # Redirect logger to also output to UI
        import logging
        ui_handler = UILogHandler(self.log_text)
        ui_handler.setLevel(logging.INFO)
        ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
        get_logger().addHandler(ui_handler)
    
    def _log(self, msg: str, level: str = "INFO"):
        """Add message to log display."""
        self.log_text.append(f"[{level}] {msg}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def _select_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar PDF", "", "PDF Files (*.pdf)"
        )
        if path:
            self.pdf_path = path
            self.pdf_edit.setText(path)
            self._log(f"PDF seleccionado: {Path(path).name}")
            self._check_ready_to_analyze()
    
    def _select_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Plantilla Excel", "", "Excel Files (*.xlsx *.xls)"
        )
        if path:
            self.template_path = path
            self.excel_edit.setText(path)
            self._log(f"Plantilla seleccionada: {Path(path).name}")
            self._check_ready_to_analyze()
    
    def _check_ready_to_analyze(self):
        self.analyze_btn.setEnabled(bool(self.pdf_path and self.template_path))
    
    def _on_price_type_changed(self, index: int):
        self.price_type = PriceType.SALE if index == 0 else PriceType.PUBLICATION
        self._log(f"Tipo de precio: {self.price_type.value}")
    
    def _analyze_pdf(self):
        """Start PDF analysis in background thread."""
        num_comparables = self.comparables_spin.value()
        
        self.analyze_btn.setEnabled(False)
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self._log(f"Iniciando análisis de PDF ({num_comparables} comparables)...")
        
        self.worker = WorkerThread(
            self.service.analyze_pdf,
            self.pdf_path,
            num_comparables
        )
        self.worker.finished.connect(self._on_analysis_finished)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.progress.connect(self._on_progress)
        self.worker.start()
    
    @Slot(object)
    def _on_analysis_finished(self, result):
        """Handle analysis completion."""
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        
        self.extraction_result = result
        
        if result.warnings:
            for w in result.warnings:
                self._log(w, "WARNING")
        
        self._log(f"Extracción completada: {len(result.properties)} propiedades detectadas")
        
        if not result.properties:
            QMessageBox.warning(self, "Advertencia", 
                "No se detectaron propiedades en el PDF.\n"
                "Verifique que el PDF contenga texto extraíble.")
            return
        
        # Validate
        is_valid, errors, warnings = self.service.validate_data(
            result.properties, self.comparables_spin.value(), None
        )
        
        for w in warnings:
            self._log(w, "WARNING")
        
        if errors:
            for e in errors:
                self._log(e, "ERROR")
            QMessageBox.warning(self, "Validación", 
                "Se encontraron errores:\n" + "\n".join(errors) +
                "\n\nPuede continuar pero revise la vista previa.")
        
        # Show preview dialog
        self._show_preview()
    
    @Slot(str)
    def _on_analysis_error(self, error_msg: str):
        """Handle analysis error."""
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self._log(f"Error: {error_msg}", "ERROR")
        QMessageBox.critical(self, "Error", f"Error analizando PDF:\n{error_msg}")
    
    @Slot(int, str)
    def _on_progress(self, pct: int, msg: str):
        """Handle progress update."""
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(pct)
        self._log(msg)
    
    def _show_preview(self):
        """Show preview dialog."""
        if not self.extraction_result:
            return
        
        dialog = PreviewDialog(
            self.extraction_result.properties,
            None,  # Property to analyze - could add separate form
            self
        )
        dialog.exec()
        
        edited_props, edited_analyze = dialog.get_results()
        if edited_props is not None:
            self.extraction_result.properties = edited_props
            self.generate_btn.setEnabled(True)
            self._log("Vista previa confirmada. Listo para generar Excel.")
        else:
            self._log("Vista previa cancelada.")
    
    def _generate_excel(self):
        """Generate Excel file."""
        if not self.extraction_result or not self.extraction_result.properties:
            QMessageBox.warning(self, "Advertencia", "No hay datos para generar.")
            return
        
        # Determine output path
        default_output = create_default_output_path(self.template_path)
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel Generado", default_output, "Excel Files (*.xlsx)"
        )
        
        if not output_path:
            return
        
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self._log("Generando Excel...")
        
        self.worker = WorkerThread(
            self.service.generate_excel,
            self.template_path,
            output_path,
            self.extraction_result.properties,
            None,  # property_to_analyze
            self.price_type,
            self.comparables_spin.value()
        )
        self.worker.finished.connect(self._on_generation_finished)
        self.worker.error.connect(self._on_generation_error)
        self.worker.start()
    
    @Slot(object)
    def _on_generation_finished(self, result: ACMGenerationResult):
        """Handle generation completion."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        if result.success:
            self._log(f"Excel generado: {Path(result.output_path).name}", "INFO")
            QMessageBox.information(self, "Éxito", 
                f"Excel generado correctamente:\n{result.output_path}")
        else:
            self._log(f"Error: {result.message}", "ERROR")
            QMessageBox.critical(self, "Error", result.message)
    
    @Slot(str)
    def _on_generation_error(self, error_msg: str):
        """Handle generation error."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        self._log(f"Error: {error_msg}", "ERROR")
        QMessageBox.critical(self, "Error", f"Error generando Excel:\n{error_msg}")


class UILogHandler(logging.Handler):
    """Logging handler that writes to QTextEdit."""
    
    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.text_edit = text_edit
    
    def emit(self, record):
        msg = self.format(record)
        # Use QMetaObject.invokeMethod for thread safety
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.text_edit, "append",
            Qt.QueuedConnection,
            Q_ARG(str, msg)
        )


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set up file logging
    setup_logging(Path("acm_generator.log"))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()