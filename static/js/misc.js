/* ============================================================
   SUTRA — Misc page scripts (Django-integrated)
   Handles client-side enhancements. All data persistence is
   now handled server-side by Django views.
   ============================================================ */

/* ---- PDP accordion (also called from main.js but safe to re-run) ---- */
function initAccordions() {
  document.querySelectorAll('.accordion__toggle').forEach(btn => {
    if (btn.dataset.accordionWired) return;
    btn.dataset.accordionWired = '1';
    btn.addEventListener('click', () => {
      const accordion = btn.closest('.accordion');
      const content = accordion.querySelector('.accordion__content');
      const isOpen = accordion.classList.contains('is-open');
      accordion.classList.toggle('is-open', !isOpen);
      btn.setAttribute('aria-expanded', String(!isOpen));
      if (content) content.style.maxHeight = isOpen ? '0' : content.scrollHeight + 'px';
    });
  });
}

/* ---- Toast helper (delegates to main.js window.showToast) ---- */
function showToast(msg, type) {
  if (window.showToast) window.showToast(msg, type);
}

document.addEventListener('DOMContentLoaded', () => {
  initAccordions();
});
