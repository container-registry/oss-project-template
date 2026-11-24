import assert from 'node:assert/strict';
import { test } from 'node:test';
import { checkProblems, inlineNotes, parseReleaseNotes, renderedLength } from './release-notes.mjs';

const body = notes => `Change.\n\n## Release Notes\n\n${notes}\n`;

test('reads the section up to the next heading', () => {
  const section = parseReleaseNotes('x\n## Release Notes\nUse `a`.\n## Testing\nran');
  assert.deepEqual(section, { found: true, notApplicable: false, text: 'Use `a`.', trailingHeading: '## Testing' });
});

test('ignores headings in code fences and HTML comments', () => {
  const section = parseReleaseNotes('```\n## Release Notes\n```\n<!--\n## Release Notes\n-->\n## Release Notes\n```sh\n# comment\n```');
  assert.equal(section.text, '```sh\n# comment\n```');
  assert.equal(section.trailingHeading, undefined);
});

test('an indented code block is not a heading', () => {
  assert.equal(parseReleaseNotes('    ## Release Notes\n    text').found, false);
});

test('N/A, also emphasised, means no note', () => {
  for (const value of ['N/A', 'n/a.', '**N/A**', '_N/A_']) {
    assert.deepEqual(checkProblems('fix: x', body(value)), [], value);
    assert.equal(parseReleaseNotes(body(value)).text, '', value);
  }
});

test('feat and fix need notes or N/A', () => {
  assert.equal(checkProblems('feat: x', 'no section').length, 1);
  assert.equal(checkProblems('fix(core): x', body('<!-- fill in -->')).length, 1);
  assert.equal(checkProblems('fix: x', body('TBD')).length, 0, 'TBD is a note, not a skip');
  assert.deepEqual(checkProblems('chore: x', 'no section'), []);
});

test('any breaking title needs real notes', () => {
  assert.equal(checkProblems('chore!: x', body('N/A')).length, 1);
  assert.deepEqual(checkProblems('feat(api)!: x', body('Drops v1.')), []);
});

test('the section must be last, even when N/A', () => {
  assert.equal(checkProblems('fix: x', 'a\n## Release Notes\nN/A\n### Testing\nok').length, 1);
});

test('rejects alert boxes and long notes', () => {
  assert.equal(checkProblems('feat: x', body('> [!NOTE]\n> hi')).length, 1);
  assert.equal(checkProblems('feat: x', body('a'.repeat(551))).length, 1);
  assert.deepEqual(checkProblems('feat: x', body(`[${'a'.repeat(550)}](https://example.test/long)`)), []);
});

test('rendered length skips markup', () => {
  assert.equal(renderedLength('**a** *b* ~~c~~ _d_ `e_f` [g](https://x.test)'), 'a b c d e_f g'.length);
});

const repo = 'acme/widget';
const url = n => `https://github.com/${repo}/pull/${n}`;
const bodies = { 1: body('One.'), 2: body('N/A'), 4: body('Original.'), 5: 'no section' };
const fetch = n => bodies[n];

test('puts notes under release-please and harbor style entries', () => {
  const release = [
    `* **core:** a ([#1](https://github.com/${repo}/issues/1)) ([abc](https://github.com/${repo}/commit/abc))`,
    `- b by @x in [#2](${url(2)})`,
    `- c (backport [#4](https://github.com/${repo}/issues/4)) by @x in [#5](${url(5)})`,
    '',
    '## Container Images',
  ].join('\n');
  assert.equal(inlineNotes(release, [repo], fetch), [
    release.split('\n')[0], '', '  One.', '', release.split('\n')[1],
    release.split('\n')[2], '', '  Original.', '', '## Container Images',
  ].join('\n'));
});

test('a re-run adds nothing', () => {
  const once = inlineNotes(`- a in [#1](${url(1)})\n`, [repo], fetch);
  assert.equal(inlineNotes(once, [repo], () => body(`see [#1](${url(1)})`)), once);
});

test('matches former repository names', () => {
  const release = `- a in [#1](https://github.com/acme/old/pull/1)`;
  assert.match(inlineNotes(release, [repo, 'acme/old'], fetch), /One\./);
});
