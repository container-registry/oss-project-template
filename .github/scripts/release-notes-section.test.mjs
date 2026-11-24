import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MAX_RENDERED_LENGTH, parseReleaseNotes, renderedLength, sectionProblems } from './release-notes-section.mjs';

test('reads the section up to the end of the body', () => {
  const section = parseReleaseNotes('## Summary\n\nx\n\n## Release Notes\n\nUsers can now do Y.\n');
  assert.deepEqual(section, { found: true, text: 'Users can now do Y.', trailingHeading: undefined });
});

test('any heading ends the section', () => {
  const section = parseReleaseNotes('## Release Notes\n\nNote.\n\n### Tests\n\nnot published\n');
  assert.equal(section.text, 'Note.');
  assert.equal(section.trailingHeading, '### Tests');
});

test('N/A, blank and comment-only sections count as empty', () => {
  for (const body of ['## Release Notes\n\nN/A', '## Release Notes\n', '## Release Notes\n<!-- hint -->\n']) {
    assert.deepEqual(parseReleaseNotes(body), { found: true, text: '', trailingHeading: undefined });
  }
  assert.equal(parseReleaseNotes('## Summary\n\nx').found, false);
});

test('rendered length ignores link targets, images and markers', () => {
  assert.equal(renderedLength('See [the docs](https://example.com/a/very/long/path) for **details**.'), 'See the docs for details.'.length);
  assert.equal(renderedLength('![shot](https://example.com/x.png) `code`'), 'code'.length);
});

test('problems: trailing heading, alert box, length', () => {
  assert.equal(sectionProblems({ text: 'ok', trailingHeading: undefined }).length, 0);
  assert.match(sectionProblems({ text: 'ok', trailingHeading: '## Testing' })[0], /last section/);
  assert.match(sectionProblems({ text: '> [!NOTE]\n> careful', trailingHeading: undefined })[0], /Alert boxes/);
  assert.match(sectionProblems({ text: 'a'.repeat(MAX_RENDERED_LENGTH + 1), trailingHeading: undefined })[0], /limit is 550/);
});
