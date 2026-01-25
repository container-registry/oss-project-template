#!/usr/bin/env bash
# export-settings.sh - Export current repository settings to YAML
#
# Usage: ./scripts/export-settings.sh > current-settings.yml

set -euo pipefail

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner')
DEFAULT_BRANCH=$(gh api "/repos/$REPO" --jq '.default_branch')

# Create temp files
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

gh api "/repos/$REPO" > "$TMP_DIR/repo.json"
gh api "/repos/$REPO/labels" --paginate > "$TMP_DIR/labels.json"
gh api "/repos/$REPO/branches/$DEFAULT_BRANCH/protection" 2>/dev/null > "$TMP_DIR/protection.json" || echo '{}' > "$TMP_DIR/protection.json"
gh api "/repos/$REPO/code-scanning/default-setup" 2>/dev/null > "$TMP_DIR/code_scanning.json" || echo '{}' > "$TMP_DIR/code_scanning.json"
gh api "/repos/$REPO/rulesets" 2>/dev/null > "$TMP_DIR/rulesets.json" || echo '[]' > "$TMP_DIR/rulesets.json"
gh api "/repos/$REPO/environments" 2>/dev/null > "$TMP_DIR/environments.json" || echo '{"environments":[]}' > "$TMP_DIR/environments.json"

cat <<'HEADER'
# Repository Settings
#
# YAML tree maps to GitHub API paths (base: /repos/{owner}/{repo}):
#   repository                   -> PATCH /repos/{owner}/{repo}
#   labels.{name}                -> PUT /repos/{owner}/{repo}/labels/{name}
#   branches.{name}.protection   -> PUT /repos/{owner}/{repo}/branches/{name}/protection
#   security                     -> PATCH /repos/{owner}/{repo} (security_and_analysis)
#   code_scanning                -> PATCH /repos/{owner}/{repo}/code-scanning/default-setup
#   rulesets.{name}              -> POST/PUT /repos/{owner}/{repo}/rulesets
#   environments.{name}          -> PUT /repos/{owner}/{repo}/environments/{name}
#
# Reference: https://docs.github.com/en/rest/repos

HEADER

jq -n \
  --slurpfile repo "$TMP_DIR/repo.json" \
  --slurpfile labels "$TMP_DIR/labels.json" \
  --slurpfile protection "$TMP_DIR/protection.json" \
  --slurpfile code_scanning "$TMP_DIR/code_scanning.json" \
  --slurpfile rulesets "$TMP_DIR/rulesets.json" \
  --slurpfile environments "$TMP_DIR/environments.json" \
  --arg branch "$DEFAULT_BRANCH" \
'($repo[0]) as $r | ($labels[0]) as $l | ($protection[0]) as $p | ($code_scanning[0]) as $cs | ($rulesets[0]) as $rs | ($environments[0].environments) as $envs |
{
  repository: {
    description: $r.description,
    homepage: ($r.homepage // ""),
    topics: $r.topics,
    visibility: $r.visibility,
    has_issues: $r.has_issues,
    has_projects: $r.has_projects,
    has_wiki: $r.has_wiki,
    has_downloads: $r.has_downloads,
    has_discussions: $r.has_discussions,
    is_template: $r.is_template,
    default_branch: $r.default_branch,
    allow_forking: $r.allow_forking,
    allow_squash_merge: $r.allow_squash_merge,
    allow_merge_commit: $r.allow_merge_commit,
    allow_rebase_merge: $r.allow_rebase_merge,
    delete_branch_on_merge: $r.delete_branch_on_merge,
    allow_auto_merge: $r.allow_auto_merge,
    allow_update_branch: $r.allow_update_branch,
    squash_merge_commit_title: $r.squash_merge_commit_title,
    squash_merge_commit_message: $r.squash_merge_commit_message,
    merge_commit_title: $r.merge_commit_title,
    merge_commit_message: $r.merge_commit_message,
    web_commit_signoff_required: $r.web_commit_signoff_required
  },
  labels: ($l | map({(.name): {color, description: (.description // "")}}) | add),
  security: {
    secret_scanning: {status: $r.security_and_analysis.secret_scanning.status},
    secret_scanning_push_protection: {status: $r.security_and_analysis.secret_scanning_push_protection.status},
    dependabot_security_updates: {status: $r.security_and_analysis.dependabot_security_updates.status}
  },
  code_scanning: (if $cs.state then {state: $cs.state, query_suite: $cs.query_suite, languages: $cs.languages} else null end),
  rulesets: (if ($rs | length) > 0 then ($rs | map({(.name): (del(.id, .node_id, .source, .created_at, .updated_at, ._links, .current_user_can_bypass, .name))}) | add) else null end),
  branches: (
    if $p.url then
      {($branch): {protection: {
        required_status_checks: (if $p.required_status_checks then {strict: $p.required_status_checks.strict, contexts: $p.required_status_checks.contexts} else null end),
        enforce_admins: $p.enforce_admins.enabled,
        required_pull_request_reviews: (if $p.required_pull_request_reviews then {
          required_approving_review_count: $p.required_pull_request_reviews.required_approving_review_count,
          dismiss_stale_reviews: $p.required_pull_request_reviews.dismiss_stale_reviews,
          require_code_owner_reviews: $p.required_pull_request_reviews.require_code_owner_reviews
        } else null end),
        restrictions: null,
        required_linear_history: $p.required_linear_history.enabled,
        allow_force_pushes: $p.allow_force_pushes.enabled,
        allow_deletions: $p.allow_deletions.enabled
      }}}
    else null end
  ),
  environments: (
    if ($envs | length) > 0 then
      ($envs | map({
        (.name): (del(.id, .node_id, .created_at, .updated_at, .html_url, .name) |
          with_entries(select(.value != null and .value != [])))
      }) | add)
    else null end
  )
} | with_entries(select(.value != null))' | yq -P '.'
