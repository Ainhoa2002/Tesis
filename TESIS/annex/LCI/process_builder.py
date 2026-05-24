"""openLCA process and flow creation logic.

This module owns all openLCA-creation-related behavior for the import workflow:
- flow lookup/synchronization/creation
- process creation or rebuild with exchanges
- per-file import reporting with centralized warnings and errors
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import olca_schema as o
import logging

from csv_reader import read_input_rows, read_output_rows


@dataclass
class ProcessImportReport:
    """Structured report for one imported *_ipe CSV file."""

    csv_path: str
    process_name: str
    category_name: str
    process_uuid: str = ""
    process_created: bool = False
    skipped: bool = False
    created_output_flows: list[dict[str, str]] = field(default_factory=list)
    output_flows_for_library: list[dict[str, str]] = field(default_factory=list)
    process_provider_rows: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    inputs_built: int = 0


@dataclass
class ProductSystemCreationReport:
    process_name: str
    product_system_name: str
    product_system_uuid: str = ""
    created: bool = False
    updated: bool = False
    skipped: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _warn(report: ProcessImportReport, message: str) -> None:
    report.warnings.append(message)
    logging.warning(message)


def _error(report: ProcessImportReport, message: str) -> None:
    report.errors.append(message)
    logging.error(message)


def _normalize_category_path(value):
    """Return a normalized openLCA category path as plain string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        parts = [str(v).strip() for v in value if str(v).strip()]
        return "/".join(parts)
    return str(value).strip()


# search for the name in openLCA
def _get_entity_by_name(client, model_type, name):
    ref = client.find(model_type, name=name)
    if not ref:
        return None
    return client.get(model_type, uid=ref.id)


# Search for the flow property in openLCA, it can be Number, Piece or Item
def _get_number_flow_property(client):
    for prop_name in ("Number", "Piece", "Item"):
        prop = _get_entity_by_name(client, o.FlowProperty, prop_name)
        if prop:
            return prop
    return None


# Search for the flow property in openLCA, it can be Mass or Weight
def _get_mass_flow_property(client):
    return _get_entity_by_name(client, o.FlowProperty, "Mass")


def _get_transport_work_flow_property(client):
    # Common openLCA names for tkm-like properties.
    for prop_name in (
        "Mass transport",
        "Item transport",
        "Goods transport (mass*distance)",
        "Transport",
        "Transport work",
        "Mass*distance",
    ):
        prop = _get_entity_by_name(client, o.FlowProperty, prop_name)
        if prop:
            return prop

    # Fallback: pick a flow property that clearly represents transport work.
    # This covers database variants with localized/custom names.
    try:
        descriptors = list(client.get_descriptors(o.FlowProperty))
    except Exception:
        descriptors = []

    for descriptor in descriptors:
        name = str(getattr(descriptor, "name", "") or "").strip().lower()
        if name == "":
            continue
        if "transport" in name and ("mass" in name or "distance" in name):
            prop = client.get(o.FlowProperty, uid=descriptor.id)
            if prop:
                return prop
    return None


def _get_existing_process_by_name(client, process_name):
    """Return the existing openLCA process with this name, if any."""
    existing_ref = client.find(o.Process, name=process_name)
    if not existing_ref:
        return None
    return client.get(o.Process, uid=existing_ref.id)


def _same_ref(ref_a, ref_b):
    if not ref_a or not ref_b:
        return False
    id_a = str(getattr(ref_a, "id", "") or "").strip().lower()
    id_b = str(getattr(ref_b, "id", "") or "").strip().lower()
    if id_a and id_b:
        return id_a == id_b
    name_a = str(getattr(ref_a, "name", "") or "").strip().lower()
    name_b = str(getattr(ref_b, "name", "") or "").strip().lower()
    return bool(name_a and name_b and name_a == name_b)


def _upsert_flow_property_factor(flow, flow_property, conversion_factor, is_reference):
    if flow.flow_properties is None:
        flow.flow_properties = []

    for factor in flow.flow_properties:
        if _same_ref(getattr(factor, "flow_property", None), flow_property):
            changed = False
            if float(getattr(factor, "conversion_factor", 0.0) or 0.0) != float(conversion_factor):
                factor.conversion_factor = float(conversion_factor)
                changed = True
            if bool(getattr(factor, "is_ref_flow_property", False)) != bool(is_reference):
                factor.is_ref_flow_property = bool(is_reference)
                changed = True
            return changed

    factor = o.FlowPropertyFactor()
    factor.flow_property = flow_property
    factor.conversion_factor = float(conversion_factor)
    factor.is_ref_flow_property = bool(is_reference)
    flow.flow_properties.append(factor)
    return True


