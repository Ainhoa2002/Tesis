# USAGE MANIFEST — `LCI_MEXICO_CONVERTER`

Resumen: lista los scripts principales y los archivos de datos (CSV) presentes en `LCI_MEXICO_CONVERTER`, más notas rápidas sobre su propósito. Útil para decidir qué incluir en el anexo y qué puede ser reemplazado por muestras reducidas.

Scripts clave
- `Pipeline.py` — Pipeline principal para calcular masas paramétricas y generar los `*_component_results.csv` y `*_ipe_flows_from_parameters.csv` por subsystem. Contiene utilidades de sincronización (`MEXICO_ipe_flows_from_parameters.csv`, `subsystem_units.csv`).
- `update_ipe_with_uuid.py` — Actualiza filas IPE con UUIDs desde `created_flows_uuid_map.csv` / mapeos.
- `fill_ipe_columns_from_library.py` — CLI / wrapper que alimenta `MEXICO_ipe_flows_from_parameters.csv` desde las librerías locales.
- `tools/build_component_libraries.py` — Genera/normaliza `component_library_*.csv` a partir de fuentes origen.
- `tools/add_eliminate_component.py` — Utilidad de mantenimiento para marcar/eliminar componentes.
- `tools/import_component_parameter_or_io.py` — Importa parámetros o duplica filas CSV.
- `tools/find_component.py` — Ayuda manual para localizar componentes por designator/código.
- `tools/export_to_excel.py` — Exporta tablas consolidadas a Excel para revisión/manual edits.
- `visualization/mass_visuals_app.py` — Aplicación ligera para visualizar distribuciones de masa (genera gráficos locales).

Archivos de datos (CSV) importantes presentes
- `MEXICO_ipe_flows_from_parameters.csv` — archivo agregador de flujos IPE para el sistema MEXICO.
- `*_component_results.csv` (p.ej. `4Q_output_control_card_component_results.csv`) — resultados por componente (contienen `Total_mass_kg`).
- `*_component_io_flows.csv` (p.ej. `4Q_output_control_card_component_io_flows.csv`) — filas I/O por componente.
- `*_component_parameters.csv` (p.ej. `4Q_output_control_card_component_parameters.csv`) — parámetros por componente usados por el pipeline.
- `subsystem_units.csv` — mapea subsistemas a cantidades por subsistema (usado por `Pipeline.py`).
- `all_cards_module_extraction.csv` / `all_cards_module_extraction.md` — extracción consolidada del BOM original.
- `created_flows_uuid_map.csv`, `created_process_uuid_map.csv` — mapas generados (UUIDs) por scripts de creación (si existen en ejecución previa).
- `transport_phase_legs_library.csv` / equivalents — (si aplica) mapeos para fases de transporte.

Notas y recomendaciones específicas
- Mantener en el anexo: `Pipeline.py`, `update_ipe_with_uuid.py`, `fill_ipe_columns_from_library.py`, `tools/build_component_libraries.py`, `component_parameters/io/results` CSVs esenciales para reproducir el flujo.
- Considerar reemplazar por muestras: grandes `*_component_io_flows.csv` o `*_component_results.csv` generados por procesos enteros, y en su lugar incluir versiones reducidas (ej. 1–3 filas) para mostrar formato y permitir pruebas rápidas.
- Corregir rutas absolutas: algunos scripts dentro de la carpeta referencian rutas locales (buscar `C:\Users\alorzaga` o rutas fuera del subcarpeta). Sustituir por rutas relativas o parámetros.
- Archivos generados (plots, HTML) deben eliminarse del anexo; incluir instrucciones para regenerarlos si es necesario.

Siguiente sugerencia inmediata
- Puedo: 1) extraer un `requirements.txt` aproximado desde los imports usados en esta carpeta; 2) generar versiones pequeñas (samples) de los CSVs grandes (si quieres que cree `samples/` con 1–3 filas representativas). ¿Cuál prefieres primero?

Smoke test
- `smoke_test.py` valida `Pipeline.run_pipeline` con un CSV mínimo embebido para verificar que la limpieza no rompió el cálculo local.

