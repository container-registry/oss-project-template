import { parseReleaseNotes, sectionProblems } from './release-notes-section.mjs';

// PR check for the `## Release Notes` section. Rules: CONTRIBUTING.md,
// "Adding Release Notes to Your PR". Reads PR_TITLE and PR_BODY.

const title = process.env.PR_TITLE ?? '';
const section = parseReleaseNotes(process.env.PR_BODY ?? '');
const [, type = '', breaking = ''] = title.match(/^(\w+)(?:\([^)]*\))?(!)?:/) ?? [];

const problems = [];
if (breaking && !section.text) {
  problems.push(`${type}!: PRs need a "## Release Notes" section that says what breaks and what users must do.`);
} else if ((type === 'feat' || type === 'fix') && !section.found) {
  problems.push(`${type}: PRs need a "## Release Notes" section: notes when users are affected, otherwise N/A.`);
}
if (section.text) {
  problems.push(...sectionProblems(section));
}

for (const problem of problems) {
  console.log(`::error title=Release Notes::${problem}`);
}
if (problems.length === 0) {
  console.log(section.text ? 'Release notes are valid.' : 'No release notes required.');
}
process.exitCode = problems.length === 0 ? 0 : 1;
