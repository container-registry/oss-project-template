# Template Adoption Checklist

Use this checklist when applying this template to your project.

---

## 1. Replace Placeholders (Required)

Find and replace these placeholders across all files:

| Placeholder | Replace With | Files Affected |
|-------------|--------------|----------------|
| `{{ORG_NAME}}` | Your GitHub org (e.g., `goharbor`) | `config.yml`, `SUPPORT.md`, `ROADMAP.md` |
| `{{REPO_NAME}}` | Your repo name (e.g., `harbor`) | `config.yml`, `SUPPORT.md`, `ROADMAP.md` |
| `{{DOCS_URL}}` | Documentation URL | `config.yml`, `SUPPORT.md`, `welcome.yml` |
| `{{SLACK_URL}}` | Slack/Discord invite URL | `config.yml`, `SUPPORT.md`, `ROADMAP.md` |
| `{{HOMEPAGE_URL}}` | Project homepage | `settings.yml` |

**Quick replace command:**
```bash
# macOS/Linux
find . -type f \( -name "*.yml" -o -name "*.md" \) -exec sed -i '' \
  -e 's/{{ORG_NAME}}/your-org/g' \
  -e 's/{{REPO_NAME}}/your-repo/g' \
  -e 's|{{DOCS_URL}}|https://docs.example.com|g' \
  -e 's|{{SLACK_URL}}|https://slack.example.com|g' \
  -e 's|{{HOMEPAGE_URL}}|https://example.com|g' \
  {} \;
```

---

## 2. Repository Settings

### `.github/settings.yml`

This file maps 1:1 to GitHub REST API and is auto-applied on push to main.

- [ ] Update `description` to your project description
- [ ] Set `homepage` URL (or leave empty)
- [ ] Review merge strategies (`allow_squash_merge`, etc.)
- [ ] Keep `actions.can_approve_pull_request_reviews` enabled so release-please can open release PRs
- [ ] Uncomment and configure branch protection rules if needed
- [ ] Add project-specific component labels

**Export current settings:**
```bash
./scripts/export-settings.sh > current.yml
diff .github/settings.yml current.yml
```

---

## 3. Issue Templates

### `.github/ISSUE_TEMPLATE/config.yml`

- [ ] Replace all placeholder URLs
- [ ] Remove or update contact links not applicable to your project

### `.github/ISSUE_TEMPLATE/bug_report.yml`

- [ ] Review and customize form fields
- [ ] Update version dropdown options
- [ ] Add project-specific environment fields

### `.github/ISSUE_TEMPLATE/feature_request.yml`

- [ ] Review and customize form fields
- [ ] Add project-specific sections if needed

### `.github/ISSUE_TEMPLATE/proposal.yml`

- [ ] Review and customize form fields
- [ ] Adjust for your project's RFC/proposal process

---

## 4. PR Template

### `.github/pull_request_template.md`

- [ ] Review "Type of Change" checkboxes
- [ ] Update checklists for your project requirements
- [ ] Add project-specific sections if needed

---

## 5. Workflows

### `.github/workflows/welcome.yml`

- [ ] Replace `{{DOCS_URL}}` in welcome messages
- [ ] Customize welcome messages for your project

### `.github/workflows/labeler.yml`

- [ ] No changes needed (uses `labeler.yml` config)

### DCO Enforcement (dco2 GitHub App)

