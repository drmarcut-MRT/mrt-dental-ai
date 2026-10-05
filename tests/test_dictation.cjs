const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../app/static/dictation.js'), 'utf8');

function setup({denied = false, responseError = false} = {}) {
  class Element {
    constructor() { this.dataset = {}; this.events = {}; this.children = []; this.value = 'Text existent'; this.isConnected = true; }
    append(...children) { this.children.push(...children); }
    setAttribute() {}
    addEventListener(name, callback) { this.events[name] = callback; }
    dispatchEvent() {}
  }
  const target = new Element(); let controls;
  target.parentElement = {after: element => { controls = element; }};
  let recorder; let stopped = 0; let uploads = 0; let received;
  class Recorder {
    static isTypeSupported() { return true; }
    constructor(stream, options) { recorder = this; this.mimeType = options.mimeType; this.state = 'inactive'; }
    start() { this.state = 'recording'; }
    stop() {
      this.state = 'inactive';
      // A final recorder chunk arrives before onstop, as in the browser.
      this.ondataavailable({data: new Blob(['b'.repeat(150)])});
      this.stopPromise = this.onstop();
    }
  }
  const window = {isSecureContext: true, MediaRecorder: Recorder, addEventListener() {}};
  const context = {window, MediaRecorder: Recorder, Blob, FormData, Event,
    setTimeout: () => 1, clearTimeout() {},
    document: {createElement: () => new Element()},
    navigator: {mediaDevices: {getUserMedia: async () => {
      if (denied) { const error = new Error(); error.name = 'NotAllowedError'; throw error; }
      return {getTracks: () => [{stop: () => { stopped++; }}]};
    }}},
    fetch: async (url, options) => {
      uploads++; received = options.body.get('audio');
      return {ok: !responseError, json: async () => responseError ? {error: 'Eroare simulată'} : {text: 'Text dictat'}};
    }};
  vm.runInNewContext(source, context);
  window.attachDictation({querySelectorAll: () => [target]});
  return {target, button: controls.children[0], status: controls.children[1],
    recorder: () => recorder, uploads: () => uploads, received: () => received, stopped: () => stopped};
}

test('dictation accumulates all chunks, appends text and releases microphone', async () => {
  const env = setup(); await env.button.events.click();
  env.recorder().ondataavailable({data: new Blob(['a'.repeat(150)])});
  await env.button.events.click(); await env.recorder().stopPromise;
  assert.equal(env.received().size, 300);
  assert.equal(env.target.value, 'Text existent\nText dictat');
  assert.equal(env.uploads(), 1); assert.ok(env.stopped() > 0);
  assert.equal(env.button.disabled, false);
});

test('microphone denial recovers without uploading', async () => {
  const env = setup({denied: true}); await env.button.events.click();
  assert.equal(env.uploads(), 0); assert.equal(env.button.disabled, false);
  assert.match(env.status.textContent, /nu a fost permis/);
});

test('transcription error preserves text and releases microphone', async () => {
  const env = setup({responseError: true}); await env.button.events.click();
  await env.button.events.click(); await env.recorder().stopPromise;
  assert.equal(env.target.value, 'Text existent');
  assert.equal(env.status.textContent, 'Eroare simulată');
  assert.ok(env.stopped() > 0); assert.equal(env.button.disabled, false);
});
