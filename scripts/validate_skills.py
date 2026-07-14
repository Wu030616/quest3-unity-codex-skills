#!/usr/bin/env python3
"""Validate repository structure without third-party dependencies."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_FIELD_RE = re.compile(r"^([a-z][a-z0-9-]*):(?:\s*(.*))?$")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
REQUIRED_ROOT_FILES = {
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_NOTICES.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
}
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
}
PERSONAL_PATH_PATTERNS = {
    "mac_user_path": re.compile(r"/Users/[^/\s]+/"),
    "windows_user_path": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
}


def extract_frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}, [f"{path.relative_to(ROOT)}: missing opening frontmatter delimiter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, [f"{path.relative_to(ROOT)}: missing closing frontmatter delimiter"]

    fields: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:end], start=2):
        if not line or line[0].isspace():
            continue
        match = TOP_LEVEL_FIELD_RE.fullmatch(line)
        if not match:
            errors.append(f"{path.relative_to(ROOT)}:{line_number}: invalid top-level YAML field")
            continue
        key, value = match.groups()
        if key in fields:
            errors.append(f"{path.relative_to(ROOT)}:{line_number}: duplicate field {key}")
        fields[key] = (value or "").strip().strip('"').strip("'")
    return fields, errors


def validate_relative_links(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for target in MARKDOWN_LINK_RE.findall(text):
        target = target.strip().strip("<>")
        if not target or target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        relative_target = target.split("#", 1)[0]
        if relative_target and not (path.parent / relative_target).exists():
            errors.append(
                f"{path.relative_to(ROOT)}: broken relative link {relative_target}"
            )
    return errors


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"{skill_dir.relative_to(ROOT)}: missing SKILL.md"]

    fields, field_errors = extract_frontmatter(skill_file)
    errors.extend(field_errors)
    unknown = sorted(set(fields) - ALLOWED_FIELDS)
    if unknown:
        errors.append(f"{skill_file.relative_to(ROOT)}: unsupported fields {unknown}")

    name = fields.get("name", "")
    description = fields.get("description", "")
    compatibility = fields.get("compatibility", "")
    if not NAME_RE.fullmatch(name):
        errors.append(f"{skill_file.relative_to(ROOT)}: invalid skill name {name!r}")
    if name != skill_dir.name:
        errors.append(
            f"{skill_file.relative_to(ROOT)}: name {name!r} does not match directory"
        )
    if not 1 <= len(description) <= 1024:
        errors.append(f"{skill_file.relative_to(ROOT)}: description must be 1-1024 characters")
    if len(compatibility) > 500:
        errors.append(f"{skill_file.relative_to(ROOT)}: compatibility exceeds 500 characters")
    if fields.get("license") != "Apache-2.0":
        errors.append(f"{skill_file.relative_to(ROOT)}: license must be Apache-2.0")
    if len(skill_file.read_text(encoding="utf-8").splitlines()) > 500:
        errors.append(f"{skill_file.relative_to(ROOT)}: SKILL.md exceeds 500 lines")
    if not (skill_dir / "SOURCE.md").is_file():
        errors.append(f"{skill_dir.relative_to(ROOT)}: missing SOURCE.md")

    for markdown in sorted(skill_dir.rglob("*.md")):
        errors.extend(validate_relative_links(markdown))
    return errors


def validate_sensitive_text() -> list[str]:
    errors: list[str] = []
    candidates = list(SKILLS_ROOT.rglob("*"))
    candidates.extend(ROOT / name for name in REQUIRED_ROOT_FILES if (ROOT / name).is_file())
    for path in sorted({path for path in candidates if path.is_file()}):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in {**SECRET_PATTERNS, **PERSONAL_PATH_PATTERNS}.items():
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT)}: possible {label}")
    return errors


def main() -> int:
    errors: list[str] = []
    missing = sorted(name for name in REQUIRED_ROOT_FILES if not (ROOT / name).is_file())
    if missing:
        errors.append(f"missing root files: {missing}")
    if not SKILLS_ROOT.is_dir():
        errors.append("missing skills directory")
        skill_dirs: list[Path] = []
    else:
        skill_dirs = sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())
    if not skill_dirs:
        errors.append("no skill directories found")
    for skill_dir in skill_dirs:
        errors.extend(validate_skill(skill_dir))
    errors.extend(validate_sensitive_text())

    result = {
        "ok": not errors,
        "skills": [path.name for path in skill_dirs],
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
