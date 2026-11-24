import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

// The `## Release Notes` section of a pull request description.
//   check                      validate PR_TITLE and PR_BODY
//   inline <file> <repo>...    put each entry's note under it in a release body;
//                              extra repos are former names the changelog links to

export const MAX_RENDERED_LENGTH = 550;

const SECTION = /^ {0,3}##[ \t]+release notes[ \t#]*$/i;
const HEADING = /^ {0,3}#{1,6}(?:[ \t]|$)/;
const FENCE = /^ {0,3}(?:`{3,}|~{3,})/;
const NOT_APPLICABLE = /^(\*{1,2}|_{1,2})?n\/a\1\.?$/i;

export function stripHtmlComments(text) {
  let result = '';
  let from = 0;
  for (;;) {
    const start = text.indexOf('<!--', from);
    if (start === -1) {
      return result + text.slice(from);
    }
    result += text.slice(from, start);
    const end = text.indexOf('-->', start + 4);
    if (end === -1) {
      return result;
    }
    from = end + 3;
  }
}

export function parseReleaseNotes(body) {
  const lines = stripHtmlComments(body ?? '').split(/\r?\n/);
  let fenced = false;
  let start = -1;
  let end = lines.length;
  for (const [index, line] of lines.entries()) {
    if (FENCE.test(line)) {
      fenced = !fenced;
    } else if (fenced) {
      continue;
    } else if (start === -1) {
      start = SECTION.test(line) ? index : -1;
    } else if (HEADING.test(line)) {
      end = index;
      break;
    }
  }
  if (start === -1) {
    return { found: false, notApplicable: false, text: '' };
  }
  const text = lines.slice(start + 1, end).join('\n').trim();
  const notApplicable = NOT_APPLICABLE.test(text);
  return { found: true, notApplicable, text: notApplicable ? '' : text, trailingHeading: lines[end]?.trim() };
}

export function renderedLength(text) {
  return text
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/^ {0,3}(?:`{3,}|~{3,}).*$/gm, '')
    .replace(/^\s*(?:[-*+]|\d+[.)]|>)\s+/gm, '')
    .replace(/[`*]|~~/g, '')
    .replace(/(^|\W)_+|_+(?=\W|$)/g, '$1')
    .replace(/\s+/g, ' ')
    .trim().length;
}

export function checkProblems(title, body) {
  const [, type = '', breaking = ''] = title.match(/^(\w+)(?:\([^)]*\))?(!)?:/) ?? [];
  const section = parseReleaseNotes(body);
  const required = breaking || type === 'feat' || type === 'fix';
  const problems = [];
  if (breaking && !section.text) {
    problems.push(`${type}!: PRs need a "## Release Notes" section that says what breaks and what users must do.`);
  } else if (required && !section.text && !section.notApplicable) {
    problems.push(`${type}: PRs need a "## Release Notes" section with notes, or N/A when users are not affected.`);
  }
  if (!section.found || !(required || section.text)) {
    return problems;
  }
  if (section.trailingHeading) {
    problems.push(`"## Release Notes" must be the last section, but "${section.trailingHeading}" follows it.`);
  }
  if (/^\s*>\s*\[!\w+\]/m.test(section.text)) {
    problems.push('Alert boxes such as "> [!NOTE]" do not render inside the changelog list; write plain text.');
  }
  const length = renderedLength(section.text);
  if (length > MAX_RENDERED_LENGTH) {
    problems.push(`Release notes are ${length} characters as rendered; the limit is ${MAX_RENDERED_LENGTH}. Link to docs for details.`);
  }
  return problems;
}

export function inlineNotes(markdown, repositories, fetchBody) {
  const repo = `https://github\\.com/(?:${repositories.map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`;
  const anyReference = new RegExp(`\\[#(\\d+)\\]\\(${repo}/(?:issues|pull)/\\1\\)`, 'g');
  // An entry title can name other pull requests; "in [#N]" is the entry's own.
  const ownReference = new RegExp(`\\bin \\[#(\\d+)\\]\\(${repo}/pull/\\1\\)`, 'g');
  const backportReference = new RegExp(`\\(backport \\[#(\\d+)\\]\\(${repo}/(?:issues|pull)/\\1\\)`, 'gi');
  const last = (line, pattern, skip) => [...line.matchAll(pattern)].map(match => match[1]).filter(n => n !== skip).at(-1);

  const notes = new Map();
  const noteOf = number => {
    if (!notes.has(number)) {
      notes.set(number, parseReleaseNotes(fetchBody(number)));
    }
    return notes.get(number);
  };

  const lines = markdown.split(/\r?\n/);
  const output = [];
  for (const [index, line] of lines.entries()) {
    output.push(line);
    // Notes are indented, so only unindented items are entries, and an entry
    // followed by indented text already has its note.
    const item = line.match(/^[-*]\s+/);
    if (!item || lines.slice(index + 1).find(next => next.trim())?.startsWith(' ')) {
      continue;
    }
    const backported = last(line, backportReference);
    const own = last(line, ownReference) ?? last(line, anyReference, backported);
    // A backport without a section of its own carries the original's note.
    const note = [own, backported].filter(Boolean).map(noteOf).find(section => section.found);
    if (note?.text) {
      const indent = ' '.repeat(item[0].length);
      output.push('', ...note.text.split('\n').map(noteLine => (noteLine ? indent + noteLine : '')), '');
    }
  }
  return output.join('\n').replace(/\n{3,}/g, '\n\n');
}

function pullRequestBody(repository, number) {
  for (let attempt = 1; ; attempt++) {
    try {
      return JSON.parse(execFileSync('gh', ['api', `repos/${repository}/pulls/${number}`], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })).body;
    } catch (error) {
      // The reference is an issue, not a pull request.
      if (`${error.stderr}`.includes('HTTP 404')) {
        return undefined;
      }
      if (attempt === 5) {
        throw error;
      }
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, attempt * 2000);
    }
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [command, file, ...repositories] = process.argv.slice(2);
  if (command === 'check') {
    const problems = checkProblems(process.env.PR_TITLE ?? '', process.env.PR_BODY ?? '');
    problems.forEach(problem => console.log(`::error title=Release Notes::${problem}`));
    process.exitCode = problems.length ? 1 : 0;
  } else if (command === 'inline' && file && repositories.length) {
    writeFileSync(file, inlineNotes(readFileSync(file, 'utf8'), repositories, n => pullRequestBody(repositories[0], n)));
  } else {
    throw new Error('usage: release-notes.mjs check | inline <file> <owner/repo> [former/name...]');
  }
}
