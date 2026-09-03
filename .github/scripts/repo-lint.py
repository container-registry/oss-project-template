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
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Files that would legitimately still contain placeholder markers after
# adoption because they document the mechanism itself. Empty on purpose:
# bootstrap deletes CHECKLIST.md, and nothing else explains placeholders in
# prose any more. Add a path here only with a reason.
PLACEHOLDER_DOCS: set[str] = set()

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

    declared = set((yaml.safe_load(settings.read_text(encoding="utf-8")) or {}).get("labels") or {})

    sources = {".github/labeler.yml": set(yaml.safe_load(labeler.read_text(encoding="utf-8")) or {})}

    # Issue forms apply labels on submission and drift from settings.yml the
    # same way the labeler does.
    for form in sorted((ROOT / ".github/ISSUE_TEMPLATE").glob("*.y*ml")):
        if form.name == "config.yml":
            continue
        doc = yaml.safe_load(form.read_text(encoding="utf-8")) or {}
        labels = doc.get("labels") or []
        if isinstance(labels, str):
            labels = [part.strip() for part in labels.split(",")]
        if labels:
            sources[_rel(form)] = set(labels)

    for source, emitted in sources.items():
        for name in sorted(emitted - declared):
            errors.append(f"{source} applies label {name!r} which .github/settings.yml does not declare")


def check_release_please_packages_exist(errors: list[str]) -> None:
    """release-please silently tracks package paths that do not exist."""
    config = ROOT / ".release-please/config-app.json"
    manifest = ROOT / ".release-please/manifest-app.json"
    if not config.exists():
        return

    packages = json.loads(config.read_text(encoding="utf-8")).get("packages") or {}
    for pkg in packages:
        if not (ROOT / pkg).is_dir():
            errors.append(f".release-please/config-app.json tracks package {pkg!r}, which is not a directory")

    if manifest.exists():
        tracked = set(json.loads(manifest.read_text(encoding="utf-8")))
        for pkg in sorted(tracked - set(packages)):
            errors.append(f".release-please/manifest-app.json pins {pkg!r}, which config-app.json does not track")
        for pkg in sorted(set(packages) - tracked):
            errors.append(f".release-please/config-app.json tracks {pkg!r}, which manifest-app.json does not pin")


def check_version_file_matches_manifest(errors: list[str]) -> None:
    """With release-type `simple`, version.txt and the manifest must agree."""
    config = ROOT / ".release-please/config-app.json"
    manifest = ROOT / ".release-please/manifest-app.json"
    version = ROOT / "version.txt"
    if not (config.exists() and manifest.exists() and version.exists()):
        return
    if json.loads(config.read_text(encoding="utf-8")).get("release-type") != "simple":
        return

    pinned = json.loads(manifest.read_text(encoding="utf-8")).get(".")
    actual = version.read_text(encoding="utf-8").strip()
    if pinned != actual:
        errors.append(f"version.txt is {actual!r} but .release-please/manifest-app.json pins {pinned!r}")


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
        # A link resolves relative to the file that contains it; a path written
        # in a table is usually relative to the repository root. Accept either.
        if (path.parent / ref).exists() or (ROOT / ref).exists():
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


def check_local_workflow_calls_resolve(errors: list[str]) -> None:
    """A `uses: ./.github/workflows/x.yml` must point at a file that exists.

    Removing an optional pack used to leave the caller behind, which takes the
    whole calling workflow down rather than just the removed job.
    """
    workflows = ROOT / ".github/workflows"
    if not workflows.is_dir():
        return

    local = re.compile(r"uses:\s*(\./[A-Za-z0-9._/-]+)")
    for path in sorted(workflows.glob("*.y*ml")):
        for match in local.finditer(path.read_text(encoding="utf-8")):
            ref = match.group(1)[2:]
            target = ROOT / ref
            # A composite action is referenced by its directory.
            is_action_dir = target.is_dir() and any(
                (target / name).is_file() for name in ("action.yml", "action.yaml")
            )
            if target.is_file() or is_action_dir:
                continue
            errors.append(f"{_rel(path)}: calls {match.group(1)!r}, which does not exist")


def check_issue_template_config(errors: list[str]) -> None:
    """Every contact link needs name, url and about.

    Removing an optional URL used to leave the surrounding entry behind, and
    GitHub rejects the whole chooser rather than just that link.
    """
    import yaml

    config = ROOT / ".github/ISSUE_TEMPLATE/config.yml"
    if not config.exists():
        return

    doc = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    for index, link in enumerate(doc.get("contact_links") or []):
        missing = [key for key in ("name", "url", "about") if not (link or {}).get(key)]
        if missing:
            name = (link or {}).get("name", f"#{index}")
            errors.append(
                f".github/ISSUE_TEMPLATE/config.yml: contact link {name!r} is missing {', '.join(missing)}"
            )


