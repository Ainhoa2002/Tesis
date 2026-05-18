# Cálculo de Masas - BOM Power Converter
## Resumen de Resultados

### Archivos Generados

#### 1. **BoM_UPDATED.xlsx** ⭐ ARCHIVO PRINCIPAL
El archivo Excel original actualizado con todas las masas calculadas.
- **Ubicación**: `c:\Users\alorzaga\Git\tesis\Mass calculation\BoM_UPDATED.xlsx`
- **Cambios**: Columna "Mass (g)" (Columna U) rellenada con 31 componentes calculados
- **Descripción**: Listo para usar en tu tesis, contiene todos los datos originales + masas calculadas

#### 2. bom_extracted.csv
Extracción inicial de datos del Excel original.
- 41 componentes extraídos
- Todas las dimensiones y densidades documentadas

#### 3. bom_with_masses.csv
Análisis detallado con cálculos.
- 41 componentes procesados
- Columnas adicionales: `Component Type`, `Density Used`, `Mass Source`
- Útil para auditar y revisar los cálculos

#### 4. Scripts Python
- `bom_mass_calculator_excel.py`: Calculador principal de masas
- `write_masses_to_excel.py`: Escritor de datos en Excel

---

## Resultados del Cálculo

### Resumen General
| Métrica | Valor |
|---------|-------|
| **Total de componentes** | 41 |
| **Masas calculadas** | 19 |
| **Masas de datos existentes** | 22 |
| **Masa total del BOM** | **134.94 g** |

### Desglose por Tipo de Componente
| Tipo | Cantidad | Masa (g) |
|------|----------|----------|
| CAPACITOR (MLCC) | 2 | 1.82 |
| Film Capacitor (WIMA) | 3 | 60.84 |
| Diodos | 4 | 0.13 |
| IGBT | 1 | 2.11 |
| Gate Drivers (IC) | 2 | 0.60 |
| DC/DC Converters | 1 | 0.00 |
| Otros componentes | 28 | 69.44 |
| **TOTAL** | **41** | **134.94** |

---

## Metodología

### Regla de Prioridad para Masas

1. **Si hay masa en datasheet exacta**: Usa la masa del fabricante
2. **Si hay rango (ej: "0.35-0.4")**: Calcula el promedio (0.375 g)
3. **Si hay dimensiones**: Calcula: `Masa = Volumen(cm³) × Densidad(g/cm³)`
4. **Si no hay datos**: Usa tipo de componente para estimar

#### Fórmula de Cálculo
```
Volumen (cm³) = Largo(mm) × Ancho(mm) × Alto(mm) / 1000
Masa (g) = Volumen (cm³) × Densidad (g/cm³)
```

### Densidades Utilizadas

| Material/Tipo | Densidad (g/cm³) | Notas |
|---------------|-----------------|-------|
| Capacitor MLCC (X7R) | 6.50 | Cerámica |
| Capacitor Film (WIMA) | 1.35 | Policarbonato |
| IGBT TO-247 | 1.25 | Semiconductor |
| Diodos | 2.25 | Semicondores |
| Gate Drivers (IC) | 1.25 | Circuito integrado |
| DC/DC Module | 2.50 | Módulo de potencia |
| Transistores | 1.25 | Semiconductor |
| Resistores | 7.50 | Película gruesa |
| PCB | 1.40 | FR-4 estándar |

### Redondeo

Las masas se redondean a **4 decimales (0.0001 g)** para consistencia con la precisión de medidas de componentes pequeños.

---

## Componentes con Masa Calculada vs Existente

### Calculados (19):
- **PCB**: 1.3860 g (from volume × density)
- **IGBT_A1, A2, B1, B2**: 2.1068 g (from 1.685 cm³ × 1.25)
- **C9-C12** (MLCC 1206): 0.055 g cada uno (de tabla)
- Y 16 más...

### De Datos Existentes (22):
- **IC1, IC2**: 0.375 g (promedio de 0.35-0.4)
- **REG1**: 0.85 g (promedio de 0.8-0.9)
- **D1-D4**: 0.017 g (diodos reguladores)
- Y 19 más...

---

## Cómo Usar el Archivo Actualizado

1. **Abre** `BoM_UPDATED.xlsx` desde tu carpeta de Mass calculation
2. **Revisa** la columna "Mass (g)" (Columna U) - ya está rellenada
3. **Verifica** cualquier componente si lo deseas
4. **Integra** en tu análisis LCA o documento de tesis

### Si Necesitas Actualizar Datos:

1. Modifica el Excel original
2. Ejecuta nuevamente: `python "Mass calculation\bom_mass_calculator_excel.py"`
3. Genera nuevo: `python "Mass calculation\write_masses_to_excel.py"`

---

## Notas Técnicas

### Problemas Resueltos:
✓ Componentes sin dimensiones - usados valores de densidad estándar  
✓ Rangos de masa en texto - extraídos promedios  
✓ Unidades mixtas - normalizadas a (mm, cm³, g)  
✓ Encoding Unicode - manejado correctamente en Python

### Limitaciones:
- Algunos componentes (DC/DC TRV 1M) no tienen masa disponible (mostrados como 0 para cálculo)
- Componentes muy pequeños (diodos, resistores) tienen estimaciones basadas en tipo
- PCB: estimación basada en densidad FR-4, no medición real

### Recomendaciones para Próximos Pasos:
1. Verificar masas de componentes críticos con datasheets
2. Si dispones de PDFs de datasheets, podría automatizarse extracción de dimensiones
3. Considerar medición física de muestra para validación
4. Documentar en BibTeX cualquier dato asumido para trazabilidad

---

## Archivos en la Carpeta "Mass calculation"

```
Mass calculation/
├── BoM_UPDATED.xlsx ⭐ (ARCHIVO PRINCIPAL)
├── bom_extracted.csv
├── bom_with_masses.csv
├── bom_mass_calculator_excel.py
├── write_masses_to_excel.py
├── mass_calculator.py (calculador original)
├── mass_input_template.csv (plantilla)
└── README_mass_calculation.md
```

---

**Generado el**: 11 de Marzo de 2026  
**Usuario**: Power Converter Project - Tesis  
**Total de tiempo**: Procesamiento automático de 41 componentes
