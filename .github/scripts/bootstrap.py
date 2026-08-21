#!/usr/bin/env python3
"""Turn the template into a project.

Substitutes every placeholder, removes the packs that were not selected, records
where the repository came from, and then runs repo-lint so a half-applied
template fails loudly instead of quietly.

Run through `task bootstrap`. Safe to re-run: it is a no-op once the marker
file CHECKLIST.md is gone.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

SKIP_DIRS = {".git", "node_modules", "dist", "bin", ".task", "vendor", ".idea"}
TEXT_SUFFIXES = {".md", ".yml", ".yaml", ".json", ".toml", ".txt", ".env", ".go", ".py", ".js"}
EXTRA_FILES = {"Dockerfile", "LICENSE", "NOTICE", "CODEOWNERS", "go.mod", "Taskfile.yml", ".gitignore"}

# Files that document the placeholder mechanism and are removed at the end, so
# they are never substituted.
TEMPLATE_ONLY = ["CHECKLIST.md", ".github/scripts/bootstrap.py"]

# Prose that only makes sense while the repository is still a template is
# wrapped in these markers and stripped during bootstrap. Without this the
# README keeps linking to CHECKLIST.md after bootstrap deletes it.
TEMPLATE_BLOCK = re.compile(
    r"[ \t]*<!--[ ]*template-only:start[ ]*-->.*?<!--[ ]*template-only:end[ ]*-->[ \t]*\n?",
    re.S,
)


def optional_block(key: str) -> re.Pattern:
    """Match a block that only belongs in the file when `key` has a value.

    Dropping one line is not enough: removing a URL leaves its heading behind,
    and removing the `url:` of an issue-template contact link leaves an entry
    GitHub rejects. Both comment syntaxes are supported so the same marker
    works in Markdown and in YAML.
    """
    return re.compile(
        rf"[ \t]*(?:<!--[ ]*if:{key}[ ]*-->|#[ ]*if:{key})"
        rf".*?"
        rf"(?:<!--[ ]*endif[ ]*-->|#[ ]*endif)[ \t]*\n?",
        re.S,
    )


@dataclasses.dataclass(frozen=True)
class Field:
    key: str
    prompt: str
    required: bool = True
    default: str = ""


FIELDS = (
    Field("ORG_NAME", "GitHub organisation or user"),
    Field("REPO_NAME", "Repository name"),
    Field("REPO_DESCRIPTION", "One-line description"),
    Field("MODULE_PATH", "Go module path", required=False),
    Field("COPYRIGHT_HOLDER", "Copyright holder"),
    Field("COPYRIGHT_YEAR", "Copyright year"),
    Field("MAINTAINER_NAME", "Lead maintainer, full name"),
    Field("MAINTAINER_GITHUB", "Lead maintainer, GitHub handle"),
    Field("SECURITY_EMAIL", "Address for security reports"),
    Field("CONDUCT_EMAIL", "Address for code of conduct reports"),
    Field("HOMEPAGE_URL", "Project homepage", required=False),
    Field("DOCS_URL", "Documentation URL", required=False),
    Field("SLACK_URL", "Chat invite URL", required=False),
)


def iter_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if SKIP_DIRS & set(rel.parts):
            continue
        if str(rel) in TEMPLATE_ONLY:
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in EXTRA_FILES:
            yield path


def collect(args) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in FIELDS:
        value = getattr(args, field.key.lower(), None)
        if value is None:
            if not sys.stdin.isatty():
                if field.required:
                    sys.exit(f"error: --{field.key.lower().replace('_', '-')} is required in non-interactive mode")
                value = ""
            else:
                suffix = "" if field.required else " (optional, blank to omit)"
                value = input(f"{field.prompt}{suffix}: ").strip()
        if field.required and not value:
            sys.exit(f"error: {field.key} is required")
        values[field.key] = value

    if not values["MODULE_PATH"]:
        values["MODULE_PATH"] = f"github.com/{values['ORG_NAME']}/{values['REPO_NAME']}"
    return values


def substitute(values: dict[str, str], dry_run: bool) -> int:
    # For an omitted optional value, remove the whole marked block, then any
    # stray line that still mentions the placeholder.
    blank = [field.key for field in FIELDS if not field.required and not values[field.key]]
    blocks = [optional_block(key) for key in blank]
    drops = [re.compile(rf"^.*\{{\{{{key}\}}\}}.*$\n?", re.M) for key in blank]

    changed = 0
    for path in iter_files():
        original = path.read_text(encoding="utf-8")
        text = original

        # Sections that only apply while this is still a template.
        text = TEMPLATE_BLOCK.sub("", text)

        # Blocks that exist only for an omitted optional value.
        for pattern in blocks:
            text = pattern.sub("", text)

        # Then any stray line still mentioning it, so nothing points nowhere.
        for pattern in drops:
            text = pattern.sub("", text)

        for key, value in values.items():
            text = text.replace(f"{{{{{key}}}}}", value)

        if text != original:
            changed += 1
            if dry_run:
                print(f"would rewrite {path.relative_to(ROOT)}")
            else:
                path.write_text(text, encoding="utf-8")
    return changed


GO_PACK = [
    "go.mod", "go.sum", "main.go", "main_test.go", "Dockerfile", ".golangci.yaml",
    ".github/workflows/ci.yml", ".github/workflows/release-assets.yml",
    ".github/workflows/publish-image.yml", ".github/actions/setup",
]


def remove_go_pack(dry_run: bool) -> None:
    """Remove the Go pack and the two references that would otherwise dangle."""
    for rel in GO_PACK:
        path = ROOT / rel
        if not path.exists():
            continue
        print(f"{'would remove' if dry_run else 'removing'} {rel}")
        if not dry_run:
            if path.is_dir():
                for child in sorted(path.rglob("*"), reverse=True):
                    child.unlink() if child.is_file() else child.rmdir()
                path.rmdir()
            else:
                path.unlink()

    release_please = ROOT / ".github/workflows/release-please.yml"
    if release_please.exists() and not dry_run:
        text = release_please.read_text(encoding="utf-8")
        # Drop the jobs that call the workflows just deleted.
        for job in ("publish-release-assets", "publish-image", "document-artifacts"):
            text = re.sub(rf"\n  {job}:\n(?:(?:    |\n).*\n)*", "\n", text)
        release_please.write_text(text, encoding="utf-8")
        print("removed the publish jobs from release-please.yml")


def strip_release_migration_keys(dry_run: bool) -> None:
    """Remove release-please keys that only make sense in the template repo.

    `bootstrap-sha` marks where the template's own history starts. In a new
    repository it points at a commit that does not exist, so release-please
    would look for it, never find it, and fall back to the full history.
    """
    config = ROOT / "release-please-config.json"
    if not config.exists():
        return

    text = config.read_text(encoding="utf-8")
    stripped = re.sub(r'^[ \t]*"bootstrap-sha":[^\n]*\n', "", text, flags=re.M)
    if stripped == text:
        return

    print(f"{'would remove' if dry_run else 'removing'} bootstrap-sha from release-please-config.json")
    if not dry_run:
        config.write_text(stripped, encoding="utf-8")


def write_provenance(values: dict[str, str], dry_run: bool) -> None:
    """Record where this repository came from.

    Without it there is no way to ask which repositories were created from
    which version of the template, so a fix reaches exactly one new repository
    and the rest stay divergent.
    """
    try:
        sha = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sha = "unknown"

    content = (
        "# Created from container-registry/oss-project-template.\n"
        "# Kept so it is possible to ask which repositories carry which version\n"
        "# of the template, and which still carry a defect fixed upstream.\n"
        f"template_repository: container-registry/oss-project-template\n"
        f"template_commit: {sha}\n"
        f"bootstrapped_for: {values['ORG_NAME']}/{values['REPO_NAME']}\n"
    )
    target = ROOT / ".github/template.yml"
    print(f"{'would write' if dry_run else 'writing'} .github/template.yml")
    if not dry_run:
        target.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in FIELDS:
        parser.add_argument(f"--{field.key.lower().replace('_', '-')}", dest=field.key.lower())
    parser.add_argument("--lang", choices=["go", "none"], default="go",
                        help="Keep the Go and container pack, or remove it")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not (ROOT / "CHECKLIST.md").exists():
        print("Already bootstrapped: CHECKLIST.md is gone. Nothing to do.")
        return 0

    values = collect(args)
    changed = substitute(values, args.dry_run)
    print(f"{'would rewrite' if args.dry_run else 'rewrote'} {changed} file(s)")

    if args.lang == "none":
        remove_go_pack(args.dry_run)

    strip_release_migration_keys(args.dry_run)
    write_provenance(values, args.dry_run)

    for rel in TEMPLATE_ONLY:
        path = ROOT / rel
        if path.exists():
            print(f"{'would remove' if args.dry_run else 'removing'} {rel}")
            if not args.dry_run:
                path.unlink()

    if args.dry_run:
        print("\nDry run: nothing was written.")
        return 0

    print("\nVerifying...")
    result = subprocess.run([sys.executable, str(ROOT / ".github/scripts/repo-lint.py")])
    if result.returncode != 0:
        print("\nBootstrap finished but repo-lint failed. Fix the above before pushing.", file=sys.stderr)
        return 1

    print(
        "\nDone. Next:\n"
        "  1. Review the diff.\n"
        "  2. task check\n"
        "  3. Add a SETTINGS_TOKEN secret so .github/settings.yml can be applied.\n"
        "  4. git add -A && git commit -s -m 'chore: bootstrap from template'\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
