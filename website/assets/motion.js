const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
document.querySelectorAll('.demo').forEach((demo) => {
  const video = demo.querySelector('video');
  const button = demo.querySelector('button');
  let started = false;
  let visible = false;
  let finished = false;
  let wantsPlayback = !reducedMotion.matches;
  const offer = (replay) => {
    button.textContent = replay ? button.dataset.replay : button.dataset.play;
    button.hidden = false;
  };
  const play = () => {
    if (!visible || !wantsPlayback || finished || !video.paused) return;
    started = true;
    button.hidden = true;
    if (!video.src) video.src = video.dataset.src;
    video.muted = true;
    video.play().catch((error) => {
      // Scrolling away may interrupt an in-flight play request.
      if (error?.name === 'AbortError') return;
      wantsPlayback = false;
      offer(false);
    });
  };
  video.addEventListener('ended', () => {
    finished = true;
    wantsPlayback = false;
    offer(true);
  });
  button.addEventListener('click', () => {
    video.currentTime = 0;
    finished = false;
    wantsPlayback = true;
    play();
  });
  const observer = new IntersectionObserver((entries) => {
    const entry = entries[entries.length - 1];
    visible = entry.isIntersecting && entry.intersectionRatio >= 0.35;
    if (visible) play();
    else video.pause();
  }, { threshold: [0, 0.35] });
  observer.observe(demo);
  const updatePreference = () => {
    if (reducedMotion.matches) {
      wantsPlayback = false;
      video.pause();
      offer(started);
    } else if (!started) {
      wantsPlayback = true;
      button.hidden = true;
      play();
    }
  };
  reducedMotion.addEventListener('change', updatePreference);
  updatePreference();
});
