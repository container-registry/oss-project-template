# {{REPO_NAME}}

{{REPO_DESCRIPTION}}

<!-- template-only:start -->
> This repository is a template. Create a repository from it, run `task bootstrap`, and this banner and the
> template sections below disappear. See [CHECKLIST.md](CHECKLIST.md) for the decisions bootstrap cannot make
> for you.

Repository configuration and automation for small open-source projects that want the engineering hygiene of a
large one without a platform team. It is the template behind the
[container-registry](https://github.com/container-registry) projects, among them
[harbor-next](https://github.com/container-registry/harbor-next) and the goharbor
[Trivy scanner adapter](https://github.com/goharbor/harbor-scanner-trivy), so every gate in it is exercised by
real pull requests rather than hypothetical ones.

## When It Fits

The template is deliberately opinionated. It assumes your project looks like this:

- **Hosted on GitHub, GitHub-native.** Actions, Dependabot, CodeQL, GHCR. The only external service assumed
  is GitHub itself; there is nothing to sign up for.
- **One repository, one deliverable.** A single Taskfile, release stream and changelog. Not a monorepo.
- **A small maintainer team, often one person.** Automation stands in for the reviewer you do not have:
  merges default to zero required approvals, and bots handle labels, releases and settings drift.
- **Go first, but not Go only.** The Go pack builds, tests and ships a signed multi-arch container image.
  `task bootstrap --lang=none` drops it and keeps everything else for any language.
- **A Helm chart with its own release line.** The chart pack lints, unit-tests, scans and publishes a signed
  OCI chart, versioned independently of the app. `task bootstrap --chart=none` drops it.
- **Releases nobody cuts by hand.** Conventional commits, squash merge and release-please decide the version,
  changelog, tag, GitHub release, images, SBOMs and provenance.

It is a poor fit if you want merge commits, free-form commit messages, manual versioning, a monorepo, or a
forge other than GitHub. Those are load-bearing assumptions, not defaults you flip.

## Using This Template

```bash
gh repo create <your-org>/my-project --template container-registry/oss-project-template --private --clone
cd my-project
task bootstrap          # prompts, or pass --org-name etc; --lang=none drops the Go pack, --chart=none the chart
task check              # the same gates CI runs
```

`task bootstrap` substitutes every placeholder, drops optional links you left blank, removes the packs you did
not select, records which template commit you started from in `.github/template.yml`, deletes itself and
CHECKLIST.md, and then runs the consistency checks so a half-applied template fails loudly.

## Features

- **Working CI on the first push.** Spelling, workflow lint, workflow security audit, YAML lint, dependency
  review, and repository-consistency checks that keep the template's own rules enforced.
- **A complete Go pack.** Build, race-enabled tests, lint, tidy check, licence check, vulnerability scan and a
  container image smoke test. It skips itself when there is no `go.mod`.
- **Releases without ceremony.** Conventional commits drive the version, the changelog, the tag, the GitHub
  release, signed multi-arch images, SBOMs and build provenance. See [docs/RELEASES.md](docs/RELEASES.md).
- **A chart pack that proves itself.** helm lint, chart-testing, kube-linter, Artifact Hub metadata, a closed
  values schema, helm-unittest, a GitOps determinism check, Trivy, and a release that packages, pushes and
  signs the chart. It publishes to ttl.sh until you point it at a registry, so the flow works with zero secrets.
- **Security defaults that are on.** Secret scanning with push protection, private vulnerability reporting,
  Dependabot, CodeQL, OpenSSF Scorecard, a branch ruleset, and a `SECURITY.md` with a real disclosure policy.
- **Settings as code.** Labels, merge strategy, security toggles and the ruleset live in
  `.github/settings.yml`, are applied automatically on push, and are drift-checked weekly.
- **Every action pinned to a full SHA**, enforced by a gate and kept current by Dependabot.
- **Local equals CI.** Task runs the same commands in both, `versions.env` pins the tool versions, and git
  hooks catch a failing gate before it reaches a pull request.
- **Contribution plumbing done.** DCO gate checked in-repo, conventional-commit PR titles, path and size
  labels, a first-contributor welcome, and issue and pull request templates.

Every workflow, config file and secret is mapped in [docs/repo-automation.md](docs/repo-automation.md), which
also says when each is safe to delete.

## Decisions Already Made

| Decision | Why |
|----------|-----|
| Conventional commits | Versioning and changelogs stop being a manual step |
| Squash merge only | One commit per pull request, so history stays bisectable |
| DCO sign-off | Provenance of contributions, checked in-repo rather than by an app |
| One support surface | Issues only. A second inbox a small team does not clear reads worse than none |
| Task, not Make | The same commands run locally and in CI, from one file |
| Tool versions in `versions.env` | A local run and a CI run use the same binaries |
| GitHub-native by default | The only external service assumed is GitHub itself |

Disagree with one? Each is a file or a line, and every workflow header says when it is safe to delete.

## After Adoption

Nothing pulls template changes automatically. `.github/template.yml` records the commit you started from, so it
is possible to ask which repositories are behind and which carry a defect already fixed here.

<!-- template-only:end -->

## Install

<!-- How to install or run the project. -->

## Usage

<!-- The shortest useful example. -->

## Development

```bash
task setup    # install the pinned tools and the git hooks
task check    # run the gates CI runs
task --list   # everything else
```

<!-- pack:chart:start -->
The Helm chart lives in `deploy/chart`; `task helm:ci` runs its whole quality gate.
<!-- pack:chart:end -->

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Repository automation is documented in
[docs/repo-automation.md](docs/repo-automation.md), and the release process in [docs/RELEASES.md](docs/RELEASES.md).

## Security

Report vulnerabilities privately. See [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
