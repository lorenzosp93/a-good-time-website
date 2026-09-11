const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = readFileSync(`${__dirname}/assets/motion.js`, 'utf8');
function setup(reduced, reject = false) {
  const events = {};
  const preference = {matches: reduced, addEventListener(_, fn) { this.change = fn; }};
  const video = {src: '', dataset: {src: '/demo.mp4'}, currentTime: 7, plays: 0, paused: true,
    play() { this.plays++; this.paused = false; return reject ? Promise.reject() : Promise.resolve(); },
    pause() { this.paused = true; }, addEventListener(name, fn) { events[name] = fn; }};
  const button = {hidden: true, dataset: {play: 'Play', replay: 'Replay'},
    addEventListener(_, fn) { this.click = fn; }};
  let visibility;
  vm.runInNewContext(source, {
    matchMedia: () => preference,
    document: {querySelectorAll: () => [{querySelector: tag => tag === 'video' ? video : button}]},
    IntersectionObserver: class { constructor(fn) { visibility = (ratio) => fn([{isIntersecting: ratio > 0, intersectionRatio: ratio}]); } observe() {} unobserve() {} }
  });
  return {video, button, preference, events, enter: () => visibility(1), visibility};
}
(async () => {
  const normal = setup(false);
  normal.enter(); normal.enter();
  assert.equal(normal.video.plays, 1);
  normal.video.currentTime = 12;
  normal.visibility(0);
  assert.equal(normal.video.paused, true);
  normal.visibility(0.2);
  assert.equal(normal.video.plays, 1);
  normal.enter();
  assert.equal(normal.video.plays, 2);
  assert.equal(normal.video.currentTime, 12);
  assert.equal(normal.button.hidden, true);
  normal.video.paused = true;
  normal.events.ended();
  normal.visibility(0); normal.enter();
  assert.equal(normal.video.plays, 2);
  assert.equal(normal.button.hidden, false);
  assert.equal(normal.button.textContent, 'Replay');
  normal.button.click();
  assert.equal(normal.video.currentTime, 0);
  assert.equal(normal.video.plays, 3);
  assert.equal(normal.button.hidden, true);
  const second = setup(false);
  normal.visibility(0); second.enter();
  assert.equal(normal.video.paused, true);
  assert.equal(second.video.paused, false);
  const reduced = setup(true);
  reduced.enter();
  assert.equal(reduced.video.plays, 0);
  assert.equal(reduced.video.src, '');
  assert.equal(reduced.button.textContent, 'Play');
  reduced.button.click();
  assert.equal(reduced.video.plays, 1);
  const blocked = setup(false, true);
  blocked.enter();
  await Promise.resolve();
  assert.equal(blocked.button.hidden, false);
  assert.equal(blocked.button.textContent, 'Play');
  console.log('Viewport pause/resume, independent demos, replay, reduced motion and autoplay fallback passed.');
})();
