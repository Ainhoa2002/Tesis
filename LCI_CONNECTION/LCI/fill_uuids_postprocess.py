import csv
from pathlib import Path

# Load UUID mapping from component_library_ecoinvent_uuid_map.csv
def load_uuid_map(map_path):
    uuid_map = {}
    with open(map_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            flow = str(row['Ecoinvent_flow']).strip().strip('"')
            flow = flow.replace('\u202c', '').replace('\u202a', '').replace('\u200e', '').replace('\u200f', '').strip()
            uuid = str(row['UUID']).strip()
            uuid_map[flow] = uuid
    return uuid_map

# Fill UUID column in a CSV file given a flow column name
def fill_uuid_column(csv_path, uuid_map, flow_col='Flow', uuid_col='UUID'):
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
        fieldnames = rows[0].keys() if rows else []
    updated = False
    for row in rows:
        flow = str(row.get(flow_col, '')).strip().strip('"')
        flow = flow.replace('\u202c', '').replace('\u202a', '').replace('\u200e', '').replace('\u200f', '').strip()
        uuid = uuid_map.get(flow, '')
        if row.get(uuid_col, '') != uuid:
            row[uuid_col] = uuid
            updated = True
    if updated:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Updated: {csv_path}")

# Main routine
def main():
    base_dir = Path(__file__).parent
    uuid_map = load_uuid_map(base_dir / 'component_library_ecoinvent_uuid_map.csv')
    # Update all *_ipe_flows_from_parameters.csv
    for csv_path in base_dir.glob('*_ipe_flows_from_parameters.csv'):
        fill_uuid_column(csv_path, uuid_map, flow_col='Flow', uuid_col='UUID')
    # Update component_library_ecoinvent_totals.csv
    fill_uuid_column(base_dir / 'component_library_ecoinvent_totals.csv', uuid_map, flow_col='Ecoinvent_flow', uuid_col='UUID')

if __name__ == '__main__':
    main()
