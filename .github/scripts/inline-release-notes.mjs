import { execFileSync } from 'node:child_process';
import { parseReleaseNotes } from './release-notes-section.mjs';

// Puts each pull request's `## Release Notes` section under that pull
// request's entry in a published GitHub release. Safe to re-run: an entry
// that already carries a note is left alone.
// Usage: inline-release-notes.mjs <tag>. Needs GH_TOKEN and GITHUB_REPOSITORY.

const [tag] = process.argv.slice(2);
const repository = process.env.GITHUB_REPOSITORY;
if (!tag || !repository) {
  throw new Error('usage: GITHUB_REPOSITORY=<owner/repo> inline-release-notes.mjs <tag>');
}

const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
// release-please links the squash-merged "(#N)" as an issue URL; the entry's
// own pull request is the last such link, after any the subject mentions.
const reference = new RegExp(`\\[#(\\d+)\\]\\(https://github\\.com/${escape(repository)}/(?:issues|pull)/\\1\\)`, 'g');
const LIST_ITEM = /^\s*[-*]\s+/;

function gh(args, input) {
  for (let attempt = 1; ; attempt++) {
    try {
      return execFileSync('gh', args, { encoding: 'utf8', input, stdio: ['pipe', 'pipe', 'pipe'] });
    } catch (error) {
      if (`${error.stderr ?? ''}`.includes('HTTP 404') || attempt === 5) {
        throw error;
      }
      console.error(`gh ${args.slice(0, 2).join(' ')} failed (attempt ${attempt}/5); retrying...`);
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, attempt * 2000);
    }
  }
}

function releaseNotesOf(number) {
  try {
    return parseReleaseNotes(JSON.parse(gh(['api', `repos/${repository}/pulls/${number}`])).body).text;
  } catch (error) {
    // The link names an issue, not a pull request.
    if (`${error.stderr ?? ''}`.includes('HTTP 404')) {
      return '';
    }
    throw error;
  }
}

const release = JSON.parse(gh(['api', `repos/${repository}/releases/tags/${tag}`]));
const lines = (release.body ?? '').split(/\r?\n/);
const output = [];
let added = 0;

for (const [index, line] of lines.entries()) {
  output.push(line);
  const number = LIST_ITEM.test(line) ? [...line.matchAll(reference)].at(-1)?.[1] : undefined;
  if (!number) {
    continue;
  }
  const indent = ' '.repeat(line.match(LIST_ITEM)[0].length);
  if (lines[index + 1] === '' && lines[index + 2]?.startsWith(indent) && lines[index + 2].trim()) {
    continue;
  }
  const text = releaseNotesOf(number);
  if (text) {
    // Continuation lines must be indented past the bullet, or the note,
    // and any code block or list inside it, falls out of the list item.
    output.push('', ...text.split('\n').map(noteLine => (noteLine ? indent + noteLine : '')), '');
    added++;
  }
}

if (added > 0) {
  gh(['api', '-X', 'PATCH', `repos/${repository}/releases/${release.id}`, '--input', '-'], JSON.stringify({ body: output.join('\n') }));
}
console.log(`${tag}: added ${added} release note(s).`);
