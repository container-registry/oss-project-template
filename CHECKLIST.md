# Adoption Checklist

`task bootstrap` does everything mechanical. This is what it cannot decide for you.

Work through it after bootstrap, before the first real pull request.

---

## 1. Decide, then edit

| Decision | Where | Default |
|----------|-------|---------|
| Who maintains this | `MAINTAINERS.md`, `.github/CODEOWNERS` | the handle you gave bootstrap |
| What the security scope is | `SECURITY.md`, the commented scope paragraph | generic |
| Which versions you support | `SECURITY.md`, supported-versions table | latest plus previous minor |
| Whether questions get a second inbox | `.github/settings.yml` → `has_discussions` | issues only |
| Whether a review is required to merge | `.github/settings.yml` → `required_approving_review_count` | 0, so a solo maintainer is not blocked |
| Which licences dependencies may use | `Taskfile.yml` → `license-check` | forbidden, restricted and unknown rejected |
| Dependabot or Renovate | `.github/dependabot.yml`, `optional/renovate.json` | Dependabot. Add Renovate limited to `versions.env` if hand-bumping tool pins gets old; never both on the same ecosystem |
| Whether to publish a Scorecard score | `.github/workflows/scorecard.yml` → `publish_results` | false |
| Where the Helm chart is published | `CHART_REPOSITORY` repository variable, `CHART_REGISTRY_USERNAME` / `CHART_REGISTRY_PASSWORD` secrets | `ttl.sh/<org>/<repo>/charts`, anonymous and gone within 24 hours. Fine for proving the flow, not for releases |

## 2. Repository setup

- [ ] Add a `SETTINGS_TOKEN` secret: a fine-grained token scoped to this repository, with **Administration:
      read and write** and **Metadata: read**. Without it `apply-settings` reports what it skipped and succeeds,
      and none of `.github/settings.yml` is applied.
- [ ] Run `gh workflow run apply-settings.yml -f mode=verify` and confirm labels, security toggles and the
      ruleset are applied.
- [ ] Confirm **Settings → Actions → Allow GitHub Actions to create and approve pull requests** is on, or
      release-please cannot open its release pull request.
- [ ] Link the project board in `ROADMAP.md` if one exists, or delete the file.
- [ ] Replace the `Install` and `Usage` sections in `README.md`.
- [ ] If you kept the chart pack: set `CHART_REPOSITORY` and the registry secrets, then put the Artifact Hub
      repository ID into `deploy/chart/artifacthub-repo.yml` once the repository is listed there. Until then
      chart releases go to ttl.sh.

## 3. Optional

- [ ] Install the [dco2 app](https://github.com/apps/dco2) for one-click sign-off remediation. `dco.yml` is the
      gate; the app is only nicer UX.
- [ ] `.github/FUNDING.yml` if the project takes sponsorship.
- [ ] `GOVERNANCE.md` once more than one organisation maintains the project. Before that it describes a process
      nobody follows.
- [ ] `ADOPTERS.md` once there are adopters worth naming.
- [ ] all-contributors, above roughly 20 contributors. Below that the GitHub contributors graph is enough.

## 4. Verify it works

- [ ] `task check` passes locally.
- [ ] Open a pull request titled `feat: smoke test`. Confirm it is labelled by path and by size, the title check
      passes, the DCO check passes, and `required-checks` is green.
- [ ] Merge it. Confirm release-please opens a release pull request.
- [ ] Merge that. Confirm the release carries binaries, `checksums.txt`, an SBOM, and the verification commands
      in its body, and that the image is signed:
      ```bash
      cosign verify ghcr.io/<org>/<repo>@<digest> \
        --certificate-identity-regexp '^https://github.com/<org>/<repo>/' \
        --certificate-oidc-issuer https://token.actions.githubusercontent.com
      ```
- [ ] `gh workflow run apply-settings.yml -f mode=check` reports no drift.
- [ ] If you kept the chart pack: open a pull request titled `feat(chart): smoke test` that touches only
      `deploy/chart/`. Confirm `Chart CI` runs and `Chart Scope Paths` passes, merge it, merge the
      `chore: release chart 0.1.0` pull request it opens, and confirm the chart release carries the install
      section and `cosign verify` succeeds against the chart digest.

## 5. Before making any check required

Read the release-pull-request section in [docs/RELEASES.md](docs/RELEASES.md) first. GitHub holds every workflow
run on a release pull request until a person approves it, because `github-actions[bot]` pushed the branch, so a
required status check turns each release into a manual approval. Require only the aggregate `required-checks`
context, and only after release-please opens its pull request with a GitHub App token.

---

Automation reference: [docs/repo-automation.md](docs/repo-automation.md).
