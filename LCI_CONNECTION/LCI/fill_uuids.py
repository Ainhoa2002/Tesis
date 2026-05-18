def normalize_flow(flow):
    # Remove all whitespace and both types of quotes, return raw content
    import re
    return re.sub(r'\s+', '', str(flow).replace('"', '').replace("'", ''))
import csv
from pathlib import Path

def load_uuid_map(map_path):
    uuid_map = {}
    with open(map_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Robustly get the flow and UUID columns, stripping whitespace from keys
            flow = normalize_flow(row.get('Ecoinvent_flow', '').strip())
            uuid = str(row.get('UUID', '')).strip()
            if flow:
                uuid_map[flow] = uuid
    print("[DEBUG] Mapping keys:", list(uuid_map.keys()))
    return uuid_map

def fill_uuid_column(csv_path, uuid_map, flow_col='Flow', uuid_col='UUID'):
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []
    print(f"[DEBUG] Fieldnames for {csv_path.name}: {fieldnames}")
    updated = False
    for row in rows:
        flow_raw = row.get(flow_col, '')
        flow = normalize_flow(flow_raw)
        uuid = ''
        for k, v in uuid_map.items():
            if flow == normalize_flow(k):
                uuid = v
                break
        print(f"[DEBUG] Row flow_raw: '{flow_raw}', normalized: '{flow}', matched UUID: '{uuid}'")
        if not uuid:
            print(f"WARNING: No UUID found for flow '{flow_raw}' (normalized: '{flow}') in {csv_path.name}")
        row[uuid_col] = uuid  # Always fill, even if empty
        updated = True
    if updated:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

def main():
    base_dir = Path(__file__).parent
    uuid_map = load_uuid_map(base_dir / 'component_library_ecoinvent_uuid_map.csv')
    # Update all *_ipe_flows_from_parameters.csv
    for csv_path in base_dir.glob('*_ipe_flows_from_parameters.csv'):
        fill_uuid_column(csv_path, uuid_map, flow_col='Flow', uuid_col='UUID')
    # Update component_library_ecoinvent_totals.csv
    fill_uuid_column(base_dir / 'component_library_ecoinvent_totals.csv', uuid_map, flow_col='Ecoinvent_flow', uuid_col='UUID')
    print('UUID filling complete.')

if __name__ == '__main__':
    main()
