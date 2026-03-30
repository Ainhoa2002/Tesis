import os
import olca_schema as o
from csv_reader import read_inputs

# ------------------------------------------------------------------
# 1. Obtener nombre del proceso a partir del nombre del archivo
# ------------------------------------------------------------------
def get_process_name(path):
    """Extrae el nombre base (antes de '_ipe...') del archivo."""
    filename = os.path.basename(path)
    # Elimina todo desde "_ipe" en adelante (incluyendo la extensión)
    return filename.split("_ipe")[0]

# ------------------------------------------------------------------
# 2. Obtener el flujo a partir de una fila del CSV
# ------------------------------------------------------------------
def get_flow(client, row):
    """
    Devuelve un objeto Flow (producto o flujo elemental) según:
    - Si row['flow/process'] == 'flow' → buscar directamente por UUID.
    - Si row['flow/process'] == 'unit process' → obtener el proceso y extraer su primer output.
    """
    uid = row.get("UUID", "").strip()
    if not uid or uid.lower() == "nan":
        print(f"  Advertencia: UUID vacío para '{row.get('Flow', '')}'")
        return None

    entity_type = row.get("flow/process", "").strip().lower()

    if entity_type == "flow":
        flow = client.get(o.Flow, uid=uid)
        if flow is None:
            print(f"  Flujo con UUID {uid} no encontrado")
        return flow

    if entity_type == "unit process":
        proc = client.get(o.Process, uid=uid)
        if proc is None:
            print(f"  Proceso con UUID {uid} no encontrado")
            return None
        # Buscar el primer exchange que sea output (is_input=False)
        for exch in proc.exchanges:
            if not exch.is_input:
                return exch.flow
        print(f"  El proceso '{proc.name}' no tiene output")
        return None

    print(f"  Tipo de entidad desconocido: {entity_type}")
    return None

# ------------------------------------------------------------------
# 3. Crear un flujo producto (para el output del proceso)
# ------------------------------------------------------------------
def create_product_flow(client, name):
    """
    Crea un flujo producto con el nombre dado.
    Se asume que la propiedad de flujo 'Mass' y la unidad 'kg' existen.
    """
    mass_prop = client.get(o.FlowProperty, name="Mass")
    if mass_prop is None:
        raise ValueError("Propiedad de flujo 'Mass' no encontrada en la base")

    # Crear un nuevo flujo producto
    flow = o.Flow()
    flow.name = name
    flow.flow_type = o.FlowType.PRODUCT_FLOW

    # Crear el factor de propiedad (necesario para la unidad)
    factor = o.FlowPropertyFactor()
    factor.flow_property = mass_prop
    factor.conversion_factor = 1.0
    factor.reference_flow_property = True

    flow.flow_properties = [factor]

    # Asignar la unidad por defecto (kg)
    kg_unit = client.get(o.Unit, name="kg")
    if kg_unit is None:
        raise ValueError("Unidad 'kg' no encontrada")
    flow.unit = kg_unit

    client.put(flow)
    return flow

# ------------------------------------------------------------------
# 4. Crear un proceso vacío (solo estructura)
# ------------------------------------------------------------------
def new_process(name):
    process = o.Process()
    process.name = name
    process.process_type = o.ProcessType.UNIT_PROCESS
    process.exchanges = []
    return process

# ------------------------------------------------------------------
# 5. Añadir el exchange de referencia (output)
# ------------------------------------------------------------------
def add_reference_output(process, flow):
    ex = o.Exchange()
    ex.flow = flow
    ex.amount = 1.0
    ex.is_input = False
    ex.quantitative_reference = True   # si tu versión no lo soporta, ignora
    process.exchanges.append(ex)

# ------------------------------------------------------------------
# 6. Añadir un exchange de input
# ------------------------------------------------------------------
def add_input(process, flow, amount):
    ex = o.Exchange()
    ex.flow = flow
    ex.amount = float(amount)
    ex.is_input = True
    process.exchanges.append(ex)

# ------------------------------------------------------------------
# 7. Función principal: construir proceso y sistema a partir del CSV
# ------------------------------------------------------------------
def build_process_from_csv(client, csv_path):
    print(f"Procesando: {csv_path}")

    # 1. Obtener nombre del proceso
    process_name = get_process_name(csv_path)

    # 2. Leer solo las filas con Direction=Input
    rows = read_inputs(csv_path)
    if not rows:
        print("  No se encontraron inputs en el CSV")
        return

    # 3. Crear el flujo de referencia (output)
    ref_flow = create_product_flow(client, process_name)

    # 4. Crear proceso vacío
    process = new_process(process_name)

    # 5. Añadir output de referencia
    add_reference_output(process, ref_flow)

    # 6. Añadir todos los inputs
    for row in rows:
        flow = get_flow(client, row)
        if flow is None:
            continue
        amount = row.get("Amount", "0").strip()
        try:
            amount = float(amount)
        except:
            amount = 0.0
        add_input(process, flow, amount)

    # 7. Guardar proceso
    client.put(process)
    print(f"  Proceso guardado: {process_name}")

    # 8. Crear sistema producto
    config = o.LinkingConfig(
        prefer_unit_processes=True,
        provider_linking=o.ProviderLinking.PREFER_DEFAULTS
    )
    system = client.create_product_system(process, config)
    print(f"  Sistema producto creado: {system.name} (ID: {system.id})")