"""
Flow builder for openLCA flows, similar to process_builder.py.
Allows specifying output folder and updates created_flows_uuid_map.csv.
"""

import os
import csv
from pathlib import Path
import logging
try:
    import olca_schema as o
except Exception as exc:
    logging.warning("olca_schema not available: %s", exc)
    o = None
import sys

# interactive-safe output helper
_IS_TTY = sys.stdout.isatty()
def _out(msg: str, level: str = "info") -> None:
    if _IS_TTY:
        print(msg)
    else:
        import logging
        getattr(logging, level)(msg)

CREATED_FLOWS_MAP = Path(__file__).resolve().parent / "created_flows_uuid_map.csv"

def flow_exists(flow_name, client):
    if o is None or client is None:
        logging.warning("Cannot check flow existence: olca_schema or client not available")
        return None
    ref = client.find(o.Flow, name=flow_name)
    if ref:
        flow = client.get(o.Flow, uid=ref.id)
        logging.info("Flow '%s' exists with the UUID: %s", flow_name, flow.id)
        return flow
    return None

def add_flow_to_map(flow_name, flow_uuid):
    if not CREATED_FLOWS_MAP.exists():
        with open(CREATED_FLOWS_MAP, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Flow", "UUID"])
    # Check if already present (skip header and empty rows)
    with open(CREATED_FLOWS_MAP, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if row and row[0] == flow_name:
                return
    with open(CREATED_FLOWS_MAP, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([flow_name, flow_uuid])

def build_flow(client, flow_name, unit, flow_type, **kwargs):
    # Check if flow exists
    existing = flow_exists(flow_name, client)
    if existing:
        return existing
    # Search all FlowProperties for a matching unit name (case-insensitive)
    flow_property = None
    if o is None or client is None:
        logging.error("Cannot build flow: olca_schema or olca client not available")
        return None

    for prop_desc in client.get_descriptors(o.FlowProperty):
        if prop_desc.name.strip().lower() == unit.strip().lower():
            flow_property = client.get(o.FlowProperty, uid=prop_desc.id)
            break
    if not flow_property:
        logging.warning("No matching FlowProperty found for unit '%s'. The unit will not be set.", unit)
        return None
    # Create flow using openLCA API helpers
    if flow_type == "elementary":
        flow = o.new_elementary_flow(flow_name, flow_property)
    else:
        flow = o.new_product(flow_name, flow_property)
    client.put(flow)
    # Always write summary to default location (same folder as script)
    with open(f"{flow_name}_summary.txt", "w", encoding="utf-8") as f:
        f.write(f"Flow: {flow_name}\nUUID: {flow.id}\nUnit: {unit}\nType: {flow_type}\n")
    add_flow_to_map(flow_name, flow.id)
    logging.info("Flow '%s' created with UUID: %s, unit: %s, type: %s", flow_name, flow.id, unit, flow_type)
    return flow


if __name__ == "__main__":
    try:
        import olca_ipc as ipc
    except Exception as exc:
        logging.error("olca_ipc not available: %s", exc)
        ipc = None
    import sys as _sys

    _out("--- Flow Builder ---")
    flow_name = input("Enter flow name: ").strip()
    if not flow_name:
        _out("No flow name provided. Exiting.")
        _sys.exit(1)

    client = None
    if ipc is not None:
        try:
            client = ipc.Client(8080)
        except Exception as exc:
            logging.exception("Could not connect to openLCA IPC: %s", exc)

    existing = flow_exists(flow_name, client)
    if existing:
        _sys.exit(0)

    # Ask for unit and require it
    unit = input("Enter flow unit (e.g., kg, LU, tkm, item): ").strip()
    while not unit:
        _out("Unit is required.", level="warning")
        unit = input("Enter flow unit (e.g., kg, LU, tkm, item): ").strip()

    # Ask for flow type
    flow_type = input("Enter flow type ('elementary' or 'product', default: product): ").strip().lower()
    if flow_type not in ("elementary", "product"):
        flow_type = "product"

    build_flow(client, flow_name, unit=unit, flow_type=flow_type)
