import os
import olca_schema as o
from csv_reader import read_input_rows

def build_process_from_inputs(client, process_name, inputs, category_name):
    # Create a unit process and attach it to the system category.
    process = o.Process()
    process.name = process_name
    process.process_type = o.ProcessType.UNIT_PROCESS
    process.exchanges = []
    # In this olca_schema version, process.category is a category path string.
    process.category = category_name

    input_count = 0
    for row in inputs:
        # UUID is required to resolve each input flow from openLCA.
        uuid = row.get("UUID", "").strip()
        if not uuid:
            continue
        flow = client.get(o.Flow, uid=uuid)
        if not flow:
            print(f"  Flow with UUID {uuid} not found, skipping.")
            continue
        try:
            # Amount must be numeric to create a valid exchange.
            amount = float(row.get("Amount", 0))
        except (ValueError, TypeError):
            print(f"  Invalid amount '{row.get('Amount')}' for UUID {uuid}, skipping.")
            continue
        # Build one input exchange for each valid CSV row.
        in_ex = o.Exchange()
        in_ex.flow = flow
        in_ex.amount = amount
        in_ex.is_input = True
        process.exchanges.append(in_ex)
        input_count += 1

    # Skip process creation when no valid input exchanges were built.
    if input_count == 0:
        print("  No valid inputs found, skipping process creation.")
        return

    try:
        client.put(process)
        print(f"  Process '{process_name}' saved with {input_count} inputs.")
    except Exception as e:
        print(f"  Failed to save process: {e}")
        return

    # Quick read-back check to confirm persistence in openLCA.
    fetched = client.get(o.Process, name=process_name)
    if fetched:
        print(f"  Verified: process '{fetched.name}' (ID: {fetched.id})")
    else:
        print(f"  Warning: process '{process_name}' not found after saving.")

    return process

def process_csv(client, csv_path, category_name):
    # Reader already filters rows to Direction == Input.
    inputs = read_input_rows(csv_path)
    if not inputs:
        print(f"No inputs found in {csv_path}, skipping.")
        return

    base = os.path.basename(csv_path)
    process_name = base.split("_ipe")[0]
    print(f"\nProcessing {base} -> process '{process_name}' in category '{category_name}'")
    build_process_from_inputs(client, process_name, inputs, category_name)