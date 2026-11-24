# Contributing

Thanks for taking the time to contribute.

By contributing you agree that your contribution is licensed under the terms in [LICENSE](LICENSE).

## Before You Start

- Search [existing issues](https://github.com/{{ORG_NAME}}/{{REPO_NAME}}/issues) before opening a new one.
- For anything larger than a bug fix, open a [proposal](https://github.com/{{ORG_NAME}}/{{REPO_NAME}}/issues/new?template=proposal.yml)
  first. Agreeing on the approach before the code exists saves everyone a rewrite.
- Questions are welcome as issues, using the [question form](https://github.com/{{ORG_NAME}}/{{REPO_NAME}}/issues/new?template=question.yml).
- Never open a public issue for a security problem. Follow [SECURITY.md](SECURITY.md) instead.

## Local Setup

```bash
task setup   # installs the pinned tools and the git hooks
task check   # runs the same gates CI runs
```

`task --list` shows everything available. Tool versions come from `versions.env`, so a local run and a CI run
use the same binaries.

The git hooks installed by `task setup` check the commit message format and the sign-off before a
commit is created. They fail fast so CI does not have to.

## Vulnerabilities

CI scans the module dependency graph with [govulncheck](https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck).
Findings do not fail the job: the full report goes to the job summary, and a sticky pull request comment lists
only the findings that have a published fix, updated on every run and removed once nothing fixable is left.
A pull request from a fork gets a read-only token, so it gets the job summary and the artifact but no comment.
Only a scan that could not produce a usable report fails. Reproduce what CI reports with:

```bash
task vuln-report                     # writes vulnerability-check/report.md and comment.md
task vuln-report:check               # the scanner-health gate CI runs after the report
task vuln-check                      # plain govulncheck, non-zero on any finding
```

<!-- pack:chart:start -->
## Helm Chart

The chart lives in `deploy/chart` and has its own release line. `task helm:ci` runs everything `Chart CI` runs:
lint (helm, chart-testing, kube-linter, Artifact Hub metadata, values schema), a render, the helm-unittest
suite, a determinism check, a Trivy scan and a packaging dry run.

Adding a value means touching four places: `values.yaml` with a `# --` helm-docs comment, `values.schema.json`,
a test under `tests/`, and the README via `task helm:docs`. Scope chart-only pull requests `feat(chart):` or
`fix(chart):` and keep them inside `deploy/chart`; the `Chart Scope Paths` check fails a chart-scoped pull
request that also touches an app-release path, because that commit would bump the app version too.

<!-- pack:chart:end -->
## Commits

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) and every commit needs a
Developer Certificate of Origin sign-off:

```bash
git commit -s -m "fix: reject empty tag names"
```

The type prefix drives versioning and the changelog, so it is not cosmetic. See
[docs/RELEASES.md](docs/RELEASES.md) for what each type does to the version.

Missing a sign-off? `git commit --amend -s` for the last commit, or
`git rebase --signoff origin/main` for a branch.

## Pull Requests

- The pull request **title** must be a valid conventional-commit subject. The repository squash-merges, so that
  title becomes the commit on `main` and the changelog entry. Individual commit subjects inside the branch matter
  much less.
- Keep the change focused. A pull request that fixes one thing gets reviewed; one that fixes five gets parked.
- Update documentation in the same pull request as the behaviour it describes.
- Add or adjust tests for behaviour changes.
- All required checks must pass. If a check is wrong, say so in the pull request rather than working around it.

## Release Notes

`feat:` and `fix:` pull requests end their description with a `## Release Notes` section. After a release
is published, `release-notes.yml` puts that text under the pull request's entry in the GitHub release, so
readers see each note next to the change it explains. It does not affect `CHANGELOG.md`.

```markdown
## Release Notes

Adds federated OIDC support. Configure it with the new `federated_oidc` key;
see the [OIDC documentation](https://docs.example.com/oidc).
```

**Write notes when, without them, someone running the project would act differently after upgrading or be
surprised by what changed.** For `feat:` that is almost always the case. A `fix:` qualifies when at least
one of these holds:

- **Action needed**: users change config, migrate, clean up or re-check something
- **Behaviour change**: something works differently or stops working, or a default or permission changes
- **New decision**: the fix adds a setting users may want to set
- **Security fix** with an advisory (GHSA or CVE)
- **Visible failure gone**: an outage, data loss or regression users noticed and may have worked around

Otherwise write `N/A`: internal fixes without a visible symptom, refactors, plumbing, dependency bumps
without a CVE, and bugs that never shipped in a release.

**Rules** (the `PR Release Notes` check enforces them):

- `feat:` and `fix:` pull requests need the section; its content is the notes or `N/A`. Breaking changes
  (`feat!:`, `fix!:`) need notes
- At most 550 characters as rendered; link targets, images and Markdown markers do not count. Put details in
  the docs and link to them
- Last section of the description, with no headings inside. Any heading ends the section, so `### Tests`
  placed below it is not published
- No alert boxes such as `> [!NOTE]`; they do not render inside the release's change list. Use plain text or
  **bold**

## Review

Maintainers are listed in [MAINTAINERS.md](MAINTAINERS.md). Reviews aim to be useful rather than fast; ping the
pull request if it has gone quiet for a week.

## Code of Conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
