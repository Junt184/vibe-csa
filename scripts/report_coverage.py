#!/usr/bin/env python3
"""Compute report-side reviewed_files and EALOC from final findings JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any


SOURCE_SUFFIXES = {
    ".php",
    ".phtml",
    ".inc",
    ".py",
    ".java",
    ".go",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}

REVIEWABLE_SUFFIXES = SOURCE_SUFFIXES | {
    ".bak",
    ".conf",
    ".config",
    ".cfg",
    ".cnf",
    ".env",
    ".ini",
    ".json",
    ".properties",
    ".xml",
    ".yaml",
    ".yml",
}

IGNORED_DIR_NAMES = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    "node_modules",
    "vendor",
    "workDir",
    "Runtime",
    "Public",
    "dist",
    "build",
    "coverage",
}

IGNORED_PATH_PARTS = {
    ("ThinkPHP", "Library", "Vendor"),
}


def _normalize_relative_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.strip("/")


def _resolve_source_root(data: dict[str, Any], base_dir: str | Path | None) -> Path | None:
    source_path = (
        ((data.get("audit") or {}).get("target") or {}).get("source_path") or ""
    )
    if source_path:
        candidate = Path(str(source_path)).expanduser()
        if not candidate.is_absolute() and base_dir:
            candidate = Path(base_dir) / candidate
        candidate = candidate.resolve()
        if candidate.exists():
            return candidate

    if base_dir:
        candidate = Path(base_dir).resolve()
        if candidate.exists():
            return candidate
    return None


def _has_ignored_path_parts(parts: tuple[str, ...]) -> bool:
    lower_parts = {part.lower() for part in parts}
    if any(name.lower() in lower_parts for name in IGNORED_DIR_NAMES):
        return True
    for ignored in IGNORED_PATH_PARTS:
        if len(parts) < len(ignored):
            continue
        for idx in range(len(parts) - len(ignored) + 1):
            window = parts[idx : idx + len(ignored)]
            if tuple(part.lower() for part in window) == tuple(part.lower() for part in ignored):
                return True
    return False


def _is_candidate_reviewed_file(rel_path: str) -> bool:
    path = Path(rel_path)
    if path.suffix.lower() not in REVIEWABLE_SUFFIXES:
        return False
    return not _has_ignored_path_parts(path.parts)


def _is_candidate_source_file(rel_path: str) -> bool:
    path = Path(rel_path)
    if path.suffix.lower() not in SOURCE_SUFFIXES:
        return False
    return not _has_ignored_path_parts(path.parts)


def _iter_candidate_files(findings: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    files: list[str] = []
    for finding in findings:
        static = (finding.get("static_evidence") or {})
        for item in static.get("reviewed_files") or []:
            rel = _normalize_relative_path((item or {}).get("file"))
            if rel and rel not in seen and _is_candidate_reviewed_file(rel):
                seen.add(rel)
                files.append(rel)

        rel = _normalize_relative_path((finding.get("location") or {}).get("file"))
        if rel and rel not in seen and _is_candidate_reviewed_file(rel):
            seen.add(rel)
            files.append(rel)
    return files


def _resolve_existing_file(source_root: Path | None, rel_path: str) -> Path | None:
    candidate = Path(rel_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        return resolved if resolved.exists() else None

    if source_root is None:
        return None

    resolved = (source_root / rel_path).resolve()
    if not resolved.exists() or not resolved.is_file():
        return None

    try:
        resolved.relative_to(source_root)
    except ValueError:
        return None
    return resolved


def _strip_c_style_comments(line: str, in_block: bool) -> tuple[str, bool]:
    out: list[str] = []
    i = 0
    length = len(line)
    while i < length:
        if in_block:
            end = line.find("*/", i)
            if end == -1:
                return "".join(out), True
            i = end + 2
            in_block = False
            continue

        if line.startswith("/*", i):
            in_block = True
            i += 2
            continue

        out.append(line[i])
        i += 1
    return "".join(out), in_block


def _count_effective_loc(file_path: Path) -> int:
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = file_path.read_text(encoding="utf-8", errors="ignore")

    suffix = file_path.suffix.lower()
    in_block_comment = False
    in_py_triple_single = False
    in_py_triple_double = False
    count = 0

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if suffix == ".py":
            if in_py_triple_single:
                if "'''" in stripped:
                    in_py_triple_single = False
                continue
            if in_py_triple_double:
                if '"""' in stripped:
                    in_py_triple_double = False
                continue
            if stripped.startswith("'''"):
                if stripped.count("'''") < 2:
                    in_py_triple_single = True
                continue
            if stripped.startswith('"""'):
                if stripped.count('"""') < 2:
                    in_py_triple_double = True
                continue
            if stripped.startswith("#"):
                continue
            count += 1
            continue

        cleaned, in_block_comment = _strip_c_style_comments(line, in_block_comment)
        stripped = cleaned.strip()
        if not stripped:
            continue
        if stripped.startswith("//") or stripped.startswith("#"):
            continue
        count += 1

    return count


def compute_report_coverage(data: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, int]:
    findings = [item for item in (data.get("findings") or []) if isinstance(item, dict)]
    source_root = _resolve_source_root(data, base_dir)
    candidate_files = _iter_candidate_files(findings)

    existing_files: list[Path] = []
    seen_paths: set[Path] = set()
    for rel_path in candidate_files:
        resolved = _resolve_existing_file(source_root, rel_path)
        if resolved and resolved not in seen_paths:
            seen_paths.add(resolved)
            existing_files.append(resolved)

    source_files = [
        path for path in existing_files
        if _is_candidate_source_file(str(path.relative_to(source_root)).replace("\\", "/"))
    ] if source_root else []

    return {
        "reviewed_files": len(existing_files),
        "ealoc": sum(_count_effective_loc(path) for path in source_files),
    }


def apply_report_coverage(data: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, int]:
    coverage = compute_report_coverage(data, base_dir=base_dir)
    audit = data.setdefault("audit", {})
    summary = audit.setdefault("coverage_summary", {})
    summary["reviewed_files"] = coverage["reviewed_files"]
    summary["ealoc"] = coverage["ealoc"]
    return coverage
