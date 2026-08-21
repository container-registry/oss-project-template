# OSS Project Template

GitHub repository configuration and automation templates for open source projects.

## Principles & Assumptions

This template is opinionated. Here's what it assumes and why:

| Principle | Implementation | Why |
|-----------|----------------|-----|
| **Conventional Commits** | Commit messages must follow `type: description` format | Enables automatic versioning, changelog generation, and clear history |
| **Squash Merge Only** | Merge commits and rebases disabled | One commit per PR keeps history clean and bisectable |
| **PR-Based Workflow** | All changes via pull requests | Ensures review, CI checks, and audit trail |
| **DCO Sign-Off** | All commits require `Signed-off-by` | Legal compliance for open source contributions |
| **Automated Releases** | Version bumps from commit types | Removes manual versioning errors, ensures consistency |
| **Adaptable Versioning** | Generic release type with language-specific extension points | Works before project packaging is finalized |
| **Local-First** | Lefthook validates before push | Fail fast locally, don't waste CI time |
| **GitHub-Native** | Maximize GitHub features, minimize external dependencies | Reduces complexity, improves reliability |

### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

Signed-off-by: Name <email>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

**Version impact:**
- `feat:` → minor bump (0.1.0 → 0.2.0)
- `fix:` → patch bump (0.1.0 → 0.1.1)
- `feat!:` or `fix!:` (breaking) → major bump, or minor while on 0.x
- every other type → patch bump

Any conventional commit that is not excluded by path produces a release. Marking a changelog section
`hidden: true` removes it from the release notes; it does not stop the commit from bumping the version.
Use `exclude-paths` for that. See [docs/RELEASES.md](docs/RELEASES.md).

## Why This Template?

This template maximizes GitHub's native capabilities for automation and guardrails, reducing the need for external services while making it straightforward for new contributors to join your project:

- **Zero-friction onboarding** - YAML issue forms guide contributors through bug reports, feature requests, and proposals with validation and dropdowns
- **Automated quality gates** - DCO sign-off, spell checking, license compliance, and dependency review run automatically on every PR
- **Smart labeling** - PRs are auto-labeled by size (XS-XL) and changed components, keeping your issue tracker organized
- **Release automation** - Version bumps and changelogs generated automatically from conventional commits
- **Security-first** - OpenSSF Scorecard, dependency review, and vulnerability alerts enabled by default
- **Welcoming community** - First-time contributors receive friendly guidance; clear support channels are documented

This template is programming language agnostic. A minimal Go application is included for end-to-end testing.  


## Quick Start

1. Copy the `.github/` directory to your repository
2. Copy the community and release files (`CODE_OF_CONDUCT.md`, `SUPPORT.md`, `CHANGELOG.md`, `ROADMAP.md`, `release-please-config.json`, `.release-please-manifest.json`, `version.txt`, `docs/RELEASES.md`)
3. Copy `Taskfile.yml`, `lefthook.yml`, and `.typos.toml` - the release workflow calls `task release-assets`, and these define the checks that mirror CI
4. Replace placeholders with your project values
5. Follow the **[CHECKLIST.md](CHECKLIST.md)** for a complete adoption guide

## Local Development

Run CI checks locally before committing:

```bash
# One-time setup
task setup

# Run all checks
task check

# Or let hooks run automatically
git commit -s -m "your message"
```

### Running GitHub Actions Locally (Optional)

For workflows that can run locally, use [act](https://github.com/nektos/act):

```bash
brew install act
act -l                    # List workflows
act -j spellcheck         # Run specific job
act -j license-check
```

Note: Only `spellcheck` and `license-check` work locally. Other workflows require GitHub's API.

## Placeholders

Replace these placeholders in all files:

| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{ORG_NAME}}` | GitHub organization | `container-registry` |
| `{{REPO_NAME}}` | Repository name | `harbor-next` |
| `{{DOCS_URL}}` | Documentation URL | `https://goharbor.io/docs/` |
| `{{SLACK_URL}}` | Slack invite URL | `https://slack.cncf.io/` |
| `{{HOMEPAGE_URL}}` | Project homepage | `https://goharbor.io/` |
| `{{MODULE_PATH}}` | Go module path | `github.com/goharbor/harbor` |
| `{{REPO_DESCRIPTION}}` | Repository description | `Cloud native registry` |

