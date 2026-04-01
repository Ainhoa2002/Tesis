import os
import olca_schema as o
from csv_reader import read_input_rows, read_output_rows


def _get_entity_by_name(client, model_type, name):
    ref = client.find(model_type, name=name)
    if not ref:
        return None
    return client.get(model_type, uid=ref.id)


def _get_number_flow_property(client):
    for prop_name in ("Number", "Piece", "Item"):
        prop = _get_entity_by_name(client, o.FlowProperty, prop_name)
        if prop:
            return prop
    return None


def _get_mass_flow_property(client):
    return _get_entity_by_name(client, o.FlowProperty, "Mass")


def _find_or_create_output_flow(client, flow_name, mass_per_lu):
    existing_ref = client.find(o.Flow, name=flow_name)
    if existing_ref:
        flow = client.get(o.Flow, uid=existing_ref.id)
        if flow:
            return flow

    number_prop = _get_number_flow_property(client)
    mass_prop = _get_mass_flow_property(client)

    if not number_prop:
        raise ValueError("Flow property 'Number' (or equivalent) not found")
    if not mass_prop:
        raise ValueError("Flow property 'Mass' not found")

    flow = o.Flow()
    flow.name = flow_name
    flow.flow_type = o.FlowType.PRODUCT_FLOW

    factor_number = o.FlowPropertyFactor()
    factor_number.flow_property = number_prop
    factor_number.conversion_factor = 1.0
    factor_number.is_ref_flow_property = True

    factor_mass = o.FlowPropertyFactor()
    factor_mass.flow_property = mass_prop
    factor_mass.conversion_factor = mass_per_lu
    factor_mass.is_ref_flow_property = False

    flow.flow_properties = [factor_number, factor_mass]

    client.put(flow)
    created_ref = client.find(o.Flow, name=flow_name)
    if not created_ref:
        raise ValueError(f"Flow '{flow_name}' could not be created")
    created_flow = client.get(o.Flow, uid=created_ref.id)
    if not created_flow:
        raise ValueError(f"Flow '{flow_name}' could not be retrieved after creation")
    return created_flow

def build_process_from_inputs(client, process_name, inputs, category_name, output_rows=None):
    # Create a unit process and attach it to the system category.
    process = o.Process()
    process.name = process_name
    process.process_type = o.ProcessType.UNIT_PROCESS
    process.exchanges = []
    # In this olca_schema version, process.category is a category path string.
    process.category = category_name

    output_created = False
    for output_row in (output_rows or []):
        output_name = str(output_row.get("Flow", "")).strip()
        uuid = str(output_row.get("UUID", "")).strip()
        try:
            output_amount = float(output_row.get("Amount", 0))
        except (ValueError, TypeError):
            print(f"  Invalid output amount '{output_row.get('Amount')}' for '{output_name}', skipping output.")
            continue

        if not output_name or output_amount <= 0:
            continue

        # If UUID is present, use the existing flow and add a normal output exchange.
        if uuid:
            flow = client.get(o.Flow, uid=uuid)
            if not flow:
                print(f"  Output flow UUID {uuid} not found for '{output_name}', skipping output.")
                continue

            out_ex = o.Exchange()
            out_ex.flow = flow
            out_ex.amount = output_amount
            out_ex.is_input = False
            process.exchanges.append(out_ex)
            output_created = True
            print(f"  Existing output flow '{output_name}' added with amount {output_amount}.")
            continue

        # If UUID is missing, create/reuse a custom output flow with LU->kg conversion.
        try:
            output_flow = _find_or_create_output_flow(client, output_name, output_amount)

            out_ex = o.Exchange()
            out_ex.flow = output_flow
            out_ex.amount = 1.0
            out_ex.is_input = False
            out_ex.is_quantitative_reference = True
            process.exchanges.append(out_ex)
            output_created = True
            print(f"  Output flow '{output_name}' ready: 1 LU = {output_amount} kg")
        except Exception as e:
            print(f"  Failed to build output flow '{output_name}': {e}")

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

    # Skip process creation when no valid exchanges were built.
    if input_count == 0 and not output_created:
        print("  No valid inputs and no valid output found, skipping process creation.")
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
    # Reader filters rows to Direction == Input.
    inputs = read_input_rows(csv_path)
    output_rows = read_output_rows(csv_path)
    if not inputs and not output_rows:
        print(f"No inputs or outputs found in {csv_path}, skipping.")
        return

    base = os.path.basename(csv_path)
    process_name = base.split("_ipe")[0]
    print(f"\nProcessing {base} -> process '{process_name}' in category '{category_name}'")
    build_process_from_inputs(client, process_name, inputs, category_name, output_rows)