def _prune_non_reference_flow_properties(flow, keep_props):
    """Keep non-reference factors only for allowed flow properties.

    This avoids stale unit factors (for example old Mass/kg) when a flow is
    remapped to a different output unit such as tkm.
    """
    if flow.flow_properties is None:
        return False

    changed = False
    kept = []
    for factor in flow.flow_properties:
        if bool(getattr(factor, "is_ref_flow_property", False)):
            kept.append(factor)
            continue

        factor_prop = getattr(factor, "flow_property", None)
        keep = any(_same_ref(factor_prop, p) for p in keep_props if p is not None)
        if keep:
            kept.append(factor)
        else:
            changed = True

    if changed:
        flow.flow_properties = kept
    return changed


def _sync_output_flow_definition(client, flow, flow_name, amount_per_lu, output_unit, category_path):
    """Synchronize mutable output-flow attributes when possible.

    This keeps reused flows aligned with the current CSV contract:
    - product flow type
    - expected category path
    - Number as reference flow property (factor 1.0)
    - Secondary flow property based on output unit (kg or tkm)
    """
    if not flow:
        return

    desired_category = _normalize_category_path(category_path)
    changed = False

    if getattr(flow, "flow_type", None) != o.FlowType.PRODUCT_FLOW:
        flow.flow_type = o.FlowType.PRODUCT_FLOW
        changed = True

    if _normalize_category_path(getattr(flow, "category", "")) != desired_category:
        flow.category = desired_category
        changed = True

    number_prop = _get_number_flow_property(client)
    mass_prop = _get_mass_flow_property(client)
    transport_prop = _get_transport_work_flow_property(client)
    if not number_prop:
        raise ValueError("Flow property 'Number' (or equivalent) not found")

    unit_norm = str(output_unit or "").strip().lower()
    secondary_prop = mass_prop
    if unit_norm == "tkm" and transport_prop:
        secondary_prop = transport_prop
    elif unit_norm == "tkm" and not transport_prop:
        logging.warning("Flow property for 'tkm' not found. Falling back to 'Mass'.")

    if not secondary_prop:
        raise ValueError("Required flow property not found for output flow")

    changed = _upsert_flow_property_factor(flow, number_prop, 1.0, True) or changed
    changed = _upsert_flow_property_factor(flow, secondary_prop, amount_per_lu, False) or changed
    changed = _prune_non_reference_flow_properties(flow, keep_props=[secondary_prop]) or changed

    if not changed:
        return

    try:
        client.put(flow)
        logging.info("Flow '%s' synchronized (type/category/properties).", flow_name)
    except Exception as exc:
        logging.warning("Could not update flow '%s': %s. Reusing as-is.", flow_name, exc)


################ Find or create an output ############################
# Used when the output flow is missing a UUID
# It creates a new flow with the name of the flow and the conversion factor
# from LU to kg based on the amount in the CSV.
# If the flow already exists (by name), it will be moved to the desired category.
def _find_or_create_output_flow(client, flow_name, amount_per_lu, output_unit, category_path):
    desired_category = _normalize_category_path(category_path)

    # Obtain required flow properties once for both create and reuse paths.
    number_prop = _get_number_flow_property(client)
    mass_prop = _get_mass_flow_property(client)
    transport_prop = _get_transport_work_flow_property(client)

    if not number_prop:
        raise ValueError("Flow property 'Number' (or equivalent) not found")
    unit_norm = str(output_unit or "").strip().lower()
    secondary_prop = mass_prop
    if unit_norm == "tkm" and transport_prop:
        secondary_prop = transport_prop
    elif unit_norm == "tkm" and not transport_prop:
        logging.warning("Flow property for 'tkm' not found. Falling back to 'Mass'.")

    if not secondary_prop:
        raise ValueError("Required flow property not found for output flow")

    # Try to find it by name to reuse if it already exists
    existing_ref = client.find(o.Flow, name=flow_name)
    if existing_ref:
        flow = client.get(o.Flow, uid=existing_ref.id)
        if flow:
            _sync_output_flow_definition(
                client,
                flow,
                flow_name,
                amount_per_lu,
                output_unit,
                desired_category,
            )
            return flow, False

    # Creates new flow (the output flow)
    flow = o.Flow()
    flow.name = flow_name
    flow.flow_type = o.FlowType.PRODUCT_FLOW
    flow.category = desired_category

    factor_number = o.FlowPropertyFactor()
    factor_number.flow_property = number_prop
    factor_number.conversion_factor = 1.0
    factor_number.is_ref_flow_property = True

    factor_secondary = o.FlowPropertyFactor()
    factor_secondary.flow_property = secondary_prop
    factor_secondary.conversion_factor = amount_per_lu
    factor_secondary.is_ref_flow_property = False

    flow.flow_properties = [factor_number, factor_secondary]

    client.put(flow)

    created_ref = client.find(o.Flow, name=flow_name)
    if not created_ref:
        raise ValueError(f"Flow '{flow_name}' could not be created")
    created_flow = client.get(o.Flow, uid=created_ref.id)
    if not created_flow:
        raise ValueError(f"Flow '{flow_name}' could not be retrieved after creation")
    return created_flow, True


