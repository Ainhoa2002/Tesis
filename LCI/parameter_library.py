import argparse
import json
from pathlib import Path
from threading import RLock
from typing import Any, Dict


PARAMETER_FILE = Path(__file__).resolve().with_name("global_parameters.json")
_LOCK = RLock()


def _default_document() -> Dict[str, Any]:
    return {
        "version": 1,
        "execution": {
            "run_scope": "all",
            "target_system": "",
        },
        "parameters": {},
    }


def _ensure_file_exists() -> None:
    if PARAMETER_FILE.exists():
        return
    with open(PARAMETER_FILE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(_default_document(), f, indent=2, ensure_ascii=True)
        f.write("\n")


def load_document() -> Dict[str, Any]:
    with _LOCK:
        _ensure_file_exists()
        with open(PARAMETER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_document()
        data.setdefault("version", 1)
        data.setdefault("execution", {})
        data.setdefault("parameters", {})
        return data


def save_document(doc: Dict[str, Any]) -> None:
    payload = {
        "version": int(doc.get("version", 1)),
        "execution": dict(doc.get("execution", {})),
        "parameters": dict(doc.get("parameters", {})),
    }
    with _LOCK:
        with open(PARAMETER_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, indent=2, ensure_ascii=True)
            f.write("\n")


def get_param(name: str, default: Any = None, required: bool = False) -> Any:
    params = load_document().get("parameters", {})
    if name in params:
        return params[name]
    if required:
        raise KeyError(f"Parameter '{name}' does not exist")
    return default


def set_param(name: str, value: Any) -> None:
    doc = load_document()
    doc["parameters"][name] = value
    save_document(doc)


def delete_param(name: str) -> bool:
    doc = load_document()
    if name not in doc["parameters"]:
        return False
    del doc["parameters"][name]
    save_document(doc)
    return True


def list_params() -> Dict[str, Any]:
    return dict(load_document().get("parameters", {}))


def set_execution_scope(run_scope: str = "all", target_system: str = "") -> None:
    scope = (run_scope or "all").strip().lower()
    if scope not in {"all", "single"}:
        raise ValueError("run_scope must be 'all' or 'single'")
    doc = load_document()
    doc["execution"] = {
        "run_scope": scope,
        "target_system": str(target_system or "").strip(),
    }
    save_document(doc)


def get_execution_scope() -> Dict[str, str]:
    execution = load_document().get("execution", {})
    return {
        "run_scope": str(execution.get("run_scope", "all") or "all").strip().lower(),
        "target_system": str(execution.get("target_system", "") or "").strip(),
    }


def _parse_value(raw: str) -> Any:
    text = str(raw)
    lowered = text.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LCI global parameter library")
    sub = parser.add_subparsers(dest="command", required=True)

    set_cmd = sub.add_parser("set")
    set_cmd.add_argument("name")
    set_cmd.add_argument("value")

    get_cmd = sub.add_parser("get")
    get_cmd.add_argument("name")
    get_cmd.add_argument("--default", default="")

    sub.add_parser("list")

    del_cmd = sub.add_parser("delete")
    del_cmd.add_argument("name")

    scope_cmd = sub.add_parser("scope")
    scope_cmd.add_argument("run_scope", choices=["all", "single"])
    scope_cmd.add_argument("--target-system", default="")

    sub.add_parser("show-scope")
    return parser


def _run_cli() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "set":
        set_param(args.name, _parse_value(args.value))
        print(f"Set {args.name}")
        return 0

    if args.command == "get":
        print(get_param(args.name, default=args.default))
        return 0

    if args.command == "list":
        print(json.dumps(list_params(), indent=2, ensure_ascii=True))
        return 0

    if args.command == "delete":
        print("Deleted" if delete_param(args.name) else "Not found")
        return 0

    if args.command == "scope":
        set_execution_scope(args.run_scope, args.target_system)
        print("Scope updated")
        return 0

    if args.command == "show-scope":
        print(json.dumps(get_execution_scope(), indent=2, ensure_ascii=True))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())import argparse
import json
from pathlib import Path
from threading import RLock
from typing import Any, Dict


PARAMETER_FILE = Path(__file__).resolve().with_name("global_parameters.json")
_LOCK = RLock()


def _default_document() -> Dict[str, Any]:
    return {
        "version": 1,
        "execution": {
            "run_scope": "all",
            "target_system": "",
        },
        "parameters": {},
    }


def _ensure_file_exists() -> None:
    if PARAMETER_FILE.exists():
        return

    PARAMETER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PARAMETER_FILE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(_default_document(), f, indent=2, ensure_ascii=True)
        f.write("\n")


def load_document() -> Dict[str, Any]:
    with _LOCK:
        _ensure_file_exists()
        with open(PARAMETER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = _default_document()

        data.setdefault("version", 1)
        data.setdefault("execution", {})
        data.setdefault("parameters", {})
        return data


def save_document(doc: Dict[str, Any]) -> None:
    with _LOCK:
        payload = {
            "version": int(doc.get("version", 1)),
            "execution": dict(doc.get("execution", {})),
            "parameters": dict(doc.get("parameters", {})),
        }

        with open(PARAMETER_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, indent=2, ensure_ascii=True)
            f.write("\n")


def get_param(name: str, default: Any = None, required: bool = False) -> Any:
    params = load_document().get("parameters", {})
    if name in params:
        return params[name]
    if required:
        raise KeyError(f"Parameter '{name}' does not exist.")
    return default


def set_param(name: str, value: Any) -> None:
    doc = load_document()
    doc["parameters"][name] = value
    save_document(doc)


def delete_param(name: str) -> bool:
    doc = load_document()
    if name not in doc["parameters"]:
        return False
    del doc["parameters"][name]
    save_document(doc)
    return True


def list_params() -> Dict[str, Any]:
    return dict(load_document().get("parameters", {}))


def set_execution_scope(run_scope: str = "all", target_system: str = "") -> None:
    scope = (run_scope or "all").strip().lower()
    if scope not in {"all", "single"}:
        raise ValueError("run_scope must be 'all' or 'single'.")

    doc = load_document()
    doc["execution"] = {
        "run_scope": scope,
        "target_system": str(target_system or "").strip(),
    }
    save_document(doc)


def get_execution_scope() -> Dict[str, str]:
    execution = load_document().get("execution", {})
    run_scope = str(execution.get("run_scope", "all") or "all").strip().lower()
    target_system = str(execution.get("target_system", "") or "").strip()
    return {
        "run_scope": run_scope,
        "target_system": target_system,
    }


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Global parameter library for the LCI workspace.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_cmd = subparsers.add_parser("set", help="Set one parameter")
    set_cmd.add_argument("name")
    set_cmd.add_argument("value")

    get_cmd = subparsers.add_parser("get", help="Get one parameter")
    get_cmd.add_argument("name")
    get_cmd.add_argument("--default", default="")

    subparsers.add_parser("list", help="List all parameters")

    delete_cmd = subparsers.add_parser("delete", help="Delete one parameter")
    delete_cmd.add_argument("name")

    scope_cmd = subparsers.add_parser("scope", help="Set execution scope")
    scope_cmd.add_argument("run_scope", choices=["all", "single"])
    scope_cmd.add_argument("--target-system", default="")

    subparsers.add_parser("show-scope", help="Show execution scope")
    return parser


def _parse_value(raw: str) -> Any:
    text = str(raw)
    lowered = text.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"

    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        pass

    return text


def _run_cli() -> int:
    parser = _build_cli_parser()
    args = parser.parse_args()

    if args.command == "set":
        set_param(args.name, _parse_value(args.value))
        print(f"Set parameter: {args.name}")
        return 0

    if args.command == "get":
        value = get_param(args.name, default=args.default)
        print(value)
        return 0

    if args.command == "list":
        print(json.dumps(list_params(), indent=2, ensure_ascii=True))
        return 0

    if args.command == "delete":
        deleted = delete_param(args.name)
        print("Deleted" if deleted else "Not found")
        return 0

    if args.command == "scope":
        set_execution_scope(args.run_scope, args.target_system)
        print("Execution scope updated")
        return 0

    if args.command == "show-scope":
        print(json.dumps(get_execution_scope(), indent=2, ensure_ascii=True))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())