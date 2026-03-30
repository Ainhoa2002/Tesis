import os
import olca_ipc as ipc
from process_builder import build_process_from_csv

# Ruta donde están los CSV (ajústala si es necesario)
CSV_FOLDER = r"C:\Users\alorzaga\Git\tesis\LCI_CONNECTION\LCI"

def main():
    client = ipc.Client(8080)          # o ipc.IpC(8080) según tu instalación
    print("Conectado a openLCA")

    # Procesar todos los archivos que terminen con "_ipe_flows_from_parameters.csv"
    for file in os.listdir(CSV_FOLDER):
        if file.endswith("_ipe_flows_from_parameters.csv"):
            full_path = os.path.join(CSV_FOLDER, file)
            build_process_from_csv(client, full_path)

    print("¡Proceso finalizado!")

if __name__ == "__main__":
    main()