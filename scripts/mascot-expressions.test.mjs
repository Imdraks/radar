import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { RADAR_EXPRESSIONS, RADAR_IDLE_EXPRESSIONS } from '../frontend/src/components/mascot/expressions.ts';

const requireFrontend = createRequire(new URL('../frontend/package.json', import.meta.url));
const ts = requireFrontend('typescript');
const { createElement } = requireFrontend('react');
const { renderToStaticMarkup } = requireFrontend('react-dom/server');
const source = readFileSync(new URL('../frontend/src/components/mascot/RadarFace.tsx', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
const exports = {};
new Function('require', 'exports', js)(name => {
  if (name.endsWith('.css')) return {};
  if (name === './expressions') return { RADAR_EXPRESSIONS, RADAR_IDLE_EXPRESSIONS };
  return requireFrontend(name);
}, exports);
const render = props => renderToStaticMarkup(createElement(exports.RadarFace, props));
const decode = text => text.replaceAll('&gt;', '>').replaceAll('&lt;', '<');
const part = (html, name, nested = false) => {
  const match = html.match(new RegExp(`class="radar-mascot-${name}"[^>]*>${nested ? '<span>' : ''}([^<]*)`));
  assert.ok(match, `Missing ${name}`);
  return decode(match[1]);
};

test('default face has two full stop eyes, balanced brows and a dash mouth', () => {
  const html = render({});
  assert.match(html, /data-expression="neutral"/);
  assert.equal(part(html, 'brow radar-mascot-brow-left'), '(');
  assert.equal(part(html, 'brow radar-mascot-brow-right'), ')');
  assert.equal(part(html, 'eye radar-mascot-eye-left', true), '.');
  assert.equal(part(html, 'eye radar-mascot-eye-right', true), '.');
  assert.equal(part(html, 'mouth'), '-');
});

test('all 44 requested expressions render real glyphs, including explicit states during focus', () => {
  assert.equal(Object.keys(RADAR_EXPRESSIONS).length, 44);
  for (const [expression, [lb, rb, le, re, mouth]] of Object.entries(RADAR_EXPRESSIONS)) {
    const html = render({ expression, attentive: true });
    assert.match(html, new RegExp(`data-expression="${expression}"`));
    assert.equal(part(html, 'brow radar-mascot-brow-left'), lb);
    assert.equal(part(html, 'brow radar-mascot-brow-right'), rb);
    for (const [side, eye] of [['left', le], ['right', re]]) {
      assert.equal(part(html, `eye radar-mascot-eye-${side}`, true), ['O', '0'].includes(eye) ? '.' : eye);
    }
    assert.equal(part(html, 'mouth'), mouth);
    assert.doesNotMatch(html, /<(svg|img|canvas)\b/);
  }
});

test('gaze moves only the eyes and keeps the mouth outside the gaze container', () => {
  const html = render({});
  assert.match(html, /class="radar-mascot-eye-life"/);
  assert.match(html, /<\/span><\/span><span class="radar-mascot-mouth"/);
});

test('idle never selects negative or monetary expressions', () => {
  assert.deepEqual(RADAR_IDLE_EXPRESSIONS, ['smile', 'satisfied', 'sleepy', 'yawn', 'wink']);
  assert.deepEqual(RADAR_EXPRESSIONS.happy, ['(', ')', '^', '^', '3']);
  assert.deepEqual(RADAR_EXPRESSIONS.angry, [')', '(', '>', '<', '-']);
  assert.deepEqual(RADAR_EXPRESSIONS.intrigued, ['(', '(', '.', 'O', '?']);
});
