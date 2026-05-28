from __future__ import annotations

import argparse
import sys
import logging

# interactive-safe output helper
_IS_TTY = sys.stdout.isatty()
def _out(msg: str, level: str = "info") -> None:
    if _IS_TTY:
        print(msg)
    else:
        getattr(logging, level)(msg)
import re
from dataclasses import dataclass, field

import olca_ipc as ipc
import olca_schema as o

from parameter_library import get_param, set_param


PREFER_DEFAULTS_PARAM = "product_systems_prefer_defaults"
PRODUCT_SYSTEMS_MODULE_PARAM = "product_systems_module"
INTERACTIVE_MODE_PARAM = "product_systems_interactive_mode"


@dataclass
class ProductSystemCreationReport:
    process_input: str
    process_name: str = ""
    product_system_uuid: str = ""
    created: bool = False
    updated: bool = False
    skipped: bool = False
    provider_linking: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _normalize_name(value: str) -> str:
    return str(value or "").strip().lower()


def _parse_csv_names(raw: str) -> list[str]:
    out = []
    seen = set()
    for part in str(raw or "").split(","):
        name = part.strip()
        key = _normalize_name(name)
        if key == "" or key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


def _as_name_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return _parse_csv_names(value)
    return []


def get_prefer_defaults_processes() -> list[str]:
    return _as_name_list(get_param(PREFER_DEFAULTS_PARAM, default=[]))


def get_interactive_mode() -> int:
    """Get interactive mode: 0=silent (use params only), 1=interactive (can ask user)."""
    value = get_param(INTERACTIVE_MODE_PARAM, default=1)
    try:
        return int(value)
    except (ValueError, TypeError):
        return 1  # Default to interactive if invalid


def set_interactive_mode(mode: int) -> None:
    """Set interactive mode: 0=silent, 1=interactive."""
    set_param(INTERACTIVE_MODE_PARAM, int(mode))


def set_prefer_defaults_processes(process_names: list[str]) -> None:
    cleaned = []
    seen = set()
    for name in process_names:
        text = str(name or "").strip()
        key = _normalize_name(text)
        if key == "" or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    set_param(PREFER_DEFAULTS_PARAM, cleaned)


