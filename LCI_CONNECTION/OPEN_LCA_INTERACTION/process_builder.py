import csv

def find_or_create_flow(client, name, unit_name, flow_type="PRODUCT_FLOW"):
    flow = client.find("Flow", name)   # "Flow" en lugar de ModelType.FLOW
    if flow is not None:
        return flow
    unit = client.find("Unit", unit_name)
    if unit is None:
        raise ValueError(f"Unit {unit_name} not found in database")
    flow = client.insert(
        "Flow",
        name=name,
        flow_type=flow_type,
        unit=unit
    )
    return flow

def create_or_update_process(client, name, category, reference_flow, reference_amount, exchanges, location=None):
    existing = client.find("Process", name)
    if existing:
        existing['default_flow'] = reference_flow
        existing['default_flow_amount'] = reference_amount
        existing['exchanges'] = exchanges
        if location:
            existing['location'] = location
        existing['category'] = category
        updated = client.insert(existing)   # aquí ya es un objeto completo
        print(f"Updated existing process: {name} (ID: {updated['id']})")
        return updated
    else:
        process = client.insert(
            "Process",
            name=name,
            category=category,
            default_flow=reference_flow,
            default_flow_amount=reference_amount,
            location=location,
            exchanges=exchanges
        )
        print(f"Created new process: {name} (ID: {process['id']})")
        return process

def create_intermediate_process(client, pre_input_flow_name, pre_process_flow_name, amount, unit_name):
    input_flow = find_or_create_flow(client, pre_input_flow_name, unit_name)
    output_flow = find_or_create_flow(client, pre_process_flow_name, unit_name)

    proc_name = f"Production of {pre_process_flow_name} from {pre_input_flow_name}"
    proc_category = ["Intermediate processes"]

    exchanges = [
        {
            "flow": output_flow,
            "amount": amount,
            "is_input": False,
            "quantitative_reference": True
        },
        {
            "flow": input_flow,
            "amount": amount,
            "is_input": True,
            "quantitative_reference": False
        }
    ]

    process = create_or_update_process(
        client,
        name=proc_name,
        category=proc_category,
        reference_flow=output_flow,
        reference_amount=amount,
        exchanges=exchanges,
        location=client.find("Location", "GLO")
    )
    return process, output_flow

def process_csv(client, file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    direct_inputs = []
    pre_pairs = []

    i = 0
    while i < len(rows):
        row = rows[i]
        direction = row['Direction'].strip()
        flow_name = row['Flow'].strip()
        amount = float(row['Amount'])
        unit = row['Unit'].strip()

        if direction == 'Input':
            direct_inputs.append((flow_name, amount, unit))
        elif direction == 'pre-input':
            if i+1 < len(rows) and rows[i+1]['Direction'].strip() == 'pre-process' \
               and float(rows[i+1]['Amount']) == amount \
               and rows[i+1]['Unit'].strip() == unit:
                pre_process_name = rows[i+1]['Flow'].strip()
                pre_pairs.append((flow_name, pre_process_name, amount, unit))
                i += 1
            else:
                print(f"Warning: no matching pre-process found for {flow_name}")
        i += 1

    import os
    base = os.path.basename(file_path)
    main_name = base.replace('_ipe_flows_from_parameters.csv', '').replace('_', ' ').title()
    main_category = ["Main processes"]

    ref_product_flow = find_or_create_flow(client, main_name, "piece")

    main_exchanges = [
        {
            "flow": ref_product_flow,
            "amount": 1.0,
            "is_input": False,
            "quantitative_reference": True
        }
    ]

    for flow_name, amount, unit in direct_inputs:
        flow = find_or_create_flow(client, flow_name, unit)
        main_exchanges.append({
            "flow": flow,
            "amount": amount,
            "is_input": True,
            "quantitative_reference": False
        })

    for pre_input, pre_process, amount, unit in pre_pairs:
        inter_proc, output_flow = create_intermediate_process(client, pre_input, pre_process, amount, unit)
        main_exchanges.append({
            "flow": output_flow,
            "amount": amount,
            "is_input": True,
            "quantitative_reference": False
        })

    create_or_update_process(
        client,
        name=main_name,
        category=main_category,
        reference_flow=ref_product_flow,
        reference_amount=1.0,
        exchanges=main_exchanges,
        location=client.find("Location", "GLO")
    )







































