/* ============================================================
   SUTRA — Auth page enhancements (client-side only)
   Forms are submitted to Django views for server-side handling.
   This script adds password visibility toggle only.
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  // Password show/hide toggles
  document.querySelectorAll('[data-toggle-password]').forEach(btn => {
    btn.addEventListener('click', () => {
      const inputId = btn.dataset.togglePassword;
      const input = document.getElementById(inputId);
      if (!input) return;
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
    });
  });
});
