import os
import olca_ipc as ipc
from process_builder import process_csv
CSV_FOLDER = r"C:\Users\alorzaga\Git\tesis\LCI_CONNECTION\LCI"

def main():
    client = ipc.Client(8080)   # o ipc.IpC(8080) según tu instalación
    print("Connected to openLCA IPC server")

    for file in os.listdir(CSV_FOLDER):
        if file.endswith("_ipe_flows_from_parameters.csv"):
            full_path = os.path.join(CSV_FOLDER, file)
            process_csv(client, full_path)

    print("\nAll done!")

if __name__ == "__main__":
    main()