// Exercise browser-facing copy success and denied/missing Clipboard API fallback.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
async function scenario(mode) {
  let handler, copied, selected = false;
  const button = { hidden: true, dataset: { copy: 'prompts' }, addEventListener: (_, action) => { handler = action; } };
  const content = { textContent: 'What happened?\n\nApp version and OS version\n' };
  const status = { textContent: '' };
  const context = {
    document: {
      querySelectorAll: () => [button],
      getElementById: id => id === 'copy-status' ? status : content,
      body: { dataset: { copied: 'Copied.', copyFailed: 'Select and copy.' } },
      createRange: () => ({ selectNodeContents: node => { assert.equal(node, content); } }),
    },
    navigator: mode === 'missing' ? {} : { clipboard: { writeText: async text => {
      if (mode === 'denied') throw new Error('Permission denied');
      copied = text;
    } } },
    window: { getSelection: () => ({ removeAllRanges() {}, addRange() { selected = true; } }) },
  };
  vm.runInNewContext(fs.readFileSync(__dirname + '/assets/support.js', 'utf8'), context);
  assert.equal(button.hidden, false);
  await handler();
  if (mode === 'success') {
    assert.equal(copied, content.textContent);
    assert.equal(status.textContent, 'Copied.');
    assert.equal(selected, false);
  } else {
    assert.equal(status.textContent, 'Select and copy.');
    assert.equal(selected, true);
    assert.equal(copied, undefined);
  }
}
(async () => {
  for (const mode of ['success', 'denied', 'missing']) await scenario(mode);
  console.log('Support copy success, denied permission and missing Clipboard API passed.');
})();