def _normalize_mode_text(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in {"prefer", "prefer-defaults", "prefer_defaults", "p"}:
        return "prefer-defaults"
    if text in {"only", "only-defaults", "only_defaults", "o"}:
        return "only-defaults"
    if text in {"ignore", "ignore-defaults", "ignore_defaults", "i"}:
        return "ignore-defaults"
    return ""


def _default_product_systems_module() -> dict:
    return {
        "components": []
    }


def get_product_systems_module() -> dict:
    raw = get_param(PRODUCT_SYSTEMS_MODULE_PARAM, default=_default_product_systems_module())
    if not isinstance(raw, dict):
        return _default_product_systems_module()

    components = raw.get("components", [])
    if not isinstance(components, list):
        components = []

    normalized_components = []
    seen = set()
    for item in components:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        mode = _normalize_mode_text(item.get("provider_linking", ""))
        key = _normalize_name(name)
        if key == "" or key in seen:
            continue
        seen.add(key)
        if mode == "":
            mode = "only-defaults"
        normalized_components.append({"name": name, "provider_linking": mode})

    return {"components": normalized_components}


def set_product_systems_module(components: list[dict[str, str]]) -> None:
    cleaned = []
    seen = set()
    for item in components:
        name = str(item.get("name", "") or "").strip()
        mode = _normalize_mode_text(item.get("provider_linking", ""))
        key = _normalize_name(name)
        if key == "" or key in seen:
            continue
        if mode == "":
            mode = "only-defaults"
        seen.add(key)
        cleaned.append({"name": name, "provider_linking": mode})

    set_param(PRODUCT_SYSTEMS_MODULE_PARAM, {"components": cleaned})


def _module_component_mode_map(module_doc: dict) -> dict[str, str]:
    component_mode_map = {}
    for item in module_doc.get("components", []):
        name_key = _normalize_name(item.get("name", ""))
        mode = _normalize_mode_text(item.get("provider_linking", ""))
        if name_key == "" or mode == "":
            continue
        component_mode_map[name_key] = mode
    return component_mode_map


def _module_component_names(module_doc: dict) -> list[str]:
    out = []
    seen = set()
    for item in module_doc.get("components", []):
        name = str(item.get("name", "") or "").strip()
        key = _normalize_name(name)
        if key == "" or key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


def _mode_name(mode: o.ProviderLinking) -> str:
    if mode == o.ProviderLinking.PREFER_DEFAULTS:
        return "PREFER_DEFAULTS"
    if mode == o.ProviderLinking.ONLY_DEFAULTS:
        return "ONLY_DEFAULTS"
    if mode == o.ProviderLinking.IGNORE_DEFAULTS:
        return "IGNORE_DEFAULTS"
    return str(mode)


def _is_uuid_like(value: str) -> bool:
    text = str(value or "").strip()
    return bool(re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}", text))


def _resolve_process_descriptor(client, process_input: str):
    token = str(process_input or "").strip()
    if token == "":
        return None

    if _is_uuid_like(token):
        process = client.get(o.Process, uid=token)
        if process:
            # Convert UUID input to a descriptor accepted by create_product_system.
            return client.find(o.Process, name=str(getattr(process, "name", "") or ""))

    return client.find(o.Process, name=token)


def _select_provider_linking(
    process_name: str,
    strategy: str,
    prefer_defaults_set: set[str],
    component_mode_map: dict[str, str] | None = None,
) -> o.ProviderLinking:
    mode = str(strategy or "parameter").strip().lower()
    if mode == "prefer-defaults":
        return o.ProviderLinking.PREFER_DEFAULTS
    if mode == "only-defaults":
        return o.ProviderLinking.ONLY_DEFAULTS
    if mode == "ignore-defaults":
        return o.ProviderLinking.IGNORE_DEFAULTS

    # parameter strategy:
    # 1) if process has explicit mode in product_systems_module.components, use it
    # 2) else fallback to legacy product_systems_prefer_defaults vector
    # 3) default to ONLY_DEFAULTS
    name_key = _normalize_name(process_name)
    selected_mode = ""
    if component_mode_map is not None:
        selected_mode = _normalize_mode_text(component_mode_map.get(name_key, ""))
    if selected_mode == "prefer-defaults":
        return o.ProviderLinking.PREFER_DEFAULTS
    if selected_mode == "only-defaults":
        return o.ProviderLinking.ONLY_DEFAULTS
    if selected_mode == "ignore-defaults":
        return o.ProviderLinking.IGNORE_DEFAULTS

    if _normalize_name(process_name) in prefer_defaults_set:
        return o.ProviderLinking.PREFER_DEFAULTS
    return o.ProviderLinking.ONLY_DEFAULTS


def create_or_update_product_system(
    client,
    process_input: str,
    strategy: str = "parameter",
    prefer_defaults_processes: list[str] | None = None,
    component_mode_map: dict[str, str] | None = None,
) -> ProductSystemCreationReport:
    report = ProductSystemCreationReport(process_input=str(process_input or "").strip())

    process_ref = _resolve_process_descriptor(client, report.process_input)
    if not process_ref:
        report.skipped = True
        report.warnings.append(f"Process '{report.process_input}' not found, skipping.")
        logging.warning(report.warnings[-1])
        return report

    process_name = str(getattr(process_ref, "name", "") or report.process_input)
    report.process_name = process_name

    prefer_defaults_source = get_prefer_defaults_processes() if prefer_defaults_processes is None else prefer_defaults_processes
    prefer_defaults_set = {_normalize_name(n) for n in prefer_defaults_source}
    mode = _select_provider_linking(
        process_name,
        strategy=strategy,
        prefer_defaults_set=prefer_defaults_set,
        component_mode_map=component_mode_map,
    )
    report.provider_linking = _mode_name(mode)

    existing_ps = client.find(o.ProductSystem, name=process_name)
    if existing_ps:
        report.skipped = True
        logging.info("Skipped existing product system for '%s'", process_name)
        return report

    config = o.LinkingConfig(
        prefer_unit_processes=True,
        provider_linking=mode,
    )

    try:
        new_ps = client.create_product_system(process_ref, config)
    except Exception as exc:
        report.skipped = True
        report.errors.append(f"Failed to create product system '{process_name}': {exc}")
        logging.exception("%s", report.errors[-1])
        return report

    if not new_ps:
        report.skipped = True
        report.errors.append(f"Product system '{process_name}' was not created.")
        logging.error("%s", report.errors[-1])
        return report

    report.product_system_uuid = str(getattr(new_ps, "id", "") or "")
    if not report.updated:
        report.created = True
    logging.info(
        "Created product system '%s' (ID: %s) with provider_linking=%s",
        process_name,
        report.product_system_uuid,
        report.provider_linking,
    )
    return report


def create_product_systems_for_processes(
    client,
    process_inputs: list[str],
    strategy: str = "parameter",
    prefer_defaults_processes: list[str] | None = None,
    component_mode_map: dict[str, str] | None = None,
) -> list[ProductSystemCreationReport]:
    reports = []
    seen = set()
    for token in process_inputs:
        key = _normalize_name(token)
        if key == "" or key in seen:
            continue
        seen.add(key)
        reports.append(
            create_or_update_product_system(
                client,
                process_input=token,
                strategy=strategy,
                prefer_defaults_processes=prefer_defaults_processes,
                component_mode_map=component_mode_map,
            )
        )
    return reports


def _parse_component_modes(raw: str) -> list[dict[str, str]]:
    out = []
    seen = set()
    for part in str(raw or "").split(","):
        token = part.strip()
        if token == "":
            continue
        if ":" in token:
            name, mode_raw = token.split(":", 1)
        elif "=" in token:
            name, mode_raw = token.split("=", 1)
        else:
            name, mode_raw = token, "only-defaults"

        clean_name = str(name or "").strip()
        clean_mode = _normalize_mode_text(mode_raw)
        key = _normalize_name(clean_name)
        if key == "" or key in seen:
            continue
        if clean_mode == "":
            clean_mode = "only-defaults"
        seen.add(key)
        out.append({"name": clean_name, "provider_linking": clean_mode})
    return out


def _prompt_linking_choice() -> str:
    while True:
        raw = input("Provider linking mode? [1=Prefer default provider, 2=Only link default provider]: ").strip().lower()
        if raw in {"1", "prefer", "prefer-defaults", "p", "yes", "y"}:
            return "prefer-defaults"
        if raw in {"2", "only", "only-defaults", "o", "no", "n"}:
            return "only-defaults"
        _out("Please choose 1 (Prefer default provider) or 2 (Only link default provider).", level="warning")


def _interactive_inputs() -> tuple[list[str], str]:
    raw_names = input("Process names or UUIDs (comma-separated): ").strip()
    names = _parse_csv_names(raw_names)
    if not names:
        return [], ""

    return names, _prompt_linking_choice()


def _prompt_process_inputs(client) -> list[str]:
    raw_names = input("Enter process names or UUIDs to analyze/create (comma-separated): ").strip()
    return _parse_csv_names(raw_names)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone product system builder for openLCA")
    parser.add_argument(
        "--process-names",
        default="",
        help="Comma-separated process names or UUIDs to build product systems for.",
    )
    parser.add_argument(
        "--provider-linking",
        choices=["parameter", "prefer-defaults", "only-defaults", "ignore-defaults"],
        default="parameter",
        help="Linking strategy. 'parameter' uses product_systems_prefer_defaults vector from parameter library.",
    )
    parser.add_argument(
        "--prefer-default-processes",
        default="",
        help="Optional extra comma-separated process names treated as PREFER_DEFAULTS for this run.",
    )
    parser.add_argument(
        "--set-prefer-default-processes",
        default="",
        help="Update parameter vector product_systems_prefer_defaults and exit unless --process-names is also provided.",
    )
    parser.add_argument(
        "--set-module-components",
        default="",
        help="Set product_systems_module.components using entries like 'magnet:prefer-defaults,connection_cables:only-defaults'.",
    )
    parser.add_argument(
        "--set-interactive-mode",
        type=int,
        choices=[0, 1],
        help="Set interactive mode: 0=silent (use params only), 1=interactive (ask user).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for process names and linking mode interactively.",
    )
    return parser


def _run_cli() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.set_prefer_default_processes:
        new_values = _parse_csv_names(args.set_prefer_default_processes)
        set_prefer_defaults_processes(new_values)
        _out(
            "Updated parameter 'product_systems_prefer_defaults': "
            f"{new_values}",
            level="info",
        )
        if not args.process_names and not args.interactive:
            return 0

    if args.set_module_components:
        module_components = _parse_component_modes(args.set_module_components)
        set_product_systems_module(module_components)
        _out(
            "Updated parameter 'product_systems_module.components': "
            f"{module_components}",
            level="info",
        )
        if not args.process_names and not args.interactive:
            return 0

    if args.set_interactive_mode is not None:
        set_interactive_mode(args.set_interactive_mode)
        _out(
            f"Updated parameter 'product_systems_interactive_mode': {args.set_interactive_mode} "
            f"({['silent (use params only)', 'interactive (ask user)'][args.set_interactive_mode]})",
            level="info",
        )
        if not args.process_names and not args.interactive:
            return 0

    # Check interactive mode flag from parameters
    interactive_mode_param = get_interactive_mode()
    allow_prompting = interactive_mode_param == 1 or args.interactive

    process_names = _parse_csv_names(args.process_names)
    mode = str(args.provider_linking or "").strip().lower()
    if args.interactive:
        interactive_names, interactive_mode = _interactive_inputs()
        if interactive_names:
            process_names = interactive_names
        if interactive_mode:
            mode = interactive_mode

    client = ipc.Client(8080)

    module_doc = get_product_systems_module()
    module_component_mode_map = _module_component_mode_map(module_doc)
    
    # Auto-load module components only if NOT prompting user (silent mode)
    if mode == "parameter" and not process_names and not allow_prompting:
        process_names = _module_component_names(module_doc)

    # Only prompt if interactive mode is enabled (1) and no process names provided
    if not process_names:
        if allow_prompting:
            process_names = _prompt_process_inputs(client)
            if not process_names:
                _out("No process names were provided.", level="warning")
                return 1
            if mode in {"", "parameter"}:
                mode = _prompt_linking_choice()
        else:
            # Silent mode: no prompting allowed
            _out("No process names provided and interactive mode is disabled (product_systems_interactive_mode=0).", level="warning")
            return 1

    if mode == "":
        mode = "parameter"

    extra_prefer_defaults = _parse_csv_names(args.prefer_default_processes)
    configured_prefer_defaults = get_prefer_defaults_processes()
    merged_prefer_defaults = configured_prefer_defaults + [
        n for n in extra_prefer_defaults if _normalize_name(n) not in {_normalize_name(v) for v in configured_prefer_defaults}
    ]

    reports = create_product_systems_for_processes(
        client,
        process_inputs=process_names,
        strategy=mode,
        prefer_defaults_processes=merged_prefer_defaults,
        component_mode_map=module_component_mode_map,
    )

    created = sum(1 for r in reports if r.created)
    updated = sum(1 for r in reports if r.updated)
    skipped = sum(1 for r in reports if r.skipped)
    errors = sum(len(r.errors) for r in reports)
    _out(
        "Product system builder complete. "
        f"Created: {created}. Updated: {updated}. Skipped: {skipped}. Errors: {errors}.",
        level=("info" if errors == 0 else "warning"),
    )
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(_run_cli())
