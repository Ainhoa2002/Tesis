import argparse
import socket
from pathlib import Path
import logging

import olca_ipc as ipc
import olca_schema as o


BASE_DIR = Path(__file__).resolve().parent
MAX_SELECTION_ATTEMPTS = 3


def iter_system_folders(base_dir: Path):
    for child in sorted(base_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == "__pycache__":
            continue
        yield child


def resolve_category_name(folder_name: str) -> str:
    if folder_name.startswith("LCI_") and len(folder_name) > 4:
        return folder_name[4:]
    return folder_name


def ensure_ipc_server_available(host: str = "localhost", port: int = 8080, timeout_seconds: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _normalize_key(value: str) -> str:
    return "".join(str(value or "").strip().lower().split())


def discover_default_categories() -> set[str]:
    return {
        resolve_category_name(folder.name)
        for folder in iter_system_folders(BASE_DIR)
    }


def collect_candidate_processes(client: ipc.Client, allowed_categories: set[str]) -> list[o.Ref]:
    refs = list(client.get_descriptors(o.Process) or [])
    selected = []
    for ref in refs:
        category = str(getattr(ref, "category", "") or "")
        if category in allowed_categories:
            selected.append(ref)
            continue
        for allowed in allowed_categories:
            if category.startswith(allowed + "/"):
                selected.append(ref)
                break

    selected.sort(key=lambda r: (str(getattr(r, "category", "") or ""), str(getattr(r, "name", "") or "").lower()))
    return selected


def _parse_selection(raw: str, candidates: list[o.Ref]) -> list[o.Ref]:
    text = str(raw or "").strip()
    if text == "":
        raise ValueError("Selection is empty")

    tokens = [t.strip() for t in text.replace(",", " ").split() if t.strip()]
    if not tokens:
        raise ValueError("Selection is empty")

    by_index = {str(i): ref for i, ref in enumerate(candidates, start=1)}
    by_name = {_normalize_key(ref.name): ref for ref in candidates}

    picked = []
    seen = set()
    for token in tokens:
        token_key = _normalize_key(token)
        if token_key in {"all", "*", "0"}:
            return candidates

        ref = by_index.get(token)
        if ref is None:
            ref = by_name.get(token_key)

        if ref is None:
            raise ValueError(f"Unknown selection token: {token}")

        if ref.id not in seen:
            seen.add(ref.id)
            picked.append(ref)

    return picked


def choose_processes_interactive(candidates: list[o.Ref]) -> list[o.Ref]:
    if not candidates:
        return []

    print("Available processes:")
    print("  0. ALL")
    for i, ref in enumerate(candidates, start=1):
        category = str(getattr(ref, "category", "") or "")
        print(f"  {i}. {ref.name} [{category}]")

    attempts = 0
    while attempts < MAX_SELECTION_ATTEMPTS:
        raw = input("Choose process number/name (multiple allowed, e.g. '1 2' or 'all'): ").strip()
        try:
            return _parse_selection(raw, candidates)
        except ValueError as exc:
            attempts += 1
            print(f"Invalid selection: {exc}")

    raise ValueError("Too many invalid attempts. Operation canceled.")


def find_unlinked_input_flow_names(process: o.Process) -> list[str]:
    names = []
    seen = set()
    for ex in list(process.exchanges or []):
        if not ex.is_input:
            continue
        if ex.default_provider is not None:
            continue
        flow = ex.flow
        if not flow:
            continue
        flow_type = getattr(flow, "flow_type", None)
        if flow_type not in (None, o.FlowType.PRODUCT_FLOW, o.FlowType.WASTE_FLOW):
            # Elementary flows are not provider-linked.
            continue
        name = str(getattr(flow, "name", "") or "").strip()
        if not name:
            name = str(getattr(flow, "id", "") or "").strip()
        if not name:
            continue
        key = _normalize_key(name)
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def ask_overwrite(existing_ps: o.Ref) -> bool:
    prompt = (
        f"Product system '{existing_ps.name}' already exists (ID: {existing_ps.id}). "
        "Overwrite it? [y/N]: "
    )
    raw = input(prompt).strip().lower()
    return raw in {"y", "yes", "s", "si"}


def main():
    parser = argparse.ArgumentParser(
        description="Create openLCA product systems from imported LCI processes with selectable linking mode."
    )
    parser.add_argument(
        "--categories",
        default="",
        help="Comma-separated process categories to include (default: all LCI_* folder categories).",
    )
    parser.add_argument(
        "--select",
        default="",
        help="Selection tokens (numbers or exact process names). Use 'all' for all candidates.",
    )
    parser.add_argument(
        "--prefer-system-processes",
        action="store_true",
        help="Prefer system processes instead of unit processes (default prefers unit processes).",
    )
    parser.add_argument(
        "--cutoff",
        type=float,
        default=None,
        help="Optional linking cutoff value for LinkingConfig.",
    )
    parser.add_argument(
        "--overwrite-existing",
        choices=["ask", "yes", "no"],
        default="ask",
        help="Behavior when a product system with the same name already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without creating product systems.",
    )
    args = parser.parse_args()

    if not ensure_ipc_server_available(host="localhost", port=8080):
        logging.error(
            "openLCA IPC server is not reachable on localhost:8080. Start openLCA and enable the IPC server."
        )
        return

    client = ipc.Client(8080)
    logging.info("Connected to openLCA IPC server")

    if args.categories.strip():
        allowed_categories = {
            c.strip() for c in args.categories.split(",") if c.strip()
        }
    else:
        allowed_categories = discover_default_categories()

    candidates = collect_candidate_processes(client, allowed_categories)
    if not candidates:
        logging.warning("No processes found for categories: %s", sorted(allowed_categories))
        return

    if args.select.strip():
        selected = _parse_selection(args.select, candidates)
    else:
        selected = choose_processes_interactive(candidates)

    if not selected:
        logging.info("No processes selected.")
        return

    config = o.LinkingConfig(
        cutoff=args.cutoff,
        prefer_unit_processes=not args.prefer_system_processes,
        provider_linking=o.ProviderLinking.ONLY_DEFAULTS,
    )

    created = 0
    skipped_existing = 0
    failed = 0

    for ref in selected:
        process = client.get(o.Process, uid=ref.id)
        if not process:
            failed += 1
            logging.error("FAILED loading process: %s (ID: %s)", ref.name, ref.id)
            continue

        unlinked_inputs = find_unlinked_input_flow_names(process)

        existing = client.find(o.ProductSystem, name=ref.name)
        overwrite = False
        if existing:
            if args.overwrite_existing == "yes":
                overwrite = True
            elif args.overwrite_existing == "no":
                skipped_existing += 1
                logging.info("SKIP existing product system: %s (ID: %s)", ref.name, existing.id)
                if unlinked_inputs:
                    logging.info("Potentially unlinked inputs (no default provider): %s", ", ".join(unlinked_inputs))
                continue
            else:
                overwrite = ask_overwrite(existing)
                if not overwrite:
                    skipped_existing += 1
                    logging.info("SKIP existing product system: %s (ID: %s)", ref.name, existing.id)
                    if unlinked_inputs:
                        logging.info("Potentially unlinked inputs (no default provider): %s", ", ".join(unlinked_inputs))
                    continue

        if args.dry_run:
            if existing and overwrite:
                logging.info("[DRY-RUN] Would overwrite product system: %s (old ID: %s)", ref.name, existing.id)
            elif existing:
                logging.info("[DRY-RUN] Would skip existing product system: %s (ID: %s)", ref.name, existing.id)
            else:
                logging.info("[DRY-RUN] Would create product system for process: %s", ref.name)
            if unlinked_inputs:
                logging.info("Potentially unlinked inputs (no default provider): %s", ", ".join(unlinked_inputs))
            continue

        try:
            if existing and overwrite:
                existing_entity = client.get(o.ProductSystem, uid=existing.id)
                if existing_entity:
                    client.delete(existing_entity)
                    logging.info("OVERWRITE deleted existing product system: %s (ID: %s)", existing.name, existing.id)

            created_ref = client.create_product_system(process, config)
            if created_ref:
                created += 1
                logging.info("CREATED product system: %s (ID: %s)", created_ref.name, created_ref.id)
                if unlinked_inputs:
                    logging.info("Potentially unlinked inputs (no default provider): %s", ", ".join(unlinked_inputs))
            else:
                failed += 1
                logging.error("FAILED creating product system for process: %s", ref.name)
        except Exception as exc:
            failed += 1
            logging.exception("FAILED creating product system for process '%s': %s", ref.name, exc)

    logging.info("Summary:")
    logging.info("Selected: %s", len(selected))
    logging.info("Created: %s", created)
    logging.info("Skipped existing: %s", skipped_existing)
    logging.info("Failed: %s", failed)


if __name__ == "__main__":
    main()
