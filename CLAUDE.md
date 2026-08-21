# {{REPO_NAME}}

{{REPO_DESCRIPTION}}

## Commands

Everything runs through Task; `versions.env` pins the tool versions so a local run matches CI.

```bash
task setup    # install the pinned tools and the git hooks (once)
task check    # every gate CI runs
task --list   # everything else
```

Never inline a build or test command into a workflow. Add it to `Taskfile.yml` and have the workflow call
`task <name>`, or local and CI drift apart.

## Commits and pull requests

- Conventional commits, and every commit needs `git commit -s` (DCO). Both are enforced by git hooks and by CI.
- The repository squash-merges, so **the pull request title is the commit that lands** and the one
  release-please parses. Get the title right; individual commit subjects matter much less.
- `feat:` and `fix:` drive the version. See `docs/RELEASES.md`.
- Do not hand-edit `CHANGELOG.md`, and never push a `v*` tag by hand. release-please owns both.

## Things that will waste your time if you do not know them

- **Every GitHub Action must be pinned to a full 40-character SHA with a `# vX.Y.Z` comment.** A gate in
  `hygiene.yml` fails the build otherwise.
- **A `pull_request_target` workflow must never check out the pull request.** `repo-lint` fails the build if one
  does. Three workflows use that trigger and say why in their headers.
- **`.github/settings.yml` is applied to the live repository** on push to main. Treat it as production.
- **Never require a path-filtered workflow as a status check.** It does not report on a pull request that misses
  its filter and the check waits forever. Require the aggregate `required-checks` context.
- **The release pull request gets no workflow runs**, because GitHub raises no events for a ref pushed with
  `GITHUB_TOKEN`. See `docs/RELEASES.md` before changing required checks.
- Before adding a linter rule or a workflow, check `.github/scripts/repo-lint.py` — the repository-consistency
  checks live there rather than in shell, so they can be run and tested locally.

## Layout

`docs/repo-automation.md` maps every workflow, config file and secret, and says when each is safe to delete.
