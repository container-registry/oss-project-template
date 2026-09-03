# Repository Automation

What each piece of automation does, what it needs, and when it is safe to remove. Every workflow repeats the
short version of this in a header comment; this is the map.

## Workflows

| Workflow | What it does | Needs |
|----------|--------------|-------|
| `hygiene.yml` | Spelling, workflow lint, YAML lint, repository consistency, workflow security audit, action pin check, dependency review. Ends in a `required-checks` aggregate job. | nothing |
| `ci.yml` | Build, test, lint, tidy, licence check, vulnerability scan, and a container image smoke test. Skips itself without `go.mod`. | nothing |
| `codeql.yml` | Static analysis of the workflows and the Go code. | public repo, or Advanced Security |
| `dco.yml` | Fails a pull request whose commits lack a sign-off. | nothing |
| `scorecard.yml` | OpenSSF Scorecard. Skips on private repositories. | `SCORECARD_TOKEN` to also score branch protection |
| `pr-title.yml` | Requires a conventional-commit pull request title. | nothing |
| `labeler.yml`, `pr-size-labeler.yml` | Label pull requests by path and by size. | nothing |
| `welcome.yml` | Greets first-time contributors. | nothing |
| `apply-settings.yml` | Applies `.github/settings.yml`, and checks for drift weekly. | `SETTINGS_TOKEN` |
| `release-please.yml` | Opens release pull requests and triggers publishing. | nothing |
| `release-assets.yml` | Builds, attests and uploads binaries and their SBOM, from the commit the release tag resolves to. | nothing |
| `publish-image.yml` | Builds, pushes, verifies the platform set (`task image:verify`), signs and attests the container image, from the commit the release tag resolves to. | nothing for GHCR |

## Configuration

| File | Purpose |
|------|---------|
| `.github/settings.yml` | Repository settings, labels, security toggles and the branch ruleset, as code |
| `.github/labeler.yml` | Path to label mapping |
| `.github/dependabot.yml` | Dependency updates, including the action SHA pins |
| `.github/CODEOWNERS` | Automatic reviewer assignment |
| `.github/dco.yml` | dco2 app behaviour, if the app is installed |
| `versions.env` | Every tool version pin, read by both the Taskfile and CI |
| `.typos.toml`, `.yamllint`, `.golangci.yaml` | Linter configuration |
| `.release-please/config-app.json`, `.release-please/manifest-app.json`, `version.txt` | Release state. The directory is excluded from releases, so a second release line (a chart, say) can exclude the app line's state the same way |
| `optional/renovate.json` | Renovate config, as an alternative to Dependabot |

## Scripts

| File | Purpose |
|------|---------|
| `.github/scripts/apply-settings.js` | Applies, verifies or drift-checks `settings.yml`. Reads JSON the workflow converts, so it needs no YAML parser |
| `.github/scripts/repo-lint.py` | Repository consistency checks, also run by `task lint:repo` |

## Secrets

| Secret | Used by | Without it |
|--------|---------|------------|
| `SETTINGS_TOKEN` | `apply-settings.yml` | The job reports what it skipped and succeeds. `GITHUB_TOKEN` can only manage labels. |
| `SCORECARD_TOKEN` | `scorecard.yml` | Branch protection is not scored. Everything else works. |

Use a fine-grained personal access token scoped to this repository, with **Administration: read and write** and
**Metadata: read**.

## Things That Will Bite You

- **The release pull request gets no workflow runs.** GitHub raises no workflow events for a ref pushed with
  `GITHUB_TOKEN`. See [RELEASES.md](RELEASES.md) before making any check required.
- **Never require a path-filtered workflow as a status check.** It does not report at all on a pull request that
  misses its filter, and the check waits forever. Require `required-checks` instead.
- **`pull_request_target` workflows must never check out the pull request.** Three workflows use that trigger and
  say so; `repo-lint` fails the build if one ever gains a checkout step.
- **A `feat:` confined to an excluded path releases nothing.** `exclude-paths` is set to `docs`, `.github` and `.release-please`,
  and it is evaluated per file: one file outside pulls the whole commit back in.
- **An open release pull request only refreshes when its body would change.** `always-update: true` in
  `.release-please/config-app.json` forces a rewrite on every push to `main`. Do not remove it.