## What's Included

### Issue Templates (`.github/ISSUE_TEMPLATE/`)
- `bug_report.yml` - Bug report form
- `feature_request.yml` - Feature request form
- `proposal.yml` - Architectural proposal form
- `config.yml` - Template chooser configuration

### PR Template
- `.github/pull_request_template.md` - Pull request template with checklists

### Workflows (`.github/workflows/`)
| Workflow | Purpose |
|----------|---------|
| `welcome.yml` | Greet first-time contributors |
| `labeler.yml` | Auto-label PRs by changed files |
| `pr-size-labeler.yml` | Auto-label PRs by size (XS/S/M/L/XL) |
| `pr-title.yml` | Validate PR title follows conventional commits |
| `release-please.yml` | Create release PRs from conventional commits |
| `spellcheck.yml` | Spell check with typos |
| `license-check.yml` | License compliance for Go dependencies |
| `dependency-review.yml` | Review dependency changes in PRs |
| `scorecard.yml` | OpenSSF Scorecard integration |
| `release-assets.yml` | Build and upload release binaries |
| `apply-settings.yml` | Apply repository settings from `settings.yml` |

### Configuration Files
| File | Purpose |
|------|---------|
| `.github/labeler.yml` | File pattern to label mapping |
| `release-please-config.json` | Release-please configuration |
| `.release-please-manifest.json` | Release-please version manifest |
| `version.txt` | Generic version file maintained by release-please |
| `.github/settings.yml` | Repository settings (auto-applied via workflow) |
| `.typos.toml` | Spell checker configuration |
| `docs/RELEASES.md` | Generic release process and extension points |

### Scripts
| File | Purpose |
|------|---------|
| `scripts/export-settings.sh` | Export current repo settings to YAML for diffing |

### Community Files
| File | Purpose |
|------|---------|
| `CODE_OF_CONDUCT.md` | Community guidelines |
| `SUPPORT.md` | How to get help |
| `CHANGELOG.md` | Release changelog |
| `ROADMAP.md` | Project roadmap |

## Customization

### Adding Project-Specific Labels

Edit `.github/labeler.yml` to add component labels:

```yaml
component/api:
  - changed-files:
      - any-glob-to-any-file:
          - 'src/api/**/*'
```

### Adding Spell Check Exceptions

Edit `.typos.toml` to add project-specific terms:

```toml
[default.extend-words]
myterm = "myterm"
```

### Release Automation

The default release-please config tracks one generic package and creates `vX.Y.Z` tags. Its `simple` release type maintains `version.txt`; switch to a language-specific release type when appropriate:

```json
{
  "release-type": "simple",
  "packages": {
    ".": {}
  }
}
```

Use `go`, `node`, `python`, `rust`, or `helm` when release-please should update the project's native version file
instead - `package.json`, `pyproject.toml`, `Cargo.toml`, `Chart.yaml`. Those types do not maintain `version.txt`, so
delete it when you switch, or keep it in sync by listing it under `extra-files`. Monorepos can add package paths under
`packages`; each path gets independent version tracking and a changelog.

See [docs/RELEASES.md](docs/RELEASES.md) for the flow, version rules, required repository settings, and post-release job pattern.

## Requirements

Some workflows require:
- **Go**: For license-check workflow (Go projects only)

### DCO Enforcement

This template uses [dco2](https://github.com/cncf/dco2), a GitHub App that enforces Developer Certificate of Origin sign-offs on pull requests.

**Install the app:** https://github.com/apps/dco2

Benefits over workflow-based DCO checks:
- Remediation commits (fix missing sign-offs without force-push)
- Third-party sign-off support
- Optional bypass for GPG-signed commits (configure via `.github/dco.yml`)

## License

This template is available under the Apache 2.0 License.
