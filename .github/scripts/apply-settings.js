const fs = require('fs')
const yaml = require('js-yaml')

module.exports = async ({ github, context, core }) => {
  const { owner, repo } = context.repo
  const settings = yaml.load(fs.readFileSync('.github/settings.yml', 'utf8'))
  const mode = process.env.INPUT_MODE || (context.eventName === 'schedule' ? 'check' : 'verify')
  core.info(`Mode: ${mode}`)

  // Sections whose current state the token was not allowed to read. They are
  // dropped from BOTH sides of the drift comparison: "cannot read" is not
  // "differs", and settings.yml always carries these keys, so comparing them
  // against an absent export would report drift forever.
  let unreadable = new Set()

  // Apply repository settings
  async function applyRepository() {
    if (!settings.repository) return
    await github.rest.repos.update({ owner, repo, ...settings.repository })
    core.info('✓ repository')
  }

  // Apply default GitHub Actions workflow permissions
  async function applyActions() {
    if (!settings.actions) return
    await github.request('PUT /repos/{owner}/{repo}/actions/permissions/workflow', {
      owner, repo, ...settings.actions
    })
    core.info('✓ actions')
  }

  // Apply labels (create or update)
  async function applyLabels() {
    if (!settings.labels) return
    const { data: existing } = await github.rest.issues.listLabelsForRepo({ owner, repo, per_page: 100 })
    const existingNames = new Set(existing.map(l => l.name))
    for (const [name, config] of Object.entries(settings.labels)) {
      if (existingNames.has(name)) {
        await github.rest.issues.updateLabel({ owner, repo, name, ...config })
      } else {
        await github.rest.issues.createLabel({ owner, repo, name, ...config })
      }
    }
    core.info('✓ labels')
  }

  // Apply security settings
  async function applySecurity() {
    if (!settings.security) return
    await github.rest.repos.update({ owner, repo, security_and_analysis: settings.security })
    core.info('✓ security')
  }

  // Apply code scanning default setup
  async function applyCodeScanning() {
    if (!settings.code_scanning || settings.code_scanning.state !== 'configured') return
    await github.request('PATCH /repos/{owner}/{repo}/code-scanning/default-setup', {
      owner, repo, ...settings.code_scanning
    })
    core.info('✓ code_scanning')
  }

  // Apply rulesets (create or update)
  async function applyRulesets() {
    if (!settings.rulesets) return
    let existing = []
    try {
      const response = await github.rest.repos.getRepoRulesets({ owner, repo })
      existing = response.data
    } catch (e) {
      // No rulesets exist
    }
    const existingMap = Object.fromEntries(existing.map(r => [r.name, r.id]))
    for (const [name, config] of Object.entries(settings.rulesets)) {
      if (existingMap[name]) {
        await github.rest.repos.updateRepoRuleset({ owner, repo, ruleset_id: existingMap[name], name, ...config })
      } else {
        await github.rest.repos.createRepoRuleset({ owner, repo, name, ...config })
      }
    }
    core.info('✓ rulesets')
  }

  // Apply branch protection
  async function applyBranches() {
    if (!settings.branches) return
    for (const [branch, config] of Object.entries(settings.branches)) {
      if (config.protection) {
        await github.rest.repos.updateBranchProtection({ owner, repo, branch, ...config.protection })
      }
    }
    core.info('✓ branches')
  }

  // Apply environments
  async function applyEnvironments() {
    if (!settings.environments) return
    for (const [envName, config] of Object.entries(settings.environments)) {
      await github.rest.repos.createOrUpdateEnvironment({ owner, repo, environment_name: envName, ...config })
    }
    core.info('✓ environments')
  }

  // Apply all settings.
  //
  // Every section is attempted even if an earlier one fails, so one permission
  // gap does not hide the state of the rest -- but the failures are collected
  // and the job fails. A section that silently did not apply is drift that the
  // next `check` run would report against a repo nobody knowingly changed.
  async function applyAll() {
    const sections = [
      ['repository', applyRepository, true],
      ['actions', applyActions, true],
      ['labels', applyLabels, false],
      ['security', applySecurity, true],
      ['code_scanning', applyCodeScanning, false],
      ['rulesets', applyRulesets, true],
      ['branches', applyBranches, true],
      ['environments', applyEnvironments, true]
    ]

    const failures = []
    for (const [name, apply, needsAdmin] of sections) {
      try {
        await apply()
      } catch (e) {
        const hint = needsAdmin && (e.status === 403 || e.status === 404) ? ' (needs SETTINGS_TOKEN?)' : ''
        failures.push(`${name}: ${e.message}${hint}`)
        core.error(`\u2717 ${name}: ${e.message}${hint}`)
      }
    }

    if (failures.length > 0) {
      core.setFailed(`Failed to apply ${failures.length} of ${sections.length} section(s):\n  ${failures.join('\n  ')}`)
    }
    return failures.length === 0
  }

  // Export current settings from GitHub
  async function exportSettings() {
    unreadable = new Set()

    // 403/401 means the token may not read this section; anything else (404,
    // 422) means the feature is genuinely not configured, which is a real
    // value to compare against.
    const markIfForbidden = (section, e) => {
      if (e.status === 403 || e.status === 401) {
        unreadable.add(section)
        core.warning(`Cannot read ${section}: ${e.message}. Excluded from drift comparison.`)
      }
    }

    const { data: r } = await github.rest.repos.get({ owner, repo })
    const { data: labels } = await github.rest.issues.listLabelsForRepo({ owner, repo, per_page: 100 })

    let actionsData
    try {
      const actions = await github.request('GET /repos/{owner}/{repo}/actions/permissions/workflow', { owner, repo })
      actionsData = actions.data
    } catch (e) {
      markIfForbidden('actions', e)
    }

    let codeScanningData = {}
    try {
      const cs = await github.request('GET /repos/{owner}/{repo}/code-scanning/default-setup', { owner, repo })
      codeScanningData = cs.data
    } catch (e) {
      markIfForbidden('code_scanning', e)
    }

    let rulesetsData = []
    try {
      const rs = await github.rest.repos.getRepoRulesets({ owner, repo })
      rulesetsData = rs.data
    } catch (e) {
      markIfForbidden('rulesets', e)
    }

    let branchProtection = null
    try {
      const bp = await github.rest.repos.getBranchProtection({ owner, repo, branch: r.default_branch })
      branchProtection = bp.data
    } catch (e) {
      markIfForbidden('branches', e)
    }

    let environmentsData = []
    try {
      const envs = await github.rest.repos.getAllEnvironments({ owner, repo })
      environmentsData = envs.data.environments || []
    } catch (e) {
      markIfForbidden('environments', e)
    }

    const result = {
      repository: {
        description: r.description,
        homepage: r.homepage || '',
        topics: r.topics,
        visibility: r.visibility,
        has_issues: r.has_issues,
        has_projects: r.has_projects,
        has_wiki: r.has_wiki,
        has_downloads: r.has_downloads,
        has_discussions: r.has_discussions,
        is_template: r.is_template,
        default_branch: r.default_branch,
        allow_forking: r.allow_forking,
        allow_squash_merge: r.allow_squash_merge,
        allow_merge_commit: r.allow_merge_commit,
        allow_rebase_merge: r.allow_rebase_merge,
        delete_branch_on_merge: r.delete_branch_on_merge,
        allow_auto_merge: r.allow_auto_merge,
        allow_update_branch: r.allow_update_branch,
        squash_merge_commit_title: r.squash_merge_commit_title,
        squash_merge_commit_message: r.squash_merge_commit_message,
        merge_commit_title: r.merge_commit_title,
        merge_commit_message: r.merge_commit_message,
        web_commit_signoff_required: r.web_commit_signoff_required
      },
      actions: actionsData ? {
        default_workflow_permissions: actionsData.default_workflow_permissions,
        can_approve_pull_request_reviews: actionsData.can_approve_pull_request_reviews
      } : undefined,
      labels: Object.fromEntries(labels.map(l => [l.name, { color: l.color, description: l.description || '' }])),
      security: r.security_and_analysis ? {
        secret_scanning: { status: r.security_and_analysis.secret_scanning?.status },
        secret_scanning_push_protection: { status: r.security_and_analysis.secret_scanning_push_protection?.status },
        dependabot_security_updates: { status: r.security_and_analysis.dependabot_security_updates?.status }
      } : undefined,
      code_scanning: codeScanningData.state ? {
        state: codeScanningData.state,
        query_suite: codeScanningData.query_suite,
        languages: codeScanningData.languages
      } : undefined
    }

    // Add rulesets if any exist
    if (rulesetsData.length > 0) {
      result.rulesets = Object.fromEntries(rulesetsData.map(rs => {
        const { id, node_id, source, created_at, updated_at, _links, current_user_can_bypass, name, ...rest } = rs
        return [name, rest]
      }))
    }

    // Add branch protection if configured
    if (branchProtection) {
      result.branches = {
        [r.default_branch]: {
          protection: {
            required_status_checks: branchProtection.required_status_checks ? {
              strict: branchProtection.required_status_checks.strict,
              contexts: branchProtection.required_status_checks.contexts
            } : null,
            enforce_admins: branchProtection.enforce_admins?.enabled,
            required_pull_request_reviews: branchProtection.required_pull_request_reviews ? {
              required_approving_review_count: branchProtection.required_pull_request_reviews.required_approving_review_count,
              dismiss_stale_reviews: branchProtection.required_pull_request_reviews.dismiss_stale_reviews,
              require_code_owner_reviews: branchProtection.required_pull_request_reviews.require_code_owner_reviews
            } : null,
            restrictions: null,
            required_linear_history: branchProtection.required_linear_history?.enabled,
            allow_force_pushes: branchProtection.allow_force_pushes?.enabled,
            allow_deletions: branchProtection.allow_deletions?.enabled
          }
        }
      }
    }

    // Add environments if any exist
    if (environmentsData.length > 0) {
      result.environments = Object.fromEntries(environmentsData.map(env => {
        const { id, node_id, created_at, updated_at, html_url, name, ...rest } = env
        // Filter out empty values
        const filtered = Object.fromEntries(Object.entries(rest).filter(([, v]) => v != null && v !== '' && !(Array.isArray(v) && v.length === 0)))
        return [name, filtered]
      }))
    }

    return result
  }

  // Remove nulls and empty objects recursively
  function normalize(obj) {
    if (obj === null || obj === undefined) return undefined
    if (Array.isArray(obj)) {
      const filtered = obj.map(normalize).filter(v => v !== undefined)
      return filtered.length > 0 ? filtered : undefined
    }
    if (typeof obj === 'object') {
      const result = {}
      for (const [key, value] of Object.entries(obj)) {
        const normalized = normalize(value)
        if (normalized !== undefined) {
          result[key] = normalized
        }
      }
      return Object.keys(result).length > 0 ? result : undefined
    }
    return obj
  }

  // Sort object keys recursively for stable comparison
  function sortKeys(obj) {
    if (obj === null || obj === undefined) return obj
    if (Array.isArray(obj)) return obj.map(sortKeys)
    if (typeof obj === 'object') {
      return Object.keys(obj).sort().reduce((acc, key) => {
        acc[key] = sortKeys(obj[key])
        return acc
      }, {})
    }
    return obj
  }

  // Detect drift between settings.yml and GitHub
  async function detectDrift() {
    core.info('Exporting current GitHub settings...')
    const current = await exportSettings()

    const omit = (obj, keys) =>
      Object.fromEntries(Object.entries(obj || {}).filter(([k]) => !keys.has(k)))

    if (unreadable.size > 0) {
      core.warning(
        `Skipping drift check for section(s) this token cannot read: ${[...unreadable].sort().join(', ')}. ` +
        'Supply SETTINGS_TOKEN with admin access to verify them.'
      )
    }

    const expected = sortKeys(normalize(omit(settings, unreadable)))
    const actual = sortKeys(normalize(omit(current, unreadable)))

    const expectedJson = JSON.stringify(expected, null, 2)
    const actualJson = JSON.stringify(actual, null, 2)

    if (expectedJson === actualJson) {
      core.info('✓ No drift detected - settings.yml matches GitHub')
      return true
    }

    core.setFailed('Drift detected! settings.yml differs from GitHub state.')
    core.info('Expected:\n' + expectedJson)
    core.info('Actual:\n' + actualJson)
    return false
  }

  // Main execution
  if (mode === 'check') {
    core.startGroup('Checking for drift')
    await detectDrift()
    core.endGroup()
  } else if (mode === 'apply') {
    core.startGroup('Applying settings')
    await applyAll()
    core.endGroup()
  } else { // verify
    core.startGroup('Applying settings')
    await applyAll()
    core.endGroup()
    core.startGroup('Verifying settings were applied')
    await new Promise(r => setTimeout(r, 2000)) // Allow API to propagate
    await detectDrift()
    core.endGroup()
  }
}
