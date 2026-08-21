# {{REPO_NAME}}

{{REPO_DESCRIPTION}}

<!-- template-only:start -->
> This repository is a template. Create a repository from it, run `task bootstrap`, and this banner and the
> template sections below disappear. See [CHECKLIST.md](CHECKLIST.md) for the decisions bootstrap cannot make
> for you.

## Using This Template

```bash
gh repo create {{ORG_NAME}}/my-project --template {{ORG_NAME}}/{{REPO_NAME}} --private --clone
cd my-project
task bootstrap          # prompts, or pass --org-name etc; --lang=none drops the Go pack
task check              # the same gates CI runs
```

`task bootstrap` substitutes every placeholder, drops optional links you left blank, removes the packs you did
not select, records which template commit you started from in `.github/template.yml`, deletes itself and
CHECKLIST.md, and then runs the consistency checks so a half-applied template fails loudly.

### What You Get

- **Working CI on the first push.** Spelling, workflow lint and security audit, YAML lint, dependency review,
  repository consistency, and for Go a build, race-enabled tests, lint, tidy check, licence check, vulnerability
  scan and a container image smoke test.
- **Releases without ceremony.** Conventional commits drive the version, the changelog, the tag, the GitHub
  release, signed multi-arch images, SBOMs and build provenance.
- **Security defaults that are on.** Secret scanning with push protection, private vulnerability reporting,
  Dependabot, CodeQL, a branch ruleset, and a `SECURITY.md` with a real disclosure policy.
- **Settings as code.** Labels, merge strategy, security toggles and the ruleset live in
  `.github/settings.yml`, are applied automatically, and are drift-checked weekly.
- **Every action pinned to a SHA**, enforced by a gate, and kept current by Dependabot.

### Decisions Already Made

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

### After Adoption

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

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Repository automation is documented in
[docs/repo-automation.md](docs/repo-automation.md), and the release process in [docs/RELEASES.md](docs/RELEASES.md).

## Security

Report vulnerabilities privately. See [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
