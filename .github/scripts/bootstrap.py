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
import json
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


# The marker lines themselves are always removed, whether or not the block they
# guard survives. Leaving them behind when the value IS supplied was a bug that
# only showed up once bootstrap was run with a non-empty optional value.
MARKER_LINE = re.compile(
    r"^[ \t]*(?:<!--[ ]*(?:if:[A-Z_]+|endif)[ ]*-->|#[ ]*(?:if:[A-Z_]+|endif))[ \t]*\n",
    re.M,
)


def pack_block(name: str) -> re.Pattern:
    """Match prose that only belongs in the file while the `name` pack exists."""
    return re.compile(
        rf"[ \t]*<!--[ ]*pack:{name}:start[ ]*-->.*?<!--[ ]*pack:{name}:end[ ]*-->[ \t]*\n?",
        re.S,
    )


# The pack markers themselves never survive, whether or not the block does.
PACK_MARKER_LINE = re.compile(r"^[ \t]*<!--[ ]*pack:[a-z]+:(?:start|end)[ ]*-->[ \t]*\n", re.M)


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
        # Values land in YAML strings, JSON, and Dockerfile LABELs. Rejecting
        # the two characters that break those is simpler to reason about than
        # escaping per output format, and the answer is always to rephrase.
        bad = set(value) & set('"\\')
        if bad:
            sys.exit(f"error: {field.key} must not contain {' or '.join(sorted(bad))}")
        values[field.key] = value

    if not values["MODULE_PATH"]:
        values["MODULE_PATH"] = f"github.com/{values['ORG_NAME']}/{values['REPO_NAME']}"
    return values


def substitute(values: dict[str, str], removed_packs: set[str], dry_run: bool) -> int:
    # For an omitted optional value, remove the whole marked block, then any
    # stray line that still mentions the placeholder.
    blank = [field.key for field in FIELDS if not field.required and not values[field.key]]
    blocks = [optional_block(key) for key in blank]
    blocks += [pack_block(name) for name in sorted(removed_packs)]
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

        # Whatever blocks survived, their markers do not.
        text = MARKER_LINE.sub("", text)
        text = PACK_MARKER_LINE.sub("", text)

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
    "tools/govulncheck-report", ".github/scripts/vulnerability-comment.sh",
]


def remove_go_pack(dry_run: bool, keep_setup_action: bool) -> None:
    """Remove the Go pack and the two references that would otherwise dangle.

    The setup composite installs Go and Task. chart-ci.yml uses it for Task
    alone, so it stays while the chart pack does.
    """
    for rel in GO_PACK:
        if keep_setup_action and rel == ".github/actions/setup":
            continue
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
            # A pack directory such as tools/ is not worth keeping empty.
            parent = path.parent
            while parent != ROOT and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

    # The automation reference documents files that no longer exist.
    doc = ROOT / "docs/repo-automation.md"
    if doc.exists() and not dry_run:
        gone = ("ci.yml", "release-assets.yml", "publish-image.yml",
                ".golangci.yaml", "Dockerfile", "go.mod", "vulnerability-comment.sh")
        if not keep_setup_action:
            gone += (".github/actions/setup",)
        kept = [
            line for line in doc.read_text(encoding="utf-8").splitlines(keepends=True)
            if not (line.lstrip().startswith("|") and any(name in line for name in gone))
        ]
        doc.write_text("".join(kept), encoding="utf-8")
        print("pruned docs/repo-automation.md")

    # CONTRIBUTING.md documents the govulncheck report, which the Go pack owns.
    contributing = ROOT / "CONTRIBUTING.md"
    if contributing.exists() and not dry_run:
        text = contributing.read_text(encoding="utf-8")
        pruned = re.sub(r"## Vulnerabilities\n(?:.*\n)*?(?=## )", "", text, count=1)
        if pruned != text:
            contributing.write_text(pruned, encoding="utf-8")
            print("pruned the vulnerability section from CONTRIBUTING.md")

    # Without the Go pack the merge only tags and releases; the header must not promise an image.
    config = ROOT / ".release-please/config-app.json"
    if config.exists() and not dry_run:
        text = config.read_text(encoding="utf-8")
        pruned = text.replace("and publishes the image and binaries.", "and creates the GitHub release.")
        if pruned != text:
            config.write_text(pruned, encoding="utf-8")
            print("made the release pull request header describe the tag and release only")

    # The jobs that call the workflows just deleted.
    remove_jobs(".github/workflows/release-please.yml",
                ("publish-release-assets", "publish-image", "document-artifacts"), dry_run)


