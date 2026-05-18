import olca_ipc as ipc
import olca_schema as o

# ------------------------------------------------------------
# Configuración de prueba (cambia según lo que quieras probar)
# ------------------------------------------------------------
# Ejemplo: usar el proceso de electric connector que ya sabes que funciona
TEST_PROCESS_UUID = "dd86962a-dd7e-316b-9ae3-bb22cf1fcbc2"   # proceso unitario
# Para probar un par pre-input/pre-process, descomenta estas:
# UUID_PRE_INPUT = "40dc9f2f-40c2-37b4-8f38-53d043a5f756"
# UUID_PRE_PROCESS = "b620b979-8e06-3778-9e5f-9d5de2dc3d74"
# AMOUNT = 0.016
# UNIT = "kg"

# ------------------------------------------------------------
# Funciones auxiliares con prints de depuración
# ------------------------------------------------------------
def debug_print(title, obj, indent=0):
    """Imprime información de un objeto."""
    prefix = "  " * indent
    print(f"{prefix}--- {title} ---")
    if obj is None:
        print(f"{prefix}None")
        return
    if hasattr(obj, '__dict__'):
        # Mostrar atributos relevantes
        attrs = [k for k in obj.__dict__.keys() if not k.startswith('_')]
        print(f"{prefix}Atributos: {attrs}")
        # Para exchanges, mostrar detalles
        if hasattr(obj, 'exchanges') and obj.exchanges:
            print(f"{prefix}Número de exchanges: {len(obj.exchanges)}")
            for idx, ex in enumerate(obj.exchanges[:3]):  # primeros 3
                print(f"{prefix}  Exchange {idx}:")
                print(f"{prefix}    flow: {ex.flow.name if ex.flow else None}")
                print(f"{prefix}    amount: {ex.amount}")
                print(f"{prefix}    is_input: {ex.is_input}")
                print(f"{prefix}    quantitative_reference: {ex.quantitative_reference}")
        elif hasattr(obj, 'name'):
            print(f"{prefix}name: {obj.name}")
            if hasattr(obj, 'id'):
                print(f"{prefix}id: {obj.id}")

def get_flow_from_process_uuid_debug(client, uuid):
    print(f"\n🔍 Obteniendo proceso con UUID: {uuid}")
    proc = client.get(o.Process, uid=uuid)
    if proc is None:
        raise ValueError(f"❌ Proceso con UUID {uuid} no encontrado")
    debug_print("Proceso obtenido", proc)

    # Buscar el exchange de referencia
    ref_flow = None
    for exch in proc.exchanges:
        if exch.quantitative_reference:
            ref_flow = exch.flow
            print(f"✅ Encontrado exchange de referencia con flujo: {ref_flow.name}")
            break
    if ref_flow is None:
        raise ValueError(f"❌ El proceso '{proc.name}' no tiene exchange de referencia")
    return ref_flow

def get_flow_by_uuid_debug(client, uuid):
    print(f"\n🔍 Obteniendo flujo con UUID: {uuid}")
    flow = client.get(o.Flow, uid=uuid)
    if flow is None:
        raise ValueError(f"❌ Flujo con UUID {uuid} no encontrado")
    debug_print("Flujo obtenido", flow)
    return flow

def get_flow_from_row_debug(client, uuid, entity_type):
    print(f"\n📌 Buscando flujo para UUID={uuid}, tipo={entity_type}")
    if entity_type == 'unit process':
        return get_flow_from_process_uuid_debug(client, uuid)
    elif entity_type == 'flow':
        return get_flow_by_uuid_debug(client, uuid)
    else:
        raise ValueError(f"Tipo desconocido: {entity_type}")

def create_product_flow_debug(client, name, unit_name):
    print(f"\n🆕 Creando flujo producto: {name} con unidad {unit_name}")
    unit = client.get(o.Unit, name=unit_name)
    if unit is None:
        raise ValueError(f"Unidad '{unit_name}' no encontrada")
    prop = client.get(o.FlowProperty, name="Mass")
    if prop is None:
        raise ValueError("Flow property 'Mass' no encontrada")
    flow = o.new_product(name, prop, unit)
    client.put(flow)
    print(f"✅ Flujo creado con ID: {flow.id}")
    return flow

def create_intermediate_process_debug(client, input_flow, output_flow, amount):
    print(f"\n🏭 Creando proceso intermedio:")
    print(f"   Input: {input_flow.name} (amount={amount})")
    print(f"   Output: {output_flow.name} (amount={amount})")
    proc_name = f"Production of {output_flow.name} from {input_flow.name}"
    proc_category = ["Intermediate processes"]
    location = client.get(o.Location, name="GLO")
    print(f"   Ubicación: {location.name if location else None}")

    process = o.new_process(proc_name)
    process.category = proc_category
    process.default_flow = output_flow
    process.default_flow_amount = amount
    process.location = location

    out = o.new_output(process, output_flow, amount)
    out.is_quantitative_reference = True
    o.new_input(process, input_flow, amount)

    client.put(process)
    print(f"✅ Proceso intermedio guardado: {proc_name} (ID: {process.id})")
    return process, output_flow

# ------------------------------------------------------------
# Prueba 1: Obtener un proceso y su flujo de referencia
# ------------------------------------------------------------
def test_single_process():
    print("\n" + "="*50)
    print("PRUEBA 1: Obtener flujo de referencia de un proceso")
    print("="*50)
    client = ipc.Client(8080)
    print("Conectado a openLCA")

    try:
        flow = get_flow_from_process_uuid_debug(client, TEST_PROCESS_UUID)
        print(f"\n✅ Flujo de referencia obtenido: {flow.name} (ID: {flow.id})")
    except Exception as e:
        print(f"\n❌ Error: {e}")

# ------------------------------------------------------------
# Prueba 2: Crear un proceso intermedio con un par pre-input/pre-process
# ------------------------------------------------------------
def test_intermediate_pair():
    print("\n" + "="*50)
    print("PRUEBA 2: Crear proceso intermedio con par pre-input/pre-process")
    print("="*50)
    client = ipc.Client(8080)
    print("Conectado a openLCA")

    # Ajusta estos valores con los de tu CSV
    uuid_input = "40dc9f2f-40c2-37b4-8f38-53d043a5f756"   # market for copper, cathode
    uuid_output = "b620b979-8e06-3778-9e5f-9d5de2dc3d74"  # market for zinc, primary
    entity_type = "unit process"
    amount = 0.016
    unit = "kg"

    try:
        input_flow = get_flow_from_row_debug(client, uuid_input, entity_type)
        output_flow = get_flow_from_row_debug(client, uuid_output, entity_type)

        combined_name = f"{output_flow.name} + {input_flow.name}"
        combined_flow = create_product_flow_debug(client, combined_name, unit)

        inter_proc, _ = create_intermediate_process_debug(client, input_flow, combined_flow, amount)
        print("\n✅ Prueba completada. Revisa openLCA para ver el proceso intermedio.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

# ------------------------------------------------------------
# Ejecutar pruebas
# ------------------------------------------------------------
if __name__ == "__main__":
    test_single_process()   # Prueba con un proceso que sabes que funciona
    # test_intermediate_pair()  # Descomenta cuando la primera prueba funcione