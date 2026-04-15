from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field

import olca_ipc as ipc
import olca_schema as o

from parameter_library import get_param, set_param


PREFER_DEFAULTS_PARAM = "product_systems_prefer_defaults"


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


def _select_provider_linking(process_name: str, strategy: str, prefer_defaults_set: set[str]) -> o.ProviderLinking:
    mode = str(strategy or "parameter").strip().lower()
    if mode == "prefer-defaults":
        return o.ProviderLinking.PREFER_DEFAULTS
    if mode == "only-defaults":
        return o.ProviderLinking.ONLY_DEFAULTS
    if mode == "ignore-defaults":
        return o.ProviderLinking.IGNORE_DEFAULTS

    # parameter strategy: process names in parameter vector use PREFER_DEFAULTS,
    # all others use ONLY_DEFAULTS.
    if _normalize_name(process_name) in prefer_defaults_set:
        return o.ProviderLinking.PREFER_DEFAULTS
    return o.ProviderLinking.ONLY_DEFAULTS


def create_or_update_product_system(
    client,
    process_input: str,
    strategy: str = "parameter",
    prefer_defaults_processes: list[str] | None = None,
) -> ProductSystemCreationReport:
    report = ProductSystemCreationReport(process_input=str(process_input or "").strip())

    process_ref = _resolve_process_descriptor(client, report.process_input)
    if not process_ref:
        report.skipped = True
        report.warnings.append(f"Process '{report.process_input}' not found, skipping.")
        print(report.warnings[-1])
        return report

    process_name = str(getattr(process_ref, "name", "") or report.process_input)
    report.process_name = process_name

    prefer_defaults_source = get_prefer_defaults_processes() if prefer_defaults_processes is None else prefer_defaults_processes
    prefer_defaults_set = {_normalize_name(n) for n in prefer_defaults_source}
    mode = _select_provider_linking(process_name, strategy=strategy, prefer_defaults_set=prefer_defaults_set)
    report.provider_linking = _mode_name(mode)

    existing_ps = client.find(o.ProductSystem, name=process_name)
    if existing_ps:
        try:
            client.delete(existing_ps)
            report.updated = True
            print(f"Deleted existing product system for '{process_name}'")
        except Exception as exc:
            report.skipped = True
            report.errors.append(f"Failed to delete existing product system '{process_name}': {exc}")
            print(report.errors[-1])
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
        print(report.errors[-1])
        return report

    if not new_ps:
        report.skipped = True
        report.errors.append(f"Product system '{process_name}' was not created.")
        print(report.errors[-1])
        return report

    report.product_system_uuid = str(getattr(new_ps, "id", "") or "")
    if not report.updated:
        report.created = True
    print(
        f"Created product system '{process_name}' (ID: {report.product_system_uuid}) "
        f"with provider_linking={report.provider_linking}"
    )
    return report


def create_product_systems_for_processes(
    client,
    process_inputs: list[str],
    strategy: str = "parameter",
    prefer_defaults_processes: list[str] | None = None,
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
            )
        )
    return reports


def _prompt_linking_choice() -> str:
    while True:
        raw = input("Provider linking mode? [1=Prefer default provider, 2=Only link default provider]: ").strip().lower()
        if raw in {"1", "prefer", "prefer-defaults", "p", "yes", "y"}:
            return "prefer-defaults"
        if raw in {"2", "only", "only-defaults", "o", "no", "n"}:
            return "only-defaults"
        print("Please choose 1 (Prefer default provider) or 2 (Only link default provider).")


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
        print(
            "Updated parameter 'product_systems_prefer_defaults': "
            f"{new_values}"
        )
        if not args.process_names and not args.interactive:
            return 0

    process_names = _parse_csv_names(args.process_names)
    mode = str(args.provider_linking or "").strip().lower()
    if args.interactive:
        interactive_names, interactive_mode = _interactive_inputs()
        if interactive_names:
            process_names = interactive_names
        if interactive_mode:
            mode = interactive_mode

    client = ipc.Client(8080)

    if not process_names:
        process_names = _prompt_process_inputs(client)
        if not process_names:
            print("No process names were provided.")
            return 1
        if mode in {"", "parameter"}:
            mode = _prompt_linking_choice()

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
    )

    created = sum(1 for r in reports if r.created)
    updated = sum(1 for r in reports if r.updated)
    skipped = sum(1 for r in reports if r.skipped)
    errors = sum(len(r.errors) for r in reports)
    print(
        "Product system builder complete. "
        f"Created: {created}. Updated: {updated}. Skipped: {skipped}. Errors: {errors}."
    )
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(_run_cli())
