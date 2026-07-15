#!/usr/bin/env python3
"""Safely update JSON files in UTF-8 environments, especially Windows/PowerShell.

Typical use cases:
- write long Chinese evidence text from a file into a JSON string field
- append structured attempt/evidence objects into list fields
- update dynamic-state.json with file locking and atomic writes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _utf8 import configure_utf8_runtime, find_text_quality_issues  # type: ignore
except Exception as exc:  # pragma: no cover - bootstrap failure is fatal
    raise SystemExit(f"[ERROR] failed to load UTF-8 helpers: {exc}") from exc


configure_utf8_runtime()

try:
    from jsonschema import Draft7Validator

    HAS_JSONSCHEMA = True
except Exception:
    HAS_JSONSCHEMA = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely update JSON files with UTF-8, atomic write, and optional file lock.",
    )
    parser.add_argument("--file", required=True, help="Target JSON file path.")
    parser.add_argument("--schema", help="Optional JSON schema path for post-write validation.")
    parser.add_argument("--lock", action="store_true", help="Use a sidecar lock file during read-modify-write.")
    parser.add_argument(
        "--check-text-quality",
        action="store_true",
        help="Run UTF-8 placeholder/garbage text checks after update.",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="PATH=TEXT",
        help="Set a JSON path to a plain string value.",
    )
    parser.add_argument(
        "--set-file",
        action="append",
        default=[],
        metavar="PATH=FILE",
        help="Set a JSON path to text loaded from a UTF-8 file. Use '-' to read stdin.",
    )
    parser.add_argument(
        "--set-json",
        action="append",
        default=[],
        metavar="PATH=JSON",
        help="Set a JSON path to a JSON literal/object/array.",
    )
    parser.add_argument(
        "--set-json-file",
        action="append",
        default=[],
        metavar="PATH=FILE",
        help="Set a JSON path to JSON loaded from a file. Use '-' to read stdin.",
    )
    parser.add_argument(
        "--append",
        action="append",
        default=[],
        metavar="PATH=TEXT",
        help="Append a plain string value to a list field.",
    )
    parser.add_argument(
        "--append-file",
        action="append",
        default=[],
        metavar="PATH=FILE",
        help="Append UTF-8 text loaded from a file to a list field. Use '-' to read stdin.",
    )
    parser.add_argument(
        "--append-json",
        action="append",
        default=[],
        metavar="PATH=JSON",
        help="Append a JSON literal/object/array to a list field.",
    )
    parser.add_argument(
        "--append-json-file",
        action="append",
        default=[],
        metavar="PATH=FILE",
        help="Append JSON loaded from a file to a list field. Use '-' to read stdin.",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print a concise JSON summary of applied updates.",
    )
    args = parser.parse_args()
    if not any(
        (
            args.set,
            args.set_file,
            args.set_json,
            args.set_json_file,
            args.append,
            args.append_file,
            args.append_json,
            args.append_json_file,
        )
    ):
        parser.error("at least one update operation is required")
    return args


def read_text_file(path_value: str) -> str:
    if path_value == "-":
        text = sys.stdin.read()
    else:
        text = Path(path_value).read_text(encoding="utf-8-sig", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def read_json_file(path_value: str) -> Any:
    return json.loads(read_text_file(path_value))


def split_assignment(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise SystemExit(f"[ERROR] invalid assignment, expected PATH=VALUE: {raw}")
    path, value = raw.split("=", 1)
    path = path.strip()
    if not path:
        raise SystemExit(f"[ERROR] empty JSON path in assignment: {raw}")
    return path, value


def parse_path(raw: str) -> list[str | int]:
    path = raw.strip()
    if not path:
        raise SystemExit("[ERROR] JSON path cannot be empty")
    tokens: list[str | int] = []
    i = 0
    while i < len(path):
        if path[i] == ".":
            i += 1
            continue
        if path[i] == "[":
            end = path.find("]", i)
            if end == -1:
                raise SystemExit(f"[ERROR] unmatched '[' in path: {raw}")
            index_text = path[i + 1:end].strip()
            if not index_text.isdigit():
                raise SystemExit(f"[ERROR] list index must be a non-negative integer: {raw}")
            tokens.append(int(index_text))
            i = end + 1
            continue
        start = i
        while i < len(path) and path[i] not in ".[":
            i += 1
        key = path[start:i].strip()
        if not key:
            raise SystemExit(f"[ERROR] empty object key in path: {raw}")
        tokens.append(key)
    return tokens


def ensure_container(parent: Any, token: str | int, next_token: str | int | None) -> Any:
    expected_list = isinstance(next_token, int)
    expected_type = list if expected_list else dict
    expected_name = "list" if expected_list else "object"

    if isinstance(token, str):
        if not isinstance(parent, dict):
            raise SystemExit(f"[ERROR] cannot traverse key '{token}' on non-object container")
        current = parent.get(token)
        if current is None:
            current = [] if expected_list else {}
            parent[token] = current
        elif not isinstance(current, expected_type):
            raise SystemExit(
                f"[ERROR] path segment '{token}' expects {expected_name}, got {type(current).__name__}",
            )
        return current

    if not isinstance(parent, list):
        raise SystemExit(f"[ERROR] cannot traverse index [{token}] on non-list container")
    while len(parent) <= token:
        parent.append(None)
    current = parent[token]
    if current is None:
        current = [] if expected_list else {}
        parent[token] = current
    elif not isinstance(current, expected_type):
        raise SystemExit(
            f"[ERROR] path segment [{token}] expects {expected_name}, got {type(current).__name__}",
        )
    return current


def navigate_to_parent(data: Any, tokens: list[str | int]) -> tuple[Any, str | int]:
    if not tokens:
        raise SystemExit("[ERROR] JSON path cannot be empty")
    if len(tokens) == 1:
        return data, tokens[0]

    current = data
    for index, token in enumerate(tokens[:-1]):
        next_token = tokens[index + 1]
        current = ensure_container(current, token, next_token)
    return current, tokens[-1]


def set_at_path(data: Any, path: str, value: Any) -> None:
    tokens = parse_path(path)
    parent, last = navigate_to_parent(data, tokens)
    if isinstance(last, str):
        if not isinstance(parent, dict):
            raise SystemExit(f"[ERROR] final path segment '{last}' requires object parent")
        parent[last] = value
        return
    if not isinstance(parent, list):
        raise SystemExit(f"[ERROR] final path segment [{last}] requires list parent")
    while len(parent) <= last:
        parent.append(None)
    parent[last] = value


def append_at_path(data: Any, path: str, value: Any) -> None:
    tokens = parse_path(path)
    parent, last = navigate_to_parent(data, tokens)
    if isinstance(last, str):
        if not isinstance(parent, dict):
            raise SystemExit(f"[ERROR] append target '{last}' requires object parent")
        current = parent.get(last)
        if current is None:
            current = []
            parent[last] = current
        elif not isinstance(current, list):
            raise SystemExit(f"[ERROR] append target '{last}' is not a list")
        current.append(value)
        return
    if not isinstance(parent, list):
        raise SystemExit(f"[ERROR] append target [{last}] requires list parent")
    while len(parent) <= last:
        parent.append(None)
    current = parent[last]
    if current is None:
        current = []
        parent[last] = current
    elif not isinstance(current, list):
        raise SystemExit(f"[ERROR] append target [{last}] is not a list")
    current.append(value)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except FileNotFoundError as exc:
        raise SystemExit(f"[ERROR] target JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[ERROR] target JSON is invalid before update: {path}: {exc}") from exc


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


@contextmanager
def optional_lock(path: Path, enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return

    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+", encoding="utf-8")
    try:
        handle.seek(0)
        if handle.tell() == 0:
            handle.write("0")
            handle.flush()
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def validate_schema(data: Any, schema_path: Path) -> None:
    if not HAS_JSONSCHEMA:
        raise SystemExit("[ERROR] --schema requires jsonschema to be installed")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8-sig", errors="replace"))
    except FileNotFoundError as exc:
        raise SystemExit(f"[ERROR] schema file not found: {schema_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[ERROR] schema file is invalid JSON: {schema_path}: {exc}") from exc
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "(root)"
        raise SystemExit(f"[ERROR] schema validation failed at {location}: {first.message}")


def apply_updates(data: Any, args: argparse.Namespace) -> list[dict[str, str]]:
    summary: list[dict[str, str]] = []
    for raw in args.set:
        path, value = split_assignment(raw)
        set_at_path(data, path, value)
        summary.append({"op": "set", "path": path, "source": "inline-text"})
    for raw in args.set_file:
        path, value_file = split_assignment(raw)
        set_at_path(data, path, read_text_file(value_file))
        summary.append({"op": "set", "path": path, "source": value_file})
    for raw in args.set_json:
        path, value = split_assignment(raw)
        set_at_path(data, path, json.loads(value))
        summary.append({"op": "set-json", "path": path, "source": "inline-json"})
    for raw in args.set_json_file:
        path, value_file = split_assignment(raw)
        set_at_path(data, path, read_json_file(value_file))
        summary.append({"op": "set-json", "path": path, "source": value_file})
    for raw in args.append:
        path, value = split_assignment(raw)
        append_at_path(data, path, value)
        summary.append({"op": "append", "path": path, "source": "inline-text"})
    for raw in args.append_file:
        path, value_file = split_assignment(raw)
        append_at_path(data, path, read_text_file(value_file))
        summary.append({"op": "append", "path": path, "source": value_file})
    for raw in args.append_json:
        path, value = split_assignment(raw)
        append_at_path(data, path, json.loads(value))
        summary.append({"op": "append-json", "path": path, "source": "inline-json"})
    for raw in args.append_json_file:
        path, value_file = split_assignment(raw)
        append_at_path(data, path, read_json_file(value_file))
        summary.append({"op": "append-json", "path": path, "source": value_file})
    return summary


def main() -> int:
    args = parse_args()
    target = Path(args.file).resolve()

    with optional_lock(target, args.lock):
        data = load_json(target)
        if not isinstance(data, (dict, list)):
            raise SystemExit("[ERROR] target JSON root must be an object or array")
        summary = apply_updates(data, args)
        atomic_write_json(target, data)
        updated = load_json(target)

    if args.schema:
        validate_schema(updated, Path(args.schema).resolve())
    if args.check_text_quality:
        issues = find_text_quality_issues(updated)
        if issues:
            first = issues[0]
            raise SystemExit(
                f"[ERROR] text quality check failed at {first['path']}: "
                f"{first['message']} ({first['hint']})",
            )
    if args.print_summary:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "file": str(target),
                    "updates": summary,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    else:
        print(f"[OK] updated {target} with {len(summary)} change(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
