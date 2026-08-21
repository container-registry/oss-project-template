# Release Process

Releases are automated with [release-please](https://github.com/googleapis/release-please). Do not create release tags or GitHub Releases manually.

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
| `ci:`, `chore:`, `build:`, `style:`, `test:` | Patch | Not shown |

The `Release notes` column is set by `changelog-sections` in `release-please-config.json`. Marking a section
`hidden: true` removes it from the changelog; treat it as a presentation setting, not as a way to stop a commit
from producing a release. Confirm the bump you expect with a dry run before relying on it:

```bash
npx release-please release-pr --dry-run \
  --repo-url=<owner>/<repo> --config-file=release-please-config.json \
  --manifest-file=.release-please-manifest.json
```

## The Version Baseline

release-please finds the previous release by looking for the tag that matches the version in
`.release-please-manifest.json`. The template ships `0.0.0` in both the manifest and `version.txt`, so a new
repository starts from zero and the first `feat:` produces `v0.1.0`.

**If the repository already has releases, the manifest version and the newest `vX.Y.Z` tag must agree.** When they
do not -- for example after switching from component tags such as `app-v1.1.0` to plain `vX.Y.Z` -- release-please
finds no matching tag, walks the whole history, and repeats old commits in the next changelog. Fix it before the
first release by either:

- tagging the existing release commit with the matching tag (`git tag v1.1.0 <sha> && git push origin v1.1.0`), or
- setting `"bootstrap-sha"` in `release-please-config.json` to the commit the history should start from, then
  removing that key once the first release under the new scheme has been cut.

## Adapt It to a Project

The template uses release-please's `simple` release type so it works without a language-specific package file. Change `release-type` when the project should update a native version file, for example `go`, `node`, `python`, `rust`, or `helm`.

Add `extra-files` under `packages["."]` when the same version must be stamped into other files. The included release-assets workflow is a small Go example; customize or remove its call for other project types. Additional post-release jobs use:

```yaml
needs: [release-please]
if: ${{ needs.release-please.outputs.release_created == 'true' }}
```

The release job exposes `tag_name` (for example `v1.2.3`) and `version` (for example `1.2.3`) for publishing images, charts, binaries, or other artifacts. Keep artifact build and publish logic in Taskfile tasks so it can also run locally.

## Required Repository Settings

- Enable squash merging; disable merge commits and rebase merging.
- Allow GitHub Actions to create and approve pull requests.
- Keep `contents: write` and `pull-requests: write` scoped to the release-please job.

These defaults are declared in `.github/settings.yml`. Applying administrative settings requires a `SETTINGS_TOKEN` with repository administration access.
