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

- [ ] Update `name` to your repository name
- [ ] Update `description` to your project description
- [ ] Set `homepage` URL
- [ ] Set `default_branch` (usually `main`)
- [ ] Review merge strategies (`allow_squash_merge`, etc.)
- [ ] Uncomment and configure branch protection rules
- [ ] Add project-specific component labels

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

### `.github/workflows/dco.yml`

- [ ] No changes needed (or remove if not using DCO)

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

### `.github/workflows/release-drafter.yml`

- [ ] No changes needed (uses `release-drafter.yml` config)

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

### `.github/release-drafter.yml`

- [ ] Review categories and labels
- [ ] Customize release notes template
- [ ] Update autolabeler file patterns

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
- [ ] Verify DCO check works (if using)
- [ ] Create a draft release - release notes should populate

---

## Quick Start Commands

```bash
# 1. Copy template files to your repo
cp -r .github /path/to/your/repo/
cp CODE_OF_CONDUCT.md SUPPORT.md ROADMAP.md CHANGELOG.md /path/to/your/repo/
cp .typos.toml /path/to/your/repo/

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
