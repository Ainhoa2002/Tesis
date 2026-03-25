import os
from olca_ipc import IpC
from .process_builder import process_csv   # relative import works because we are in the same package

# Path to the folder containing CSV files (absolute path provided by user)
CSV_FOLDER = r"C:\Users\alorzaga\Git\tesis\LCI_CONNECTION\LCI"

def main():
    # Connect to openLCA IPC server (default port 8080)
    try:
        client = IpC(8080)
        print("Connected to openLCA IPC server on port 8080")
    except Exception as e:
        print(f"Error connecting to openLCA: {e}")
        print("Make sure the IPC server is running (Tools → Developer tools → IPC Server)")
        return

    # Process every CSV file ending with '_ipe_flows_from_parameters.csv'
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