def check_pr_target_never_checks_out(errors: list[str]) -> None:
    """A pull_request_target workflow must not check out the pull request.

    pull_request_target runs in the base repository's context with a writable
    token. Checking out the head there executes a fork's code with that token.
    The workflows carry a comment saying so; this is what enforces it.
    """
    import yaml

    workflows = ROOT / ".github/workflows"
    if not workflows.is_dir():
        return

    for path in sorted(workflows.glob("*.y*ml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue  # check_yaml_loads already reported it

        # PyYAML reads the unquoted key `on` as the boolean True. The value
        # may be a mapping, a sequence, or a bare string, and the guard has to
        # recognise all three or it silently passes the workflow.
        triggers = doc.get("on", doc.get(True))
        if isinstance(triggers, dict):
            names = set(triggers)
        elif isinstance(triggers, list):
            names = set(triggers)
        elif isinstance(triggers, str):
            names = {triggers}
        else:
            names = set()
        if "pull_request_target" not in names:
            continue

        for job in (doc.get("jobs") or {}).values():
            for step in (job or {}).get("steps") or []:
                uses = (step or {}).get("uses", "")
                if isinstance(uses, str) and uses.startswith("actions/checkout"):
                    errors.append(
                        f"{_rel(path)}: pull_request_target workflow checks out code "
                        f"({uses}); that runs fork code with a writable token"
                    )


# Markers bootstrap is supposed to consume. Written as split literals so this
# file never matches its own patterns.
MARKER_RES = (
    re.compile(r"<!--\s*template-only:(?:start|end)\s*-->"),
    re.compile(r"<!--\s*(?:if:[A-Z_]+|endif)\s*-->"),
    re.compile(r"^\s*#\s*(?:if:[A-Z_]+|endif)\s*$", re.M),
)


# Leading bytes of the executable formats a build is likely to leave behind.
BINARY_MAGIC = (
    b"\x7fELF",          # ELF
    b"\xfe\xed\xfa\xce",  # Mach-O 32
    b"\xfe\xed\xfa\xcf",  # Mach-O 64
    b"\xce\xfa\xed\xfe",  # Mach-O 32, byte-swapped
    b"\xcf\xfa\xed\xfe",  # Mach-O 64, byte-swapped
    b"\xca\xfe\xba\xbe",  # Mach-O universal
    b"MZ",                 # PE
)


def check_base_image_pin_matches(errors: list[str]) -> None:
    """The Dockerfile ARG defaults must match versions.env.

    Two copies of the same pin drift, and the one Renovate updates is not
    necessarily the one the build uses.
    """
    env_file = ROOT / "versions.env"
    dockerfile = ROOT / "Dockerfile"
    if not (env_file.exists() and dockerfile.exists()):
        return

    env = dict(
        line.split("=", 1)
        for line in env_file.read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    text = dockerfile.read_text(encoding="utf-8")

    for key in ("BASE_IMAGE", "BASE_IMAGE_DIGEST"):
        if key not in env:
            continue
        match = re.search(rf"^ARG {key}=(.+)$", text, re.M)
        if not match:
            errors.append(f"Dockerfile: no `ARG {key}=` to compare against versions.env")
        elif match.group(1).strip() != env[key].strip():
            errors.append(
                f"Dockerfile `ARG {key}={match.group(1).strip()}` does not match "
                f"versions.env `{key}={env[key].strip()}`"
            )


def check_no_committed_binaries(errors: list[str]) -> None:
    """No compiled executable may be tracked.

    `go build ./...` writes a binary named after the package directory into the
    working directory, and `git add -A` then commits it. It happened in this
    repository, and a template that ships one hands it to every adopter.
    """
    try:
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            capture_output=True, check=True,
        ).stdout.split(b"\0")
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return  # not a git checkout; nothing to assert

    for raw in tracked:
        if not raw:
            continue
        rel = raw.decode("utf-8", "replace")
        path = ROOT / rel
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as handle:
            head = handle.read(4)
        if any(head.startswith(magic) for magic in BINARY_MAGIC):
            size = path.stat().st_size
            errors.append(f"{rel}: a compiled executable is committed ({size} bytes)")


def check_bootstrap_left_nothing_behind(errors: list[str]) -> None:
    """After bootstrap, no placeholder and no bootstrap marker may survive.

    In the template repository itself everything still holds placeholders, so
    the check is a no-op until the CHECKLIST.md marker file is gone.
    """
    if (ROOT / "CHECKLIST.md").exists():
        return  # still an unadopted template

    # The same set bootstrap rewrites. Scanning less means a malformed adopted
    # repository passes validation.
    extra = {"Dockerfile", "LICENSE", "NOTICE", "CODEOWNERS", "go.mod", ".gitignore"}
    candidates = [
        path for path in _files()
        if path.suffix in {".md", ".yml", ".yaml", ".json", ".toml", ".txt", ".env", ".go", ".py"}
        or path.name in extra
    ]

    for path in candidates:
        rel = _rel(path)
        if rel in PLACEHOLDER_DOCS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        found = sorted(set(PLACEHOLDER_RE.findall(text)))
        if found:
            errors.append(f"{rel}: unreplaced placeholder(s): {', '.join(found)}")

        for pattern in MARKER_RES:
            for match in pattern.findall(text):
                errors.append(f"{rel}: bootstrap marker left behind: {match.strip()!r}")


CHECKS = (
    check_yaml_loads,
    check_json_loads,
    check_labeler_labels_declared,
    check_release_please_packages_exist,
    check_version_file_matches_manifest,
    check_referenced_paths_exist,
    check_pr_target_never_checks_out,
    check_issue_template_config,
    check_local_workflow_calls_resolve,
    check_bootstrap_left_nothing_behind,
    check_no_committed_binaries,
    check_base_image_pin_matches,
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
