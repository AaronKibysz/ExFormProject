# ACM Generator - Análisis Comparativo de Mercado

Generador automático de Excel de Análisis Comparativo de Mercado (ACM) a partir de PDFs inmobiliarios, usando una plantilla Excel existente.

## Características

- ✅ **Extracción semántica de PDF** - Identifica patrones, no posiciones fijas
- ✅ **Plantilla Excel preservada** - Mantiene formato, fórmulas, celdas combinadas, imágenes
- ✅ **Fórmulas reales de Excel** - No valores calculados, fórmulas dinámicas
- ✅ **N comparables variables** - Soporta 1 a N propiedades comparables
- ✅ **Vista previa editable** - Verifica y corrige datos antes de generar
- ✅ **Validación robusta** - Detecta datos faltantes, inconsistencias, duplicados
- ✅ **Logging completo** - Trazabilidad del proceso

## Requisitos

- **Python 3.12+**
- **Microsoft Excel instalado** (requerido para xlwings/COM automation)
- Windows 10/11

## Instalación

```bash
# Clonar o navegar al proyecto
cd ExFormProject-Cli

# Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

### 1. Ejecutar la aplicación

```bash
python main.py
```

### 2. Flujo de trabajo

1. **Seleccionar PDF** - Botón "Seleccionar PDF", elige el archivo con propiedades comparables
2. **Seleccionar Plantilla Excel** - Botón "Seleccionar Excel", elige tu archivo plantilla ACM
3. **N° Comparables** - Ingresa cuántas propiedades comparables tiene el PDF (ej: 4)
4. **Precio a usar** - Selecciona "Precio de Venta" o "Precio de Publicación"
5. **Analizar PDF** - Click en "Analizar PDF", espera la extracción
6. **Vista Previa** - Se abre ventana con tabla editable. Verifica/corrige datos
7. **Confirmar** - Click "Confirmar y Generar"
8. **Guardar** - Elige dónde guardar el archivo generado (sufijo `_GENERADO`)

### 3. Resultado

Se crea una **copia** de la plantilla con nombre `NOMBRE_GENERADO.xlsx` con:
- Datos de propiedades en hoja "PASO 1" (columnas C, D, E...)
- Fórmulas de homogeneización, valor unitario, ponderación, promedio
- Formato, estilos, celdas combinadas, imágenes **idénticos a la plantilla**
- Archivo original **intacto**

## Estructura del Proyecto

```
ExFormProject-Cli/
├── main.py                 # Punto de entrada
├── requirements.txt        # Dependencias
├── README.md              # Este archivo
├── AGENTS.md              # Especificación técnica
├── MEMORY.md              # Contexto del proyecto
├── app/
│   ├── __init__.py
│   ├── models/            # Modelos de datos (ComparableProperty, etc.)
│   ├── pdf_parser/        # Extracción PDF (PyMuPDF + regex semánticos)
│   ├── excel/             # Escritura Excel (xlwings/COM)
│   ├── services/          # Orquestación (ACMService)
│   ├── ui/                # Interfaz PySide6
│   ├── validation/        # Reglas de validación
│   └── utils/             # Utilidades (normalización, logging)
└── tests/                 # Tests (pendientes)
```

## Plantilla Excel Esperada

La aplicación espera una plantilla con hoja **"PASO 1"** con esta estructura (filas aproximadas):

| Fila | Campo | Col C | Col D | Col E | Col F | Col G |
|------|-------|-------|-------|-------|-------|-------|
| 116 | Encabezado | A ANALIZAR | COMP 1 | COMP 2 | COMP 3 | COMP 4 |
| 117 | Precio Dolares | | | | | |
| 118 | Dirección | | | | | |
| 119 | Tipo de Propiedad | | | | | |
| 120 | Estado Captación | | | | | |
| 121 | Sup. Cubierta (m2) | | | | | |
| 122 | Sup. Total (m2) | | | | | |
| 123 | Año Construcción | | | | | |
| 124 | Cocina | | | | | |
| 125 | Comedor | | | | | |
| 126 | Dormitorios | | | | | |
| 127 | Baños | | | | | |
| 128 | Cochera | | | | | |

**Fórmulas que se generan/actualizan dinámicamente:**
- Sup. Homog. (fila 181): `=D121+(D122-D121)/4` por cada comparable
- Valor Unitario (fila 188): `=D117/D181` por cada comparable
- Ponderación (filas 197-200): Ubicación × Categoría × Servicios
- Valor Unitario Resultante (fila 201): Valor Unitario × Ponderación
- Promedio (fila 206): `=AVERAGE(D201:G201)` **rango dinámico según N**
- Valor Propiedad (fila 214): Sup. Homog. Propiedad × Promedio

## Campos extraídos del PDF

El parser busca estos patrones (con variaciones de mayúsculas, acentos, dos puntos):

- **Precios**: "Precio de publicación", "Precio de venta" (U$S, USD, $)
- **Dirección**: "Dirección", "Ubicación", "Domicilio"
- **Superficies**: "Superficie total/cubierta/semicubierta/terreno" (m²)
- **Ambientes**: "Ambientes", "Habitaciones"
- **Dormitorios/Baños/Cochera**: "Dormitorios", "Baños", "Cochera/Garage"
- **Antigüedad/Año**: "Antigüedad", "Año de construcción"
- **Días en mercado**: "Días en mercado", "Días publicado"
- **Estados**: "Cerrada", "Abierta", "Pendiente"
- **Booleanos**: "Apto crédito", "Ofrece financiamiento", "Apto profesional"

## Normalización de números

Maneja automáticamente:
- `160`, `160.00`, `160,00` → `160.0`
- `239.38`, `239,38` → `239.38`
- `U$S 73,000`, `USD 73000`, `$73000` → `73000.0`

## Reglas Importantes

⚠️ **NO se inventan datos**: Si un campo no está en el PDF → queda vacío + warning  
⚠️ **NO se sobrescribe la plantilla**: Siempre se crea copia `_GENERADO.xlsx`  
⚠️ **NO se convierten fórmulas a valores**: Las fórmulas se mantienen como fórmulas  
⚠️ **El divisor 4 en homogeneización es constante**: NO cambia con N comparables  

## Solución de Problemas

### "El PDF parece estar escaneado"
El PDF no tiene texto seleccionable. La versión actual no incluye OCR. Convierte el PDF a texto o usa uno con capa de texto.

### Error "xlwings: Could not start Excel"
- Verifica que Microsoft Excel esté instalado y activado
- Intenta abrir Excel manualmente primero
- Ejecuta como administrador si hay problemas de permisos COM

### Fórmulas no se actualizan
- Abre el archivo generado en Excel
- Presiona `F9` o `Ctrl+Alt+F9` para forzar recálculo
- Verifica que las celdas origen tengan datos numéricos

### Columnas extra en plantilla
Si tu plantilla tiene más de 4 comparables (columnas D-G), la app detecta automáticamente cuántas hay y limpia las sobrantes.

## Logging

Los logs se guardan en `acm_generator.log` y se muestran en la interfaz:
- `INFO` - Pasos normales
- `WARNING` - Datos faltantes, inconsistencias menores
- `ERROR` - Fallos que impiden continuar

## Desarrollo

```bash
# Ejecutar tests (cuando existan)
pytest tests/

# Formatear código
black app/ tests/

# Linting
ruff check app/
```

## Licencia

Proyecto interno - Uso restringido al equipo de desarrollo.

---

**Versión**: 1.0.0  
**Autor**: Equipo de Desarrollo ACM Generator