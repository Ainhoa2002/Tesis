
import csv
import matplotlib.pyplot as plt

# File paths
system_flows = 'LCI/LCI_SYSTEM/system_ipe_flows_from_parameters.csv'
mexico_converter_flows = 'LCI/LCI_MEXICO_CONVERTER/4Q_output_control_card_ipe_flows_from_parameters.csv'
magnet_flows = 'LCI/LCI_MAGNET/magnet_ipe_flows_from_parameters.csv'
connector_system_flows = 'LCI/LCI_CONNECTION/connector_system_ipe_flows_from_parameters.csv'



# Special case for MEXICO_CONVERTER: get from MEXICO_ipe_flows_from_parameters.csv
def get_mexico_mass():
    with open('LCI/LCI_MEXICO_CONVERTER/MEXICO_ipe_flows_from_parameters.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Flow'].strip().lower() == 'mexico_converter' and row['Direction'].strip().lower() == 'output':
                return float(row['Amount'])
    raise ValueError('Output mass for MEXICO_CONVERTER not found in MEXICO_ipe_flows_from_parameters.csv')

def get_output_mass(file_path, output_name):
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Flow'].strip().lower() == output_name.strip().lower() and row['Direction'].strip().lower() == 'output':
                return float(row['Amount'])
    raise ValueError(f'Output mass for {output_name} not found in {file_path}')

# Get system input units
def get_system_inputs():
    inputs = {}
    with open(system_flows, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Direction'].strip().lower() == 'input':
                name = row['Flow'].strip().lower()
                inputs[name] = float(row['Amount'])
    return inputs

if __name__ == '__main__':
    # Get input units
    system_inputs = get_system_inputs()

    # Get mass per unit for each input
    mexico_mass = get_mexico_mass()
    magnet_mass = get_output_mass(magnet_flows, 'magnet')
    connector_mass = get_output_mass(connector_system_flows, 'connector_system')

    # Calculate totals
    total_mexico = system_inputs.get('mexico_converter', 0) * mexico_mass
    total_magnet = system_inputs.get('magnet', 0) * magnet_mass
    total_connector = system_inputs.get('connector_system', 0) * connector_mass
    total_mass = total_mexico + total_magnet + total_connector

    print('--- System Mass Visualization ---')
    print(f"MEXICO_CONVERTER: {system_inputs.get('mexico_converter', 0)} units x {mexico_mass:.6f} kg/unit = {total_mexico:.6f} kg")
    print(f"MAGNET: {system_inputs.get('magnet', 0)} units x {magnet_mass:.6f} kg/unit = {total_magnet:.6f} kg")
    print(f"CONNECTOR_SYSTEM: {system_inputs.get('connector_system', 0)} units x {connector_mass:.6f} kg/unit = {total_connector:.6f} kg")
    print(f"TOTAL SYSTEM MASS: {total_mass:.6f} kg")

    # Plotting
    labels = ['MEXICO_CONVERTER', 'MAGNET', 'CONNECTOR_SYSTEM']
    values = [total_mexico, total_magnet, total_connector]
    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, values, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    plt.ylabel('Total Mass (kg)')
    plt.title('System Mass Breakdown')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    for bar in bars:
        yval = bar.get_height()



        plt.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.2f}', va='bottom', ha='center')
    plt.tight_layout()
    plt.show()
