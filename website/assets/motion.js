const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
document.querySelectorAll('.demo').forEach((demo) => {
  const video = demo.querySelector('video');
  const button = demo.querySelector('button');
  let started = false;
  const offer = (replay) => {
    button.textContent = replay ? button.dataset.replay : button.dataset.play;
    button.hidden = false;
  };
  const play = () => {
    started = true;
    button.hidden = true;
    if (!video.src) video.src = video.dataset.src;
    video.muted = true;
    video.play().catch(() => offer(false));
  };
  video.addEventListener('ended', () => offer(true));
  button.addEventListener('click', () => {
    video.currentTime = 0;
    play();
  });
  const observer = new IntersectionObserver((entries) => {
    if (entries.some(entry => entry.isIntersecting) && !started && !reducedMotion.matches) play();
  }, { threshold: 0.35 });
  observer.observe(demo);
  const updatePreference = () => {
    if (reducedMotion.matches) {
      video.pause();
      offer(started);
    } else if (!started) {
      button.hidden = true;
      observer.unobserve(demo);
      observer.observe(demo);
    }
  };
  reducedMotion.addEventListener('change', updatePreference);
  updatePreference();
});
