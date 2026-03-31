import os
import olca_schema as o
from csv_reader import read_input_rows
def create_output_flow(client, name):
    """
    Crea un flujo producto con el nombre dado, usando la propiedad
    de flujo 'Mass' y la unidad 'kg'. Devuelve el objeto Flow.
    """
    mass = client.get(o.FlowProperty, name="Mass")
    if not mass:
        raise ValueError("Flow property 'Mass' not found")
    flow = o.Flow()
    flow.name = name
    flow.flow_type = o.FlowType.PRODUCT_FLOW
    factor = o.FlowPropertyFactor()
    factor.flow_property = mass
    factor.conversion_factor = 1.0
    factor.reference_flow_property = True
    flow.flow_properties = [factor]
    unit = client.get(o.Unit, name="kg")
    if unit:
        flow.unit = unit
    client.put(flow)
    return flow

def build_process_from_inputs(client, process_name, inputs):
    """
    Crea un proceso con nombre process_name y los inputs proporcionados.
    inputs: lista de diccionarios con las claves 'UUID', 'Amount'.
    Devuelve el proceso guardado.
    """
    # Crear flujo de salida
    out_flow = create_output_flow(client, process_name)

    # Crear proceso vacío
    process = o.Process()
    process.name = process_name
    process.process_type = o.ProcessType.UNIT_PROCESS
    process.exchanges = []

    # Output de referencia (cantidad 1)
    out_ex = o.Exchange()
    out_ex.flow = out_flow
    out_ex.amount = 1.0
    out_ex.is_input = False
    process.exchanges.append(out_ex)

    # Agregar inputs
    for row in inputs:
        uuid = row.get("UUID", "").strip()
        if not uuid:
            print(f"  Skipping row without UUID: {row}")
            continue
        flow = client.get(o.Flow, uid=uuid)
        if not flow:
            print(f"  Flow with UUID {uuid} not found, skipping.")
            continue
        amount = float(row.get("Amount", 0))
        in_ex = o.Exchange()
        in_ex.flow = flow
        in_ex.amount = amount
        in_ex.is_input = True
        process.exchanges.append(in_ex)

    # Guardar proceso
    client.put(process)
    print(f"  Process '{process_name}' saved with {len(inputs)} inputs.")

    # Crear sistema producto
    config = o.LinkingConfig(
        prefer_unit_processes=True,
        provider_linking=o.ProviderLinking.PREFER_DEFAULTS
    )
    system = client.create_product_system(process, config)
    print(f"  Product system '{system.name}' created (ID: {system.id})")

    return process

def process_csv(client, csv_path):
    """
    Procesa un archivo CSV: lee los inputs, construye el proceso y sistema.
    """
    inputs = read_input_rows(csv_path)
    if not inputs:
        print(f"No inputs found in {csv_path}, skipping.")
        return

    # Obtener nombre del proceso (parte antes de '_ipe')
    base = os.path.basename(csv_path)
    process_name = base.split("_ipe")[0]
    print(f"\nProcessing {base} -> process '{process_name}'")
    build_process_from_inputs(client, process_name, inputs)