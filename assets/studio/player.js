// Plays a HyperFrames composition in a normal browser, for the studio: shows each timed element only inside its
// window, drives the GSAP timeline, and keeps every video and sound in step with the a-roll (the clock).
// The render never loads this file: studio.py adds it to the page it serves.
(function () {
  const root = document.querySelector('[data-composition-id]');
  const DUR = +root.dataset.duration;
  // the renderer sizes the composition from data-width / data-height; a plain page has to do it itself
  root.style.width = (+root.dataset.width || 1080) + 'px';
  root.style.height = (+root.dataset.height || 1920) + 'px';
  const timed = [...document.querySelectorAll('[data-start]')].filter((e) => e !== root);
  const media = timed.filter((e) => e.tagName === 'VIDEO' || e.tagName === 'AUDIO');
  const clock = document.getElementById('aroll');
  let t = 0;
  let playing = false;
  let muted = false;
  let wall0 = 0;
  let t0 = 0;

  media.forEach((m) => {
    m.preload = 'auto';
    m.volume = Math.max(0, Math.min(1, +(m.dataset.volume || 1)));
    if (m.tagName === 'VIDEO' && m !== clock && m.dataset.hasAudio !== 'true') m.muted = true;
  });

  const span = (e) => {
    const s = +e.dataset.start || 0;
    const d = e.dataset.duration ? +e.dataset.duration : DUR - s;
    return [s, s + d];
  };

  function apply(seeking, still) {
    const tl = window.__timelines && window.__timelines.main;
    if (tl) tl.seek(t, false);
    for (const e of timed) {
      const [s, end] = span(e);
      const on = t >= s && t < end;
      e.style.visibility = on ? '' : 'hidden';
      if (still || (e.tagName !== 'VIDEO' && e.tagName !== 'AUDIO')) continue;
      const local = t - s + (+e.dataset.mediaStart || 0);
      if (on && playing) {
        if (e.paused) {
          e.currentTime = local;
          e.play().catch(() => {});
        } else if (e !== clock && Math.abs(e.currentTime - local) > 0.2) {
          e.currentTime = local;
        }
      } else {
        if (!e.paused) e.pause();
        if (on && seeking) e.currentTime = local;
      }
    }
  }

  function frame() {
    if (playing) {
      if (clock && !clock.paused) t = clock.currentTime;
      else if (!clock) t = t0 + (performance.now() - wall0) / 1000;
      if (t >= DUR - 0.02) {
        t = DUR - 0.02;
        api.pause();
      }
      apply(false);
    }
    requestAnimationFrame(frame);
  }

  const api = {
    duration: DUR,
    get time() { return t; },
    get playing() { return playing; },
    play() {
      if (t >= DUR - 0.05) t = 0;
      playing = true;
      wall0 = performance.now();
      t0 = t;
      apply(true);
    },
    pause() {
      playing = false;
      apply(true);
    },
    seek(x) {
      t = Math.max(0, Math.min(DUR - 0.02, x));
      t0 = t;
      wall0 = performance.now();
      apply(true);
    },
    // the layout at time x without moving any video (for measuring); seek() afterwards puts everything back
    pose(x) {
      t = Math.max(0, Math.min(DUR - 0.02, x));
      apply(false, true);
    },
    setMuted(m) {
      muted = m;
      media.forEach((e) => { if (e.tagName === 'AUDIO' || e === clock) e.muted = muted; });
    },
    // resolves once the a-roll shows the frame of the last seek (so a swapped preview never flashes empty)
    settled() {
      return new Promise((resolve) => {
        const wait = () => ((!clock || (clock.readyState >= 2 && !clock.seeking)) ? resolve() : setTimeout(wait, 30));
        wait();
      });
    },
    // resolves once the timeline exists and the a-roll can show the current frame
    ready: new Promise((resolve) => {
      const wait = () => {
        const ok = window.__timelines && window.__timelines.main && (!clock || clock.readyState >= 2);
        if (ok) { apply(true); resolve(); } else setTimeout(wait, 40);
      };
      wait();
    }),
  };
  window.studio = api;
  apply(true);
  requestAnimationFrame(frame);
})();
