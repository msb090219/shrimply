// Content stays visible if JavaScript or the animation API is unavailable.
const motionPreference = matchMedia('(prefers-reduced-motion: reduce)');
if ('IntersectionObserver' in window && !motionPreference.matches) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      observer.unobserve(entry.target);
      if (!motionPreference.matches && typeof entry.target.animate === 'function') {
        entry.target.animate(
          [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'none' }],
          { duration: 240, easing: 'cubic-bezier(0.23, 1, 0.32, 1)' }
        );
      }
    }
  }, { threshold: 0.1 });
  document.querySelectorAll('[data-reveal]').forEach((element) => observer.observe(element));
}