def _build_process_provider_rows(process_name: str, process_uuid: str, output_flow_references: list[str]):
    rows = []
    for flow_ref in output_flow_references:
        flow_value = str(flow_ref or "").strip()
        if flow_value == "" or process_uuid == "":
            continue
        rows.append(
            {
                "Ecoinvent_flow_reference": flow_value,
                "Ecoinvent_process": process_name,
                "UUID_provider": process_uuid,
            }
        )
    return rows


################ Creates the process in openLCA with the inputs and outputs ############################
def build_process_from_inputs(client, process_name, inputs, category_name, report: ProcessImportReport, output_rows=None):
    existing_process = _get_existing_process_by_name(client, process_name)
    process_exists = existing_process is not None
    process = o.Process()
    if existing_process:
        process.id = existing_process.id
        logging.info("Rebuilding existing process '%s' (ID: %s).", process_name, process.id)
    else:
        logging.info("Creating new process '%s'.", process_name)

    process.name = process_name
    process.process_type = o.ProcessType.UNIT_PROCESS
    process.exchanges = []
    process.category = category_name

    output_created = False
    created_output_flows = []
    output_flows_for_library = []
    seen_output_flow_library_keys = set()
    output_flow_references = []
    seen_output_refs = set()
    flow_category_path = _normalize_category_path(category_name)

    for output_row in (output_rows or []):
        output_name = str(output_row.get("Flow", "")).strip()
        uuid = str(output_row.get("UUID", "")).strip()
        output_unit = str(output_row.get("Unit", "") or "").strip().lower()
        try:
            output_amount = float(output_row.get("Amount", 0))
        except (ValueError, TypeError):
            _warn(
                report,
                f"  Invalid output amount '{output_row.get('Amount')}' for '{output_name}', skipping output.",
            )
            continue

        logging.debug("Processing output: name='%s', uuid='%s', unit='%s', amount='%s'", output_name, uuid, output_unit, output_amount)

        if not output_name or output_amount <= 0:
            logging.debug("Skipping output '%s' due to missing name or non-positive amount.", output_name)
            continue

        if uuid:
            flow = client.get(o.Flow, uid=uuid)
            if not flow:
                _warn(report, f"  Output flow UUID {uuid} not found for '{output_name}', skipping output.")
                continue

            try:
                _sync_output_flow_definition(
                    client,
                    flow,
                    output_name,
                    output_amount,
                    output_unit,
                    flow_category_path,
                )
            except Exception as e:
                _warn(report, f"  Warning: Could not synchronize output flow '{output_name}' ({uuid}): {e}")

            out_ex = o.Exchange()
            out_ex.flow = flow
            out_ex.amount = output_amount
            out_ex.is_input = False
            process.exchanges.append(out_ex)
            output_created = True
            logging.info("Existing output flow '%s' added with amount %s.", output_name, output_amount)

            output_flow_key = output_name.lower()
            if output_flow_key not in seen_output_flow_library_keys:
                seen_output_flow_library_keys.add(output_flow_key)
                output_flows_for_library.append({"Flow": output_name, "UUID": flow.id})
                logging.debug("Added output flow to mapping: %s -> %s", output_name, flow.id)

            output_key = output_name.lower()
            if output_key not in seen_output_refs:
                seen_output_refs.add(output_key)
                output_flow_references.append(output_name)
            continue

        try:
            output_flow, flow_was_created = _find_or_create_output_flow(
                client,
                output_name,
                output_amount,
                output_unit,
                flow_category_path,
            )

            out_ex = o.Exchange()
            out_ex.flow = output_flow
            out_ex.amount = 1.0
            out_ex.is_input = False
            out_ex.is_quantitative_reference = True
            process.exchanges.append(out_ex)
            output_created = True
            unit_label = output_unit if output_unit else "kg"
            logging.info("Output flow '%s' ready: 1 LU = %s %s", output_name, output_amount, unit_label)
            if flow_was_created:
                created_output_flows.append({"Flow": output_name, "UUID": output_flow.id})
                logging.debug("Created new output flow: %s -> %s", output_name, output_flow.id)

            output_flow_key = output_name.lower()
            if output_flow_key not in seen_output_flow_library_keys:
                seen_output_flow_library_keys.add(output_flow_key)
                output_flows_for_library.append({"Flow": output_name, "UUID": output_flow.id})
                logging.debug("Added output flow to mapping: %s -> %s", output_name, output_flow.id)

            output_key = output_name.lower()
            if output_key not in seen_output_refs:
                seen_output_refs.add(output_key)
                output_flow_references.append(output_name)
        except Exception as e:
            _error(report, f"  Failed to build output flow '{output_name}': {e}")
            logging.debug("Exception while creating output flow '%s': %s", output_name, e)

    input_count = 0
    for row in inputs:
        uuid = row.get("UUID", "").strip()
        provider_uuid = row.get("UUID_provider", "").strip()
        flow_name = str(row.get("Flow", "")).strip()
        logging.debug("Processing input: flow='%s', uuid='%s', provider_uuid='%s', amount='%s'", flow_name, uuid, provider_uuid, row.get('Amount', 0))

        if not uuid:
            if flow_name:
                _warn(report, f"  Missing UUID for input '{flow_name}', skipping to avoid creating a new flow.")
                logging.debug("Skipping input '%s' due to missing UUID.", flow_name)
            else:
                logging.debug("Skipping input with empty flow name and missing UUID.")
            continue

        flow = client.get(o.Flow, uid=uuid)
        if not flow:
            _warn(report, f"  Flow with UUID {uuid} not found, skipping.")
            logging.debug("Input flow UUID '%s' not found for '%s'.", uuid, flow_name)
            continue

        try:
            amount = float(row.get("Amount", 0))
        except (ValueError, TypeError):
            _warn(report, f"  Invalid amount '{row.get('Amount')}' for UUID {uuid}, skipping.")
            logging.debug("Invalid amount for input '%s' with UUID '%s'.", flow_name, uuid)
            continue

        in_ex = o.Exchange()
        in_ex.flow = flow
        in_ex.amount = amount
        in_ex.is_input = True
        process.exchanges.append(in_ex)
        logging.debug("Added input exchange for flow '%s' with UUID '%s' and amount %s.", flow_name, uuid, amount)

        if provider_uuid and provider_uuid != "NO_PROVIDER":
            provider = client.get(o.Process, uid=provider_uuid)
            if provider:
                provider_ref = o.Ref()
                provider_ref.id = provider.id
                provider_ref.name = provider.name
                provider_ref.ref_type = o.RefType.Process
                in_ex.default_provider = provider_ref
                logging.debug("Set default provider for input '%s' to process '%s' (%s)", flow_name, provider.name, provider.id)
            else:
                _warn(report, f"    Warning: Provider UUID {provider_uuid} not found")
                logging.debug("Provider UUID '%s' not found for input '%s'.", provider_uuid, flow_name)
        else:
            in_ex.default_provider = None

        input_count += 1

    report.inputs_built = input_count

    if input_count == 0 and not output_created:
        report.skipped = True
        _warn(report, "  No valid inputs and no valid output found, skipping process creation.")
        return report

    if process.id:
        logging.info("Existing process will be overwritten in openLCA.")
    else:
        logging.info("New process will be created in openLCA.")

    try:
        client.put(process)
        logging.info("Process '%s' saved with %s inputs.", process_name, input_count)
    except Exception as e:
        report.skipped = True
        _error(report, f"  Failed to save process: {e}")
        return report

    fetched = client.get(o.Process, name=process_name)
    if fetched:
        report.process_uuid = str(getattr(fetched, "id", "") or "")
        logging.info("Verified: process '%s' (ID: %s)", fetched.name, fetched.id)
    else:
        report.process_uuid = str(getattr(process, "id", "") or "")
        _warn(report, f"  Warning: process '{process_name}' not found after saving.")

    report.process_created = not process_exists
    report.created_output_flows = created_output_flows
    report.output_flows_for_library = output_flows_for_library
    report.process_provider_rows = _build_process_provider_rows(
        process_name=process_name,
        process_uuid=report.process_uuid,
        output_flow_references=output_flow_references,
    )
    return report


########## PROCESS CREATION FUNCTION END ############################
def process_csv(client, csv_path, category_name):
    """Import one *_ipe CSV file into openLCA and return structured report."""
    base = os.path.basename(csv_path)
    process_name = base.split("_ipe")[0]
    report = ProcessImportReport(
        csv_path=csv_path,
        process_name=process_name,
        category_name=category_name,
    )

    inputs = read_input_rows(csv_path)
    output_rows = read_output_rows(csv_path)
    if not inputs and not output_rows:
        report.skipped = True
        _warn(report, f"No inputs or outputs found in {csv_path}, skipping.")
        return report

    logging.info("Processing %s -> process '%s' in category '%s'", base, process_name, category_name)
    return build_process_from_inputs(client, process_name, inputs, category_name, report, output_rows)
