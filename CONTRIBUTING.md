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

The git hooks installed by `task setup` check spelling, the commit message format, and the sign-off before a
commit is created. They fail fast so CI does not have to.

## Vulnerabilities

CI scans the module dependency graph with [govulncheck](https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck).
Findings do not fail the job: the full report goes to the job summary, and a sticky pull request comment lists
only the findings that have a published fix, updated on every run and removed once nothing fixable is left.
Only a scan that could not produce a usable report fails. Reproduce what CI reports with:

```bash
task vuln-report                     # writes vulnerability-check/report.md and comment.md
task vuln-check                      # plain govulncheck, non-zero on any finding
```


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

## Review

Maintainers are listed in [MAINTAINERS.md](MAINTAINERS.md). Reviews aim to be useful rather than fast; ping the
pull request if it has gone quiet for a week.

## Code of Conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
