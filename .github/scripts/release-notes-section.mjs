// The `## Release Notes` section of a pull request description: how the
// release pipeline reads it and how the PR check validates it.

export const MAX_RENDERED_LENGTH = 550;

const HEADING = /^##\s+release notes\s*$/i;
const ANY_HEADING = /^\s{0,3}#{1,6}(?:[ \t]|$)/;
const EMPTY = /^_?(?:none|n\/a|tbd)_?[.!]?$/i;

export function stripHtmlComments(text) {
  let previous;
  do {
    previous = text;
    text = text.replace(/<!--[\s\S]*?-->/g, '');
  } while (text !== previous);
  return text;
}

// Returns { found, text, trailingHeading }. `text` is '' when the section is
// missing, blank or explicitly N/A. Any heading ends the section, so reviewer
// notes placed below it never reach a release.
export function parseReleaseNotes(body) {
  const lines = (body ?? '').split(/\r?\n/);
  const start = lines.findIndex(line => HEADING.test(line.trim()));
  if (start === -1) {
    return { found: false, text: '', trailingHeading: undefined };
  }
  let end = lines.findIndex((line, index) => index > start && ANY_HEADING.test(line));
  const trailingHeading = end === -1 ? undefined : lines[end].trim();
  if (end === -1) {
    end = lines.length;
  }
  const text = stripHtmlComments(lines.slice(start + 1, end).join('\n')).trim();
  return { found: true, text: EMPTY.test(text) ? '' : text, trailingHeading };
}

// Length as a reader sees it on the release page: link targets, images,
// HTML tags and Markdown markers do not count.
export function renderedLength(text) {
  return text
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/<img\b[^>]*>/gi, '')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/^```.*$/gm, '')
    .replace(/`/g, '')
    .replace(/\*\*|__/g, '')
    .replace(/^\s*(?:[-*+]|\d+[.)]|>)\s+/gm, '')
    .replace(/\s+/g, ' ')
    .trim().length;
}

// Problems with a section that has content; an empty list means it is valid.
export function sectionProblems({ text, trailingHeading }) {
  const problems = [];
  if (trailingHeading) {
    problems.push(`"## Release Notes" must be the last section, but "${trailingHeading}" follows it.`);
  }
  if (/^\s*>\s*\[!\w+\]/m.test(text)) {
    problems.push('Alert boxes such as "> [!NOTE]" do not render inside the release changelog list; write the warning as plain text.');
  }
  const length = renderedLength(text);
  if (length > MAX_RENDERED_LENGTH) {
    problems.push(`Release notes are ${length} characters as rendered; the limit is ${MAX_RENDERED_LENGTH}. Link to docs for details.`);
  }
  return problems;
}
