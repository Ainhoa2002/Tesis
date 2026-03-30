import os
import olca_ipc as ipc
from process_builder import process_csv

CSV_FOLDER = r"C:\Users\alorzaga\Git\tesis\LCI_CONNECTION\LCI"

def main():
    client = ipc.Client(8080)   # o ipc.ipc(8080) según tu instalación
    print("Connected to openLCA IPC server on port 8080")

    if not os.path.isdir(CSV_FOLDER):
        print(f"CSV folder not found: {CSV_FOLDER}")
        return

    for file in os.listdir(CSV_FOLDER):
        if file.endswith("_ipe_flows_from_parameters.csv"):
            full_path = os.path.join(CSV_FOLDER, file)
            print(f"\nProcessing {full_path}...")
            process_csv(client, full_path)

    print("\nAll done!")

if __name__ == "__main__":
    main()