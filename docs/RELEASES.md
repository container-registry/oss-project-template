# Release Process

Releases are automated with [release-please](https://github.com/googleapis/release-please). Never push a
`v*` tag or create a GitHub Release by hand, and never edit `CHANGELOG.md`; release-please owns all three. The
repository squash-merges, so the pull request title is the commit release-please parses.

Release state is defined by conventional commits on `main`, `release-please-config.json`, `.release-please-manifest.json`, and `CHANGELOG.md`.

## How It Works

1. Pull requests are squash-merged to `main` with a conventional title. The title becomes the commit that release-please evaluates.
2. A push to `main` opens or updates a `chore: release X.Y.Z` pull request.
3. The release pull request updates the manifest, `CHANGELOG.md`, and the generic `version.txt` version file.
4. Merging that pull request creates the `vX.Y.Z` tag and GitHub Release.

| Commit type | Version bump | Release notes |
|-------------|--------------|---------------|
| `feat:` | Minor | Features |
| `fix:` | Patch | Bug Fixes |
| `feat!:`, `fix!:`, or a `BREAKING CHANGE:` footer | Major, or minor while the version is below `1.0.0` | Breaking Changes |
| `perf:`, `revert:`, `docs:`, `refactor:` | Patch | Own section |
| `ci:`, `chore:`, `build:`, `style:`, `test:` | None on their own | Not shown |

Both columns are set by `changelog-sections` in `release-please-config.json`, and the second drives the first.
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
  --repo-url=<owner>/<repo> --config-file=release-please-config.json \
  --manifest-file=.release-please-manifest.json
```

## The Version Baseline

release-please finds the previous release by looking for the tag matching the version in
`.release-please-manifest.json`. **The manifest version and the newest release tag must agree.** When they do
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

`exclude-paths` is set to `docs` and `.github`, so a change confined to those directories does not cut a
release: documentation, workflows, issue templates and the settings file change nothing that ships. It covers
those two trees only: `README.md`, `CONTRIBUTING.md`, `SECURITY.md` and the other root documents sit outside
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
`.release-please-manifest.json` then disagree permanently, and every later release inherits the mismatch.

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
2. `CHANGELOG.md`, `version.txt` and `.release-please-manifest.json` all show the new version.
3. `release-as` is absent from `release-please-config.json`.
4. After the merge, the `Release Please` workflow completes and the release notes end with the verification
   commands.
