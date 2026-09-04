# Release Process

Releases are automated with [release-please](https://github.com/googleapis/release-please). Never push a
`v*` tag or create a GitHub Release by hand, and never edit `CHANGELOG.md`; release-please owns all three. The
repository squash-merges, so the pull request title is the commit release-please parses.

Release state is defined by conventional commits on `main`, the config and manifest in `.release-please/`, `version.txt` and `CHANGELOG.md`. The directory is itself in `exclude-paths`, so a commit confined to it does not contribute to a release, and a second release line can exclude it the same way.

<!-- pack:chart:start -->
There are **two independent release lines**, each with its own release-please instance, config, manifest,
changelog and tag namespace, both driven by the same `Release Please` workflow on every push to `main`:

| Line | Covers | Tag | Config and manifest | Changelog |
|------|--------|-----|---------------------|-----------|
| App | everything except `docs/`, `.github/`, `.release-please/`, `deploy/`, `taskfile/` | `vX.Y.Z` | `.release-please/config-app.json`, `manifest-app.json` | `CHANGELOG.md` |
| Chart | `deploy/chart/` | `chart-vX.Y.Z` | `.release-please/config-chart.json`, `manifest-chart.json` | `deploy/chart/CHANGELOG.md` |

They are separate so a chart fix does not force an app release that ships an identical binary, and an app
release does not republish the chart by itself. They are linked in one direction: the app line owns
`appVersion` in `deploy/chart/Chart.yaml` through the `x-release-please-version` marker, the chart line owns
`version`. Because the app release commit touches `Chart.yaml` and `chore` is visible in the chart changelog,
every app release also opens or refreshes the chart release pull request with a `release X.Y.Z` entry, and
merging that publishes a chart whose default image is the new app.
<!-- pack:chart:end -->

## How It Works

1. Pull requests are squash-merged to `main` with a conventional title. The title becomes the commit that release-please evaluates.
2. A push to `main` opens or updates a `chore: release X.Y.Z` pull request.
3. The release pull request updates the manifest, `CHANGELOG.md`, and the generic `version.txt` version file.
4. Merging that pull request creates the `vX.Y.Z` tag and GitHub Release.
<!-- pack:chart:start -->
5. The chart line does the same for commits under `deploy/chart/`: a `chore: release chart X.Y.Z` pull
   request bumps `.release-please/manifest-chart.json`, the chart changelog, `version` in `Chart.yaml` and the
   version in the chart `README.md`; merging it creates `chart-vX.Y.Z` and runs `publish-chart.yml`, which
   annotates `Chart.yaml` with the release image, packages the chart at that version, pushes it to
   `CHART_REPOSITORY`, signs it with cosign, pushes `artifacthub-repo.yml` as a sibling OCI artifact and
   appends the install section to the release notes.
<!-- pack:chart:end -->

| Commit type | Version bump | Release notes |
|-------------|--------------|---------------|
| `feat:` | Minor | Features |
| `fix:` | Patch | Bug Fixes |
| `feat!:`, `fix!:`, or a `BREAKING CHANGE:` footer | Major, or minor while the version is below `1.0.0` | Breaking Changes |
| `perf:`, `revert:`, `docs:`, `refactor:` | Patch | Own section |
| `ci:`, `chore:`, `build:`, `style:`, `test:` | None on their own | Not shown |
<!-- pack:chart:start -->

The chart line uses the same table with one difference: `chore:` is visible there, as Miscellaneous, and bumps
the patch version. That is what carries an app release (`chore: release X.Y.Z` touches `Chart.yaml`) into a
chart release. Which line sees a commit is decided by paths, not by scope: the app line ignores `docs/`,
`.github/`, `.release-please/`, `deploy/` and `taskfile/`, the chart line only sees `deploy/chart/`. A commit touching both opens both
release pull requests. Scope chart-only pull requests `feat(chart):` or `fix(chart):` and keep them inside
`deploy/chart`: one file the app line does not exclude puts the commit in the app changelog and bumps the app
version, and the `Chart Scope Paths` check in `pr-title.yml` fails such a pull request so it is split rather
than retyped.
When `exclude-paths` in `config-app.json` changes, update that check's patterns too.
<!-- pack:chart:end -->

Both columns are set by `changelog-sections` in `.release-please/config-app.json`, and the second drives the first.
A section marked `hidden: true` contributes no lines to the changelog entry, and release-please skips the
release outright when the entry comes out empty:

```ts
// release-please src/strategies/base.ts
if (!bumpOnlyOptions && this.changelogEmpty(releaseNotesBody)) {
  this.logger.info(`No user facing commits found since ... - skipping`);
  return undefined;
}
```

So the rule is about the release notes, not about the commit type:

- A push of only hidden types (`chore:`, `ci:`, ...) releases nothing.
- A push containing **any** visible commit cuts a release, and the bump is minor for `feat:`, major for a
  breaking change, and patch for everything else. One `docs:` alongside five `chore:` commits is a patch
  release, and the changelog shows only the `docs:` line.
- To make a type releasable, give it a visible section. To stop a change releasing regardless of its type,
  add its path to `exclude-paths`.

Confirm the bump you expect with a dry run before relying on it:

```bash
npx release-please release-pr --dry-run \
  --repo-url=<owner>/<repo> --config-file=.release-please/config-app.json \
  --manifest-file=.release-please/manifest-app.json
```

## The Version Baseline

release-please finds the previous release by looking for the tag matching the version in
`.release-please/manifest-app.json`. **The manifest version and the newest release tag must agree.** When they do
not, release-please finds no previous release, walks the whole history, and replays old commits into the next
changelog.

A repository created from this template starts clean: `task bootstrap` resets the manifest, `version.txt` and
`CHANGELOG.md` to zero, and a templated repository carries no tags, so the first `feat:` produces `v0.1.0`.
When adopting this setup into a repository that already has releases, set the manifest to the version of the
newest existing tag instead, and make sure that tag matches the `vX.Y.Z` scheme; push one at the release
commit if it does not.

## Adapt It to a Project

The template uses release-please's `simple` release type, which maintains `version.txt` and needs no
language-specific package file. Change `release-type` to `node`, `python`, `rust` or `helm` when release-please
should maintain the project's native manifest instead.

`go` is the exception. Go modules are versioned by tags, so that strategy maintains only the changelog and the
tag: its `version-file` option defaults to empty and the file updater is registered only when it is set.
Switching to `go` without setting `"version-file"` leaves `version.txt` frozen with nothing replacing it, and
the version stamped into release binaries goes stale with it.

`exclude-paths` is set to `docs`, `.github`, `.release-please`, `deploy` and `taskfile`, so a change confined to
those directories does not cut a release: documentation, workflows, issue templates, the settings file, the
release configuration and the chart change nothing that the app release ships. It covers those trees only: `README.md`, `CONTRIBUTING.md`, `SECURITY.md` and the other root documents sit outside
it, so a `docs:` commit touching those still produces a patch release, and a `fix:` to `Taskfile.yml` does
too. Add paths to `exclude-paths` if that is not what you want.

The inverse is the part that surprises people: a `feat:` whose every changed file sits under an excluded path
releases nothing, and it reads as release-please being broken rather than as configuration doing its job.

Add `extra-files` under `packages["."]` when the same version must be stamped into other files. The included release-assets workflow is a small Go example; customize or remove its call for other project types. Additional post-release jobs use:

```yaml
needs: [release-please]
if: ${{ needs.release-please.outputs.release_created == 'true' }}
```

The release job exposes `tag_name` (for example `v1.2.3`) and `version` (for example `1.2.3`) for publishing images, charts, binaries, or other artifacts. Keep artifact build and publish logic in Taskfile tasks so it can also run locally.

## Behaviour That Looks Like a Bug

Each of these cost a debugging session in a repository adopted from this template. None is a bug.

- **An open release pull request is refreshed only when its body would change.** Moving or renaming the
  config files, or changing `pull-request-header`, leaves the open pull request pointing at stale paths and
  the next push to `main` does not touch it. The config sets `always-update: true`, which makes every push
  rewrite the pull request. Keep it.
- **`release-as` in the config is permanent, not one-shot.** It applies to every release until it is removed,
  so the release after the one it was meant for proposes the same version again. Use it for exactly one
  release and remove it in that release's own pull request, or put a `Release-As: X.Y.Z` footer in a commit
  instead, which applies once.
- **`exclude-paths` is evaluated per file, and a commit is dropped only when every file it touches is
  excluded.** One file outside the excluded paths, even a one-line `README.md` edit in an otherwise
  workflow-only commit, pulls the whole commit into the changelog and bumps the version.
- **A hidden commit type cannot carry a release into another release-please package.** Only relevant with more
  than one release line: the `chore: release X.Y.Z` commit of one line is a `chore:` commit to the other,
  and with `chore` hidden there the second line sees an empty changelog and opens nothing. Make `chore`
  visible in the dependent line's config.

<!-- pack:chart:start -->
## Where the Chart Goes

`publish-chart.yml` pushes to `vars.CHART_REPOSITORY`, an OCI repository path without the chart name. Unset,
it is `ttl.sh/<owner>/<repo>/charts`: ttl.sh is anonymous and ephemeral, keeping an artifact for at most 24
hours, so a fresh repository proves the packaging, push, signing and release-notes path with no secret at all.
It is not where releases should live. For a real registry set the variable and the `CHART_REGISTRY_USERNAME`
and `CHART_REGISTRY_PASSWORD` secrets; the workflow header lists the GHCR mapping and the keyless variant for
registries that federate GitHub's OIDC identity. A manual dispatch may name another repository only on the
configured host, or on a host in `vars.CHART_REGISTRY_ALLOWLIST`.

Install and verify a published chart:

```bash
helm install <name> oci://<CHART_REPOSITORY>/<name> --version X.Y.Z
cosign verify <CHART_REPOSITORY>/<name>@<digest> \
  --certificate-identity-regexp '^https://github\.com/<org>/<repo>/\.github/workflows/publish-chart\.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

The release notes of every `chart-v*` release carry these commands with the real values.

<!-- pack:chart:end -->
## The Release Pull Request Gets No Workflow Runs

GitHub raises no workflow events for a ref pushed with `GITHUB_TOKEN`. release-please opens its
`chore: release X.Y.Z` pull request with exactly that token, so **that pull request gets zero workflow runs** -
no CI, no hygiene, no labeler.

This matters the moment a branch ruleset requires a status check: the release pull request waits for a context
that will never be reported and can never be merged. The shipped ruleset in `.github/settings.yml` therefore
requires a pull request but requires no status checks.

To require checks, first make release-please open its pull request as a GitHub App:

```yaml
- uses: actions/create-github-app-token@<sha>  # vX.Y.Z
  id: app-token
  with:
    app-id: ${{ vars.RELEASE_APP_ID }}
    private-key: ${{ secrets.RELEASE_APP_PRIVATE_KEY }}

- uses: googleapis/release-please-action@<sha>  # vX.Y.Z
  with:
    token: ${{ steps.app-token.outputs.token }}
```

Then require only the aggregate `required-checks` context from `hygiene.yml`. Never require a workflow that has
a `paths:` or `paths-ignore:` filter directly: it does not report at all on a pull request that misses the
filter, and the check waits forever.

Do not work around a blocked release pull request by pushing a tag by hand. The tag and
`.release-please/manifest-app.json` then disagree permanently, and every later release inherits the mismatch.

## Required Repository Settings

- Enable squash merging; disable merge commits and rebase merging.
- Allow GitHub Actions to create and approve pull requests.
- Keep `contents: write`, `pull-requests: write` and `issues: write` scoped to the release-please job. The
  workflow denies everything at the top level, so any job added there must request its own scopes.

These defaults are declared in `.github/settings.yml`. Applying administrative settings requires a `SETTINGS_TOKEN` with repository administration access.

## Maintainer Checklist

Before merging any pull request:

1. The title is a conventional commit, because the title is the squashed commit.
2. The merge method is squash.

Before merging a release pull request:

1. The proposed bump matches the commits since the last release (`feat:` minor, `fix:` patch, breaking
   change major). If it does not, the cause is usually a commit type or a path, see above; fix the config
   and push to `main`, the pull request rewrites itself.
2. `CHANGELOG.md`, `version.txt` and `.release-please/manifest-app.json` all show the new version.
3. `release-as` is absent from `.release-please/config-app.json`.
4. After the merge, the `Release Please` workflow completes and the release notes end with the verification
   commands.
<!-- pack:chart:start -->

Before merging a chart release pull request:

1. `deploy/chart/CHANGELOG.md`, `Chart.yaml` (`version`) and the chart `README.md` show the new chart version.
   A release pull request that does not touch the README means the restamp markers broke.
2. `appVersion` in `Chart.yaml` names an app release that has already been published; after an app release the
   chart changelog lists `release X.Y.Z` under Miscellaneous, which is expected.
3. `release-as` is absent from `.release-please/config-chart.json`.
<!-- pack:chart:end -->
