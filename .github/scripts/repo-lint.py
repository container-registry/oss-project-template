#!/usr/bin/env python3
"""Repository consistency checks.

Every check here exists because the corresponding mistake actually shipped in
this template at some point. They are cheap, dependency-free, and run both in
CI (hygiene.yml) and locally (`task lint:repo`).

A project that adopts the template can delete any individual check function and
its entry in CHECKS; nothing else depends on them.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Files that legitimately still contain {{PLACEHOLDER}} markers after adoption,
# because they document the placeholder mechanism itself.
PLACEHOLDER_DOCS = {"README.md", "CHECKLIST.md", "docs/ADOPTION.md"}

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
SKIP_DIRS = {".git", "node_modules", "dist", "bin", ".task", "vendor"}
KNOWN_SUFFIXES = {".md", ".yml", ".yaml", ".json", ".toml", ".sh", ".go", ".env",
                  ".txt", ".js", ".py", ".mjs", ".cfg", ".ini"}


def _files(*suffixes: str):
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        if suffixes and path.suffix not in suffixes:
            continue
        yield path


def _rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


def check_yaml_loads(errors: list[str]) -> None:
    """Every YAML file must fully construct, not merely tokenize.

    yamllint parses the event stream and accepts things PyYAML cannot build.
    An unquoted `url: {{DOCS_URL}}` is a flow mapping used as a mapping key:
    it lints clean and GitHub then rejects the file.
    """
    try:
        import yaml
    except ImportError:
        errors.append("PyYAML is not installed; cannot verify YAML files")
        return

    for path in _files(".yml", ".yaml"):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - report whatever the loader raises
            errors.append(f"{_rel(path)}: does not load as YAML: {type(exc).__name__}: {exc}")


def check_json_loads(errors: list[str]) -> None:
    for path in _files(".json"):
        if "lock" in path.name:
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{_rel(path)}: invalid JSON: {exc}")


def check_labeler_labels_declared(errors: list[str]) -> None:
    """Labels applied by the labeler must exist in settings.yml.

    actions/labeler with sync-labels creates missing labels with a random
    colour and no description, so the drift shows up as cosmetic noise rather
    than a failure.
    """
    import yaml

    labeler = ROOT / ".github/labeler.yml"
    settings = ROOT / ".github/settings.yml"
    if not (labeler.exists() and settings.exists()):
        return

    emitted = set(yaml.safe_load(labeler.read_text(encoding="utf-8")) or {})
    declared = set((yaml.safe_load(settings.read_text(encoding="utf-8")) or {}).get("labels") or {})
    for name in sorted(emitted - declared):
        errors.append(f".github/labeler.yml emits label {name!r} which .github/settings.yml does not declare")


def check_release_please_packages_exist(errors: list[str]) -> None:
    """release-please silently tracks package paths that do not exist."""
    config = ROOT / "release-please-config.json"
    manifest = ROOT / ".release-please-manifest.json"
    if not config.exists():
        return

    packages = json.loads(config.read_text(encoding="utf-8")).get("packages") or {}
    for pkg in packages:
        if not (ROOT / pkg).is_dir():
            errors.append(f"release-please-config.json tracks package {pkg!r}, which is not a directory")

    if manifest.exists():
        tracked = set(json.loads(manifest.read_text(encoding="utf-8")))
        for pkg in sorted(tracked - set(packages)):
            errors.append(f".release-please-manifest.json pins {pkg!r}, which release-please-config.json does not track")
        for pkg in sorted(set(packages) - tracked):
            errors.append(f"release-please-config.json tracks {pkg!r}, which .release-please-manifest.json does not pin")


def check_version_file_matches_manifest(errors: list[str]) -> None:
    """With release-type `simple`, version.txt and the manifest must agree."""
    config = ROOT / "release-please-config.json"
    manifest = ROOT / ".release-please-manifest.json"
    version = ROOT / "version.txt"
    if not (config.exists() and manifest.exists() and version.exists()):
        return
    if json.loads(config.read_text(encoding="utf-8")).get("release-type") != "simple":
        return

    pinned = json.loads(manifest.read_text(encoding="utf-8")).get(".")
    actual = version.read_text(encoding="utf-8").strip()
    if pinned != actual:
        errors.append(f"version.txt is {actual!r} but .release-please-manifest.json pins {pinned!r}")


def check_referenced_paths_exist(errors: list[str]) -> None:
    """Markdown must not advertise files the repository does not ship.

    Only two contexts are treated as a claim that a file exists: a relative
    markdown link, and a backticked path inside a table row. Prose such as
    "consider adding `.github/FUNDING.yml`" is intentionally ignored, because
    listing an optional extra is not the same as promising it is there.
    """
    link = re.compile(r"\]\(([^)#:]+?)\)")
    cell = re.compile(r"`([^`\s]+?\.[A-Za-z0-9]+)`")
    owned = {".github", "docs", "scripts", "packs", "optional", "taskfile", "test", "tests"}

    def flag(path: pathlib.Path, ref: str) -> None:
        ref = ref.strip()
        if ref.startswith("./"):
            ref = ref[2:]
        if not ref or ref.startswith(("http", "mailto", "#", "/")):
            return
        if pathlib.PurePath(ref).suffix not in KNOWN_SUFFIXES:
            return
        if (ROOT / ref).exists():
            return
        errors.append(f"{_rel(path)}: references {ref!r}, which does not exist")

    for path in _files(".md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            # A markdown link is unambiguous: it resolves relative to the file.
            for match in link.finditer(line):
                flag(path, match.group(1))
            # In a table, only a ref carrying a directory is a claim about a
            # concrete path. A bare `config.yml` is relative to whatever the
            # surrounding section heading was.
            if line.lstrip().startswith("|"):
                for match in cell.finditer(line):
                    if "/" in match.group(1) and match.group(1).split("/", 1)[0] in owned:
                        flag(path, match.group(1))


def check_no_unreplaced_placeholders(errors: list[str]) -> None:
    """After `task bootstrap` no placeholder may survive outside the docs.

    In the template repository itself every file still holds placeholders, so
    the check is a no-op until the marker file is gone.
    """
    if (ROOT / "CHECKLIST.md").exists():
        return  # still the unadopted template

    for path in _files(".md", ".yml", ".yaml", ".json", ".toml", ".txt", ".env"):
        rel = _rel(path)
        if rel in PLACEHOLDER_DOCS:
            continue
        found = sorted(set(PLACEHOLDER_RE.findall(path.read_text(encoding="utf-8"))))
        if found:
            errors.append(f"{rel}: unreplaced placeholder(s): {', '.join(found)}")


CHECKS = (
    check_yaml_loads,
    check_json_loads,
    check_labeler_labels_declared,
    check_release_please_packages_exist,
    check_version_file_matches_manifest,
    check_referenced_paths_exist,
    check_no_unreplaced_placeholders,
)


def main() -> int:
    errors: list[str] = []
    for check in CHECKS:
        try:
            check(errors)
        except Exception as exc:  # noqa: BLE001 - a broken check must not pass silently
            errors.append(f"{check.__name__} raised {type(exc).__name__}: {exc}")

    if errors:
        print(f"repo-lint: {len(errors)} problem(s)\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"repo-lint: {len(CHECKS)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