- [ ] Install [dco2](https://github.com/apps/dco2) GitHub App on your repository
- [ ] (Optional) Add `.github/dco.yml` to customize behavior (e.g., skip sign-off for GPG-signed commits)

### `.github/workflows/license-check.yml`

- [ ] Update `--ignore=` to your Go module path (must match `go.mod`)
- [ ] Review allowed/denied licenses for your project
- [ ] Remove if not a Go project

### `.github/workflows/spellcheck.yml`

- [ ] No changes needed (uses `.typos.toml` config)

### `.github/workflows/scorecard.yml`

- [ ] No changes needed

### `.github/workflows/dependency-review.yml`

- [ ] Review fail-on-severity level

### `.github/workflows/release-please.yml`

- [ ] No changes needed for changelog/tag automation (uses `release-please-config.json`)
- [ ] Add post-release jobs here if publishing images, charts, binaries, or other artifacts
- [ ] Give each job you add its own `permissions:` block. The workflow declares `permissions: {}` at the top
      level, so a new job starts with no scopes and must request exactly what it needs
      (publishing release assets needs `contents: write`; pushing to GHCR needs `packages: write`;
      keyless cosign signing needs `id-token: write`)

### `.github/workflows/release-assets.yml`

- [ ] Update the `release-assets` task in `Taskfile.yml` - the build commands live there, not in this workflow
- [ ] Adjust `RELEASE_BINARY`, `RELEASE_DIST`, and `RELEASE_PACKAGE` for your project
- [ ] Remove this workflow and its `publish-release-assets` caller in `release-please.yml` if not publishing binaries

### `.github/workflows/apply-settings.yml`

- [ ] No changes needed (applies `settings.yml` automatically on push to main)

---

## 6. Configuration Files

### `.github/labeler.yml`

- [ ] Add project-specific component labels and paths:
  ```yaml
  component/api:
    - changed-files:
        - any-glob-to-any-file:
            - 'api/**/*'
            - 'pkg/api/**/*'
  ```
- [ ] Remove language-specific patterns you don't use

### `release-please-config.json`

- [ ] Update `release-type` for your language:
  - `simple` (default) - Generic (creates `version.txt`)
  - `go` - Go modules. Maintains the changelog and tag only; Go is versioned by tags. Set
    `"version-file": "version.txt"` as well, or `version.txt` goes stale with nothing replacing it
  - `node` - Node.js (updates package.json)
  - `python` - Python (updates pyproject.toml)
  - `rust` - Rust (updates Cargo.toml)
  - `helm` - Helm charts (updates Chart.yaml)
- [ ] Customize changelog sections if needed
- [ ] Remove `bootstrap-sha`. It is a one-time migration boundary for this template's own history and points at
      a commit that does not exist in your repository

### `.release-please-manifest.json`

- [ ] Set initial version (default: `0.0.0`)
- [ ] Set `version.txt` to the same version when using the default `simple` release type

### Conventional Commits (Required)

This template uses conventional commits for automatic versioning:

| Prefix | Version Bump | Release notes | Example |
|--------|--------------|---------------|---------|
| `feat:` | Minor | Features | `feat: add user authentication` |
| `fix:` | Patch | Bug Fixes | `fix: resolve login timeout` |
| `feat!:` or `fix!:` | Major (minor below 1.0.0) | Breaking Changes | `feat!: redesign API endpoints` |
| `docs:`, `perf:`, `refactor:`, `revert:` | Patch | Own section | `docs: update README` |
| `ci:`, `chore:`, `build:`, `style:`, `test:` | None on their own | Not shown | `chore: update dependencies` |

A section marked `hidden: true` in `changelog-sections` contributes nothing to the changelog, and release-please
skips a release whose changelog would be empty. That is what makes the last row "None" - and why a push mixing
one `docs:` with several `chore:` commits still cuts a patch. See [docs/RELEASES.md](docs/RELEASES.md).

### `.typos.toml`

- [ ] Add project-specific terms to `[default.extend-words]`
- [ ] Add project-specific file exclusions

---

## 7. Community Files

### `CODE_OF_CONDUCT.md`

- [ ] Review (usually no changes needed for CNCF CoC)
- [ ] Update if using a different Code of Conduct

### `SUPPORT.md`

- [ ] Replace all placeholder URLs
- [ ] Add/remove support channels as applicable

### `ROADMAP.md`

- [ ] Replace all placeholder URLs
- [ ] Link to your actual project board

### `CHANGELOG.md`

- [ ] Clear template content
- [ ] Add your project's changelog entries

### `README.md`

- [ ] **Delete this template README entirely**
- [ ] Create your own project README

### `LICENSE`

- [ ] Update copyright year and holder
- [ ] Change license type if not using Apache 2.0

---

## 8. Application Files

### `go.mod`

- [ ] Update module path to your project
- [ ] Update Go version if needed

### `Dockerfile`

- [ ] Update for your application structure
- [ ] Adjust build commands as needed

### `main.go`

- [ ] Replace with your application code

---

## 9. Optional Additions

Consider adding based on your project needs:

- [ ] `CONTRIBUTING.md` - Detailed contribution guide
- [ ] `GOVERNANCE.md` - Project governance documentation
- [ ] `SECURITY.md` - Security policy (GitHub auto-detects)
- [ ] `CODEOWNERS` - Automatic PR reviewers
- [ ] `.github/FUNDING.yml` - Sponsor button configuration
- [ ] `.github/dependabot.yml` - Automated dependency updates
- [ ] `.pre-commit-config.yaml` - Pre-commit hooks

---

## 10. Files to Delete

Remove these template-specific files:

- [ ] `CHECKLIST.md` (this file)
- [ ] Any unused workflow files

---

## 11. Verification

After setup, verify everything works:

- [ ] Open a test issue - form should render correctly
- [ ] Open a test PR - should receive auto-labels
- [ ] Check Actions tab - workflows should run
- [ ] Verify spell check passes
- [ ] Verify dco2 app is installed and running on PRs
- [ ] Push a commit with `feat: test feature` - should create/update Release PR
- [ ] Merge Release PR - should create GitHub Release and update CHANGELOG.md
- [ ] Confirm the release created a `vX.Y.Z` tag and updated `version.txt` (or the configured language version file)

---

## 12. Local Development Setup (Optional)

Run CI checks locally before committing using [Task](https://taskfile.dev/) and [lefthook](https://github.com/evilmartians/lefthook).

### Installation

```bash
# Install Task (task runner)
brew install go-task/tap/go-task

# Install lefthook (git hooks manager)
brew install lefthook

# Or with Go
go install github.com/go-task/task/v3/cmd/task@latest
go install github.com/evilmartians/lefthook@latest
```

### Available Commands

| Command | Description |
|---------|-------------|
| `task check` | Run all pre-commit checks |
| `task spellcheck` | Run spell checker (mirrors CI) |
| `task dco-check` | Check commits have DCO sign-off |
| `task license-check` | Check Go dependency licenses |
| `task setup` | Install tools and git hooks |
| `./scripts/export-settings.sh` | Export current repo settings to YAML |

### Setup

```bash
# Install tools and git hooks
task setup

# Verify hooks are installed
lefthook list
```

### How It Works

- **Taskfile.yml** - Defines explicit commands you can run manually
- **lefthook.yml** - Configures automatic git hooks (pre-commit, commit-msg)

Hooks run automatically:
- **pre-commit**: Spell check on staged `.md`, `.yml`, `.yaml` files
- **commit-msg**: Verify DCO sign-off is present

### Customization for Other Languages

For non-Go projects, replace the `license-check` task in `Taskfile.yml`:

**Python:**
```yaml
license-check:
  desc: Check Python dependency licenses
  cmds:
    - pip-licenses --fail-on="GPL;LGPL"
  status:
    - '! test -f requirements.txt'
```

**Node.js:**
```yaml
license-check:
  desc: Check npm dependency licenses
  cmds:
    - npx license-checker --failOn "GPL;LGPL"
  status:
    - '! test -f package.json'
```

---

## Quick Start Commands

```bash
# 1. Copy template files to your repo
cp -r .github /path/to/your/repo/
cp CODE_OF_CONDUCT.md SUPPORT.md ROADMAP.md CHANGELOG.md /path/to/your/repo/
cp release-please-config.json .release-please-manifest.json version.txt /path/to/your/repo/
cp -r docs /path/to/your/repo/
# Taskfile.yml and lefthook.yml are required: release-assets.yml runs `task release-assets`,
# and the local checks that mirror CI are defined there.
cp Taskfile.yml lefthook.yml .typos.toml /path/to/your/repo/

# 2. Replace placeholders (customize these values)
cd /path/to/your/repo
export ORG="your-org"
export REPO="your-repo"
export DOCS="https://docs.example.com"
export SLACK="https://slack.example.com"
export HOME_URL="https://example.com"

find . -type f \( -name "*.yml" -o -name "*.md" \) -exec sed -i '' \
  -e "s/{{ORG_NAME}}/$ORG/g" \
  -e "s/{{REPO_NAME}}/$REPO/g" \
  -e "s|{{DOCS_URL}}|$DOCS|g" \
  -e "s|{{SLACK_URL}}|$SLACK|g" \
  -e "s|{{HOMEPAGE_URL}}|$HOME_URL|g" \
  {} \;

# 3. Commit
git add -A
git commit -s -m "chore: add GitHub repository configuration"
```
