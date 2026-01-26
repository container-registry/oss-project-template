# OSS Project Template

GitHub repository configuration and automation templates for open source projects.

## Why This Template?

This template maximizes GitHub's native capabilities for automation and guardrails, reducing the need for external services while making it straightforward for new contributors to join your project:

- **Zero-friction onboarding** - YAML issue forms guide contributors through bug reports, feature requests, and proposals with validation and dropdowns
- **Automated quality gates** - DCO sign-off, spell checking, license compliance, and dependency review run automatically on every PR
- **Smart labeling** - PRs are auto-labeled by size (XS-XL) and changed components, keeping your issue tracker organized
- **Release automation** - Release notes draft themselves from merged PRs, categorized by type
- **Security-first** - OpenSSF Scorecard, dependency review, and vulnerability alerts enabled by default
- **Welcoming community** - First-time contributors receive friendly guidance; clear support channels are documented

This template is programming language agnostic. A minimal Go application is included for end-to-end testing.  


## Quick Start

1. Copy the `.github/` directory to your repository
2. Copy the community files (`CODE_OF_CONDUCT.md`, `SUPPORT.md`, `CHANGELOG.md`, `ROADMAP.md`)
3. Copy `.typos.toml` for spell checking
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
| `release-drafter.yml` | Auto-generate release notes |
| `spellcheck.yml` | Spell check with typos |
| `license-check.yml` | License compliance for Go dependencies |
| `dependency-review.yml` | Review dependency changes in PRs |
| `scorecard.yml` | OpenSSF Scorecard integration |
| `changelog-sync.yml` | Sync GitHub Releases to CHANGELOG.md |
| `apply-settings.yml` | Apply repository settings from `settings.yml` |

### Configuration Files
| File | Purpose |
|------|---------|
| `.github/labeler.yml` | File pattern to label mapping |
| `.github/release-drafter.yml` | Release notes template |
| `.github/settings.yml` | Repository settings (auto-applied via workflow) |
| `.typos.toml` | Spell checker configuration |

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
