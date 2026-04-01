import csv
import os
import olca_ipc as ipc
import olca_schema as o

# Ruta a tu CSV (cámbiala si es necesario)
CSV_PATH = r"C:\Users\alorzaga\Git\tesis\LCI_CONNECTION\LCI\4Q_output_control_card_ipe_flows_from_parameters.csv"

def diagnose():
    client = ipc.Client(8080)  # o ipc.IpC(8080)
    print("Conectado a openLCA\n")

    # 1. Verificar unidad y propiedad de flujo básicas
    print("=== Verificación de objetos base ===")
    kg = client.get(o.Unit, name="kg")
    print(f"Unidad 'kg': {kg.name if kg else 'NO ENCONTRADA'}")
    mass = client.get(o.FlowProperty, name="Mass")
    print(f"Propiedad 'Mass': {mass.name if mass else 'NO ENCONTRADA'}")
    print()

    # 2. Leer UUIDs del CSV (solo filas con Direction = Input)
    uuids = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Direction", "").strip() == "Input":
                uuid = row.get("UUID", "").strip()
                if uuid:
                    uuids.append(uuid)

    print(f"=== Analizando {len(uuids)} UUIDs ===")
    for uuid in uuids:
        # Buscar como flujo
        flow = client.get(o.Flow, uid=uuid)
        if flow:
            print(f"✅ FLOW encontrado: {flow.name} (UUID: {uuid})")
            continue
        # Buscar como proceso
        proc = client.get(o.Process, uid=uuid)
        if proc:
            print(f"⚠️ PROCESO encontrado: {proc.name} (UUID: {uuid})")
            continue
        print(f"❌ NO ENCONTRADO: UUID {uuid}")

if __name__ == "__main__":
    diagnose()