CHART_PACK = [
    "deploy/chart", "taskfile/helm.yml", "taskfile/ct-lintconf.yaml",
    ".github/workflows/chart-ci.yml", ".github/workflows/publish-chart.yml",
    ".github/scripts/chart-annotate-images.sh",
    ".release-please/config-chart.json", ".release-please/manifest-chart.json",
]


def remove_paths(paths: list[str], dry_run: bool) -> None:
    for rel in paths:
        path = ROOT / rel
        if not path.exists():
            continue
        print(f"{'would remove' if dry_run else 'removing'} {rel}")
        if dry_run:
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*"), reverse=True):
                child.unlink() if child.is_file() else child.rmdir()
            path.rmdir()
        else:
            path.unlink()
        # A pack directory such as taskfile/ is not worth keeping empty.
        parent = path.parent
        while parent != ROOT and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


def prune_automation_doc(gone: tuple[str, ...], dry_run: bool) -> None:
    """Drop the table rows of docs/repo-automation.md that name removed files."""
    doc = ROOT / "docs/repo-automation.md"
    if doc.exists() and not dry_run:
        kept = [
            line for line in doc.read_text(encoding="utf-8").splitlines(keepends=True)
            if not (line.lstrip().startswith("|") and any(name in line for name in gone))
        ]
        doc.write_text("".join(kept), encoding="utf-8")
        print("pruned docs/repo-automation.md")


def remove_jobs(rel: str, jobs: tuple[str, ...], dry_run: bool) -> None:
    """Delete top-level jobs from a workflow, comments above them included."""
    path = ROOT / rel
    if path.exists() and not dry_run:
        text = path.read_text(encoding="utf-8")
        for job in jobs:
            # A blank line belongs to the job, but only as a blank line: `\n.*\n`
            # would also swallow the unindented line after it, which is the
            # first comment line of the next job.
            text = re.sub(rf"\n(?:  #[^\n]*\n)*  {job}:\n(?:(?:    .*\n)|\n)*", "\n", text)
        # Deleting the last job leaves its separator behind; yamllint rejects
        # a trailing blank line.
        text = re.sub(r"\n{3,}", "\n\n", text).rstrip("\n") + "\n"
        path.write_text(text, encoding="utf-8")
        print(f"removed {', '.join(jobs)} from {rel}")


def remove_chart_pack(dry_run: bool) -> None:
    """Remove the Helm chart pack and everything that would otherwise dangle."""
    remove_paths(CHART_PACK, dry_run)
    prune_automation_doc(("chart-ci.yml", "publish-chart.yml", "taskfile/helm.yml", "ct-lintconf.yaml",
                          "chart-annotate-images.sh", "config-chart.json", "deploy/chart"), dry_run)
    remove_jobs(".github/workflows/release-please.yml", ("release-please-chart", "publish-helm-chart"), dry_run)
    remove_jobs(".github/workflows/pr-title.yml", ("chart-scope-paths",), dry_run)

    if dry_run:
        return
    taskfile = ROOT / "Taskfile.yml"
    text = taskfile.read_text(encoding="utf-8")
    pruned = re.sub(r"\n(?:#[^\n]*\n)*includes:\n(?:  .*\n)*", "\n", text, count=1)
    if pruned != text:
        taskfile.write_text(pruned, encoding="utf-8")
        print("removed the helm include from Taskfile.yml")
    versions = ROOT / "versions.env"
    text = versions.read_text(encoding="utf-8")
    pruned = re.sub(r"\n# --- Helm pack -*\n.*?(?=\n# --- |\Z)", "\n", text, count=1, flags=re.S)
    if pruned != text:
        versions.write_text(pruned.rstrip("\n") + "\n", encoding="utf-8")
        print("removed the Helm pack pins from versions.env")
    # The chart's Chart.yaml is the only extra file the app release line
    # carries, and it is about to stop existing.
    config = ROOT / ".release-please/config-app.json"
    data = json.loads(config.read_text(encoding="utf-8"))
    if data["packages"]["."].pop("extra-files", None):
        config.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print("removed the chart extra-file from .release-please/config-app.json")
    labeler = ROOT / ".github/labeler.yml"
    text = labeler.read_text(encoding="utf-8")
    pruned = re.sub(r"component/chart:\n(?:  .*\n)*\n?", "", text, count=1)
    if pruned != text:
        labeler.write_text(pruned, encoding="utf-8")
        print("removed the component/chart label from labeler.yml")
    # And its definition: settings.yml is applied to the live repository, so
    # the label would be created there for a directory that does not exist.
    settings = ROOT / ".github/settings.yml"
    text = settings.read_text(encoding="utf-8")
    pruned = re.sub(r"  component/chart:\n(?:    .*\n)*", "", text, count=1)
    if pruned != text:
        settings.write_text(pruned, encoding="utf-8")
        print("removed the component/chart label from settings.yml")


