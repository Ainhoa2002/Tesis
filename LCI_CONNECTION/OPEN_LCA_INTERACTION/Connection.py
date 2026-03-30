
import olca_schema as schema
import olca_ipc as ipc
client = ipc.Client(8080)    

# 1. Obtener el flujo de ecoinvent que quieres usar como entrada
flow_name = "2,4-Dimethylphenol"
input_flow = client.find(schema.Flow, flow_name)
if input_flow is None:
    print(f"Flujo '{flow_name}' no encontrado.")
    exit(1)
print(f"Flujo encontrado: {input_flow.name} (ID: {input_flow.id})")



# Buscar unidad kg
kg = client.find(Unit, "kg")
print("Unidad kg encontrada" if kg else "No se encontró kg")

# Crear flujo de prueba
new_flow = client.insert(
    Flow,
    name="Mi flujo de prueba",
    flow_type="PRODUCT_FLOW",
    unit=kg
)
print(f"Flujo creado: {new_flow.name} (ID: {new_flow.id})")

# Buscar ubicación GLO
loc = client.find(Location, "GLO")
print("Ubicación GLO encontrada" if loc else "No se encontró GLO")

# Crear proceso de prueba
new_process = client.insert(
    Process,
    name="Mi proceso de prueba",
    category=["Pruebas"],
    default_flow=new_flow,
    default_flow_amount=1.0,
    location=loc,
    exchanges=[
        {
            "flow": new_flow,
            "amount": 1.0,
            "is_input": False,
            "quantitative_reference": True
        }
    ]
)
print(f"Proceso creado: {new_process.name} (ID: {new_process.id})")





