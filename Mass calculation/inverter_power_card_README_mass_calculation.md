# Parametric Mass + Ecoinvent Workflow

Este flujo usa una tabla compacta para que solo edites datos de entrada reales por componente.
Las columnas de clasificacion y orden se calculan automaticamente dentro del pipeline.

## Archivos principales

- `inverter_power_card_seed_parameters_from_excel.py`
  - Genera la tabla base desde `BoM.xlsx` con el esquema reducido (NECESARIO PORQUE LOS DATOS ESTABAN ALMACENADOS EN EXCEL)

- `inverter_power_card_component_parameters.csv`
  - Archivo principal editable por el usuario.

- `add_eliminate_component.py`
  - Flujo interactivo para agregar, actualizar o eliminar componentes en el CSV.

- `inverter_power_card_run_mass_ecoinvent_pipeline.py`
  - Calcula masa cuando hace falta.
  - Genera salidas por componente y flujos agrupados.

## Flujo rapido

1. Seed inicial (una vez o cuando quieras regenerar base):

`python "Mass calculation\\inverter_power_card_seed_parameters_from_excel.py"`

2. Edicion de componentes:

`python "Mass calculation\\add_eliminate_component.py"`

o edicion directa de:

`inverter_power_card_component_parameters.csv`

3. Pipeline:

`python "Mass calculation\\inverter_power_card_run_mass_ecoinvent_pipeline.py"`

## Esquema de entrada (CSV editable)

Columnas esperadas:

- `Designators`
- `Manufacturer`
- `Part_Number`
- `Description`
- `number_elements`
- `unit`
- `Quantity_per_element`
- `Has_datasheet_info`
- `L_mm`
- `W_mm`
- `H_mm`
- `Volume_cm3_excel`
- `Density_min_g_cm3`
- `Density_max_g_cm3`
- `Metal_extra_g`
- `Other_extra_g`
- `Database`
- `Database_component_title`
- `Ecoinvent_flow`
- `Ecoinvent_unit`
- `Direction`
- `Ecoinvent_amount_override`
- `Comments`
- `Notes`

## Campos calculados automaticamente por el pipeline

Aunque no esten en el CSV de entrada, el pipeline calcula y agrega en salidas:

- `Order_index`
- `Category_order`
- `Group_order`
- `Category`
- `Section`
- `Subsection`
- `Total_quantity`

Regla:

- Si `Category`, `Section`, `Subsection` no existen o estan vacios, se usa `Category = AUTO` y los demas vacios.
- `Order_index` se basa en el orden de filas del CSV.

## Logica de masa

Solo se exige masa para flujos con unidad `kg` o `g`.

Si `Ecoinvent_unit` es `kg` o `g`, la masa se resuelve asi:

1. `DATASHEET_QTY_KG`
  - Si `Has_datasheet_info=YES` y `Quantity_per_element` tiene valor, se interpreta como kg por elemento.

2. `CALCULATED` o `CALCULATED_FALLBACK`
  - Geometria + densidad:
  - `Volume_cm3 = (L_mm * W_mm * H_mm) / 1000`
  - Si faltan dimensiones, usa `Volume_cm3_excel`.
  - Densidad efectiva:
  1. promedio de `Density_min_g_cm3` y `Density_max_g_cm3`
  2. `Density_min_g_cm3`
  3. `Density_max_g_cm3`
  - `Mass_per_element_g = Volume_cm3 * Density + Metal_extra_g + Other_extra_g`

Si no se puede calcular masa para unidad `kg/g`, queda `MISSING_MASS`.

## Logica de amount para ecoinvent

- Unidad `kg/g`: usa masa calculada.
- Otras unidades: usa `Ecoinvent_amount_override`.

## Salidas

- `inverter_power_card_component_mass_results.csv`
  - Detalle completo por componente.

- `inverter_power_card_component_io_flows.csv`
  - Flujos por componente con `Amount`, base de formula y validaciones.

- `inverter_power_card_ipe_flows_from_parameters.csv`
  - Flujos agrupados por `(Flow, Unit, Direction)`.