def rewrite_identity_files(values: dict[str, str], dry_run: bool) -> None:
    """Update the two files that cannot carry a placeholder.

    go.mod must stay buildable in the template itself, and a module path
    containing braces is not a valid module path. `.github/settings.yml` is
    applied to the live repository on every push to main, so a placeholder
    there would be written to the template's own homepage field.
    """
    module = ROOT / "go.mod"
    if module.exists():
        text = module.read_text(encoding="utf-8")
        updated = re.sub(r"^module .*$", f"module {values['MODULE_PATH']}", text, count=1, flags=re.M)
        if updated != text:
            print(f"{'would set' if dry_run else 'setting'} go.mod module to {values['MODULE_PATH']}")
            if not dry_run:
                module.write_text(updated, encoding="utf-8")

    # The chart cannot carry placeholders either: helm lint runs on the
    # template itself. Its name and the image it deploys follow the repository.
    chart = ROOT / "deploy/chart"
    if chart.is_dir():
        org = values["ORG_NAME"].lower()
        # The chart name becomes a Kubernetes object name and an OCI repository
        # segment, which allow neither uppercase nor a dot; a GitHub repository
        # name allows both.
        repo = re.sub(r"[^a-z0-9]+", "-", values["REPO_NAME"].lower()).strip("-")
        if not repo:
            sys.exit(f"error: REPO_NAME {values['REPO_NAME']!r} has no character a chart name can use")
        # A DNS-1123 label; the chart name also becomes the container name,
        # which the fullname helper's 63-character truncation does not cover.
        if len(repo) > 63:
            sys.exit(f"error: REPO_NAME {values['REPO_NAME']!r} normalises to {len(repo)} characters; a chart name has at most 63")
        # The owner appears on its own next to a `{{ .Name }}` in the helm-docs
        # template, so it cannot be rewritten as part of the owner/name pair.
        for path in sorted(chart.rglob("*")):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES | {".gotmpl", ".tpl", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            updated = text.replace("container-registry/", f"{org}/")
            updated = updated.replace("oss-project-template", repo)
            if updated != text:
                print(f"{'would rewrite' if dry_run else 'rewriting'} {path.relative_to(ROOT)} for {org}/{repo}")
                if not dry_run:
                    path.write_text(updated, encoding="utf-8")

    for rel in (".release-please/config-app.json", ".release-please/config-chart.json"):
        cfg = ROOT / rel
        if not cfg.exists():
            continue
        text = cfg.read_text(encoding="utf-8")
        updated = text.replace("container-registry/oss-project-template", f"{values['ORG_NAME']}/{values['REPO_NAME']}")
        if updated != text:
            print(f"{'would rewrite' if dry_run else 'rewriting'} the release doc link in {rel}")
            if not dry_run:
                cfg.write_text(updated, encoding="utf-8")

    settings = ROOT / ".github/settings.yml"
    if settings.exists():
        text = settings.read_text(encoding="utf-8")
        updated = text
        for key, value in (("description", values["REPO_DESCRIPTION"]),
                           ("homepage", values["HOMEPAGE_URL"])):
            updated = re.sub(rf'^(\s*){key}: ""$', rf'\g<1>{key}: "{value}"', updated, count=1, flags=re.M)
        if updated != text:
            print(f"{'would set' if dry_run else 'setting'} description and homepage in settings.yml")
            if not dry_run:
                settings.write_text(updated, encoding="utf-8")


def reset_release_state(dry_run: bool) -> None:
    """Start the new repository's release history at zero.

    The manifest, version.txt and CHANGELOG.md describe the template's own
    releases. A repository created from a template carries no tags, so leaving
    the manifest at the template's version makes release-please look for a tag
    that will never exist. Reset all three so the first `feat:` produces
    v0.1.0, and strip `bootstrap-sha` if the template still carries one.
    """
    config = ROOT / ".release-please/config-app.json"
    if config.exists():
        text = config.read_text(encoding="utf-8")
        stripped = re.sub(r'^[ \t]*"bootstrap-sha":[^\n]*\n', "", text, flags=re.M)
        if stripped != text:
            print(f"{'would remove' if dry_run else 'removing'} bootstrap-sha from .release-please/config-app.json")
            if not dry_run:
                config.write_text(stripped, encoding="utf-8")

    resets = (
        (ROOT / ".release-please/manifest-app.json", '{\n  ".": "0.0.0"\n}\n'),
        (ROOT / ".release-please/manifest-chart.json", '{\n  "deploy/chart": "0.0.0"\n}\n'),
        (ROOT / "deploy/chart/CHANGELOG.md", "# Changelog\n"),
        (ROOT / "version.txt", "0.0.0\n"),
        (ROOT / "CHANGELOG.md", "# Changelog\n"),
    )
    for path, content in resets:
        if not path.exists() or path.read_text(encoding="utf-8") == content:
            continue
        print(f"{'would reset' if dry_run else 'resetting'} {path.relative_to(ROOT)}")
        if not dry_run:
            path.write_text(content, encoding="utf-8")


def reset_chart_versions(dry_run: bool) -> None:
    """Chart.yaml carries the template's own versions; both start at zero too."""
    chart = ROOT / "deploy/chart/Chart.yaml"
    if not chart.exists():
        return
    text = chart.read_text(encoding="utf-8")
    updated = re.sub(r"^version: .*$", "version: 0.0.0", text, count=1, flags=re.M)
    updated = re.sub(r'^appVersion: "[^"]*"', 'appVersion: "v0.0.0"', updated, count=1, flags=re.M)
    if updated != text:
        print(f"{'would reset' if dry_run else 'resetting'} deploy/chart/Chart.yaml versions")
        if not dry_run:
            chart.write_text(updated, encoding="utf-8")


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
    parser.add_argument("--chart", choices=["helm", "none"], default="helm",
                        help="Keep the Helm chart pack and its release line, or remove it")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not (ROOT / "CHECKLIST.md").exists():
        print("Already bootstrapped: CHECKLIST.md is gone. Nothing to do.")
        return 0

    values = collect(args)
    removed_packs = {"chart"} if args.chart == "none" else set()
    changed = substitute(values, removed_packs, args.dry_run)
    print(f"{'would rewrite' if args.dry_run else 'rewrote'} {changed} file(s)")

    if args.lang == "none":
        remove_go_pack(args.dry_run, keep_setup_action=args.chart != "none")
    if args.chart == "none":
        remove_chart_pack(args.dry_run)

    rewrite_identity_files(values, args.dry_run)
    reset_release_state(args.dry_run)
    reset_chart_versions(args.dry_run)
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
