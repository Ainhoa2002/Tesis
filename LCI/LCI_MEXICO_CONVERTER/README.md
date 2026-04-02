# LCI_MEXICO_CONVERTER Workflow

Este README describe la logica actual dentro de esta carpeta.

## Quick Start

Ejecuta desde la carpeta del repositorio:

1. Editar o agregar componentes (opcional):

```powershell
python .\LCI\LCI_MEXICO_CONVERTER\add_eliminate_component.py
```

2. Ejecutar pipeline para generar resultados y flujos:

```powershell
python .\LCI\LCI_MEXICO_CONVERTER\Pipeline.py
```

Tambien puedes pasar subsistemas por CLI:

```powershell
python .\LCI\LCI_MEXICO_CONVERTER\Pipeline.py all
python .\LCI\LCI_MEXICO_CONVERTER\Pipeline.py fuse_card inverter_power_card
```

3. Exportar a Excel (opcional):

```powershell
python .\LCI\LCI_MEXICO_CONVERTER\export_to_excel.py
```

## Entradas y Salidas por Subsystem

Entrada principal por subsistema:

- `<subsystem>_component_parameters.csv`

Salidas principales por subsistema:

- `<subsystem>_component_results.csv`
- `<subsystem>_component_io_flows.csv`
- `<subsystem>_ipe_flows_from_parameters.csv`

## Nueva Logica de Masa Total por Subsystem

En `Pipeline.py` existe la funcion reutilizable:

- `calculate_subsystem_total_mass(results_csv_path)`

Esta funcion:

- lee `<subsystem>_component_results.csv`
- suma `Total_mass_kg`
- devuelve la masa total del subsistema en kg

Uso actual de esta funcion (2 lugares):

1. Resumen global del pipeline (`total_mass` acumulado)
2. Fila adicional en `<subsystem>_ipe_flows_from_parameters.csv`

## Fila Adicional en _ipe_flows_from_parameters.csv

Al terminar cada subsistema, se agrega una fila con esta estructura:

- `Flow`: nombre del subsystem (ejemplo: `control_backplane_card`)
- `UUID`: vacio
- `Unit`: `kg`
- `Amount`: masa total del subsystem (calculada por `calculate_subsystem_total_mass`)
- `Direction`: `Output`

Objetivo: exponer la masa total del subsistema directamente en el archivo IPE.

## Reglas de Warnings para filas Output

Las filas con `Direction=Output` (como la fila de masa total) ahora se tratan como filas intencionales y no como faltantes de mapeo:

- `fill_ipe_columns_from_library.py` no intenta rellenarlas ni reportarlas como "could not be filled".
- `update_ipe_with_uuid.py` no intenta mapear UUID para esas filas ni imprime warning por UUID faltante.

## Validaciones Principales en Pipeline

- `Section` y `Ecoinvent_flow` son obligatorios.
- Si falta alguno en una fila, ese subsistema falla validacion.
- El resto de subsistemas seleccionados continua.
- **IMPORTANTE (MASA)**: Solo unidad `kg` es aceptada para contexto de masa. Cualquier fila con `unit='g'` sera rechazada con error explicito listando las filas problematicas. Todas las masas deben ingresar en kg, sin excepciones.

## Variables de Entorno Utiles

- `MASS_CALC_AUTO_SYNC_FROM_LIBRARY`
  - `1`: habilita sync automatico de parametros desde librerias al inicio.
  - `0` (default): deshabilitado.

- `MASS_CALC_AUTO_REFRESH_LIBRARIES`
  - controla el refresh automatico de librerias al finalizar pipeline.

- `MASS_CALC_CLEAR_OUTPUTS_ON_FAILURE`
  - `1`: borra salidas del subsistema que fallo validacion.
  - `0` (default): conserva salidas previas.

## Librerias y utilidades relacionadas

- `build_component_libraries.py`: recompone librerias consolidadas.
- `fill_ipe_columns_from_library.py`: rellena columnas IPE desde libreria.
- `update_ipe_with_uuid.py`: completa UUID/flow-process desde mapa.
- `find_component.py`: busqueda/edicion de componentes.
- `mass_visuals_app.py`: visualizacion de masa basada en `Total_mass_kg`.

## Nota de integracion con openLCA

Los `*_ipe_flows_from_parameters.csv` son la base para la importacion posterior hacia openLCA en el flujo de este proyecto.

