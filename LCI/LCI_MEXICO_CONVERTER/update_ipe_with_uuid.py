import csv
from pathlib import Path

def load_uuid_map(map_path):
    uuid_map = {}
    with open(map_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            flow = row['Ecoinvent_flow'].strip().strip('"')
            uuid = row['UUID'].strip()
            flow_process = row['flow/process'].strip()
            uuid_map[flow] = (uuid, flow_process)
    return uuid_map

def update_ipe_files(base_dir, uuid_map):
    for path in Path(base_dir).glob('*_ipe_flows_from_parameters.csv'):
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = list(csv.DictReader(f))
            if not reader:
                continue
            fieldnames = list(reader[0].keys())
            # Ensure UUID and flow/process columns exist after Flow
            if 'UUID' not in fieldnames or 'flow/process' not in fieldnames:
                idx = fieldnames.index('Flow') + 1
                if 'UUID' not in fieldnames:
                    fieldnames.insert(idx, 'UUID')
                if 'flow/process' not in fieldnames:
                    fieldnames.insert(idx + 1, 'flow/process')
                for row in reader:
                    row.setdefault('UUID', '')
                    row.setdefault('flow/process', '')
            updated = False
            for row in reader:
                direction = str(row.get('Direction', '')).strip().lower()
                if direction == 'output':
                    # Output summary rows intentionally have no UUID mapping.
                    continue

                flow = row['Flow'].strip().strip('"')
                if flow in uuid_map:
                    uuid, flow_process = uuid_map[flow]
                    if uuid:
                        row['UUID'] = uuid
                    else:
                        print(f"WARNING: No UUID found for flow '{flow}' in file {path.name}")
                    if flow_process:
                        row['flow/process'] = flow_process
                    updated = True
                else:
                    print(f"WARNING: No UUID found for flow '{flow}' in file {path.name}")
            if updated:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(reader)
                print(f"Updated: {path.name}")

def main():
    base_dir = Path(__file__).parent
    map_path = base_dir / 'component_library_ecoinvent_uuid_map.csv'
    uuid_map = load_uuid_map(map_path)
    update_ipe_files(base_dir, uuid_map)

if __name__ == '__main__':
    main()
