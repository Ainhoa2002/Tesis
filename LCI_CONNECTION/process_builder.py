import os
import olca_schema as o
from csv_reader import read_input_rows

def build_process_from_inputs(client, process_name, inputs):
    """
    Create a process with the given inputs. No output flow is created.
    """
    process = o.Process()
    process.name = process_name
    process.process_type = o.ProcessType.UNIT_PROCESS
    process.exchanges = []

    input_count = 0
    for row in inputs:
        uuid = row.get("UUID", "").strip()
        if not uuid:
            continue
        flow = client.get(o.Flow, uid=uuid)
        if not flow:
            print(f"  Flow with UUID {uuid} not found, skipping.")
            continue
        try:
            amount = float(row.get("Amount", 0))
        except (ValueError, TypeError):
            print(f"  Invalid amount '{row.get('Amount')}' for UUID {uuid}, skipping.")
            continue
        in_ex = o.Exchange()
        in_ex.flow = flow
        in_ex.amount = amount
        in_ex.is_input = True
        process.exchanges.append(in_ex)
        input_count += 1

    if input_count == 0:
        print("  No valid inputs found, skipping process creation.")
        return

    client.put(process)
    print(f"  Process '{process_name}' saved with {input_count} inputs.")
    return process

def process_csv(client, csv_path):
    inputs = read_input_rows(csv_path)
    if not inputs:
        print(f"No inputs found in {csv_path}, skipping.")
        return

    base = os.path.basename(csv_path)
    process_name = base.split("_ipe")[0]
    print(f"\nProcessing {base} -> process '{process_name}'")
    build_process_from_inputs(client, process_name, inputs)