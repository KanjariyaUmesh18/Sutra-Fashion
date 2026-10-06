/* ============================================================
   SUTRA — Core site script
   Django-integrated version. Navbar and footer are rendered
   server-side by Django templates — no client-side injection.
   ============================================================ */

/* ---- Badge update: reads from server-rendered badge values ---- */
window.updateBadges = function() {
  // Badges are rendered server-side via context processors.
  // This function is a no-op stub kept for compatibility.
};

window.formatPrice = (p) => '₹' + Number(p).toLocaleString('en-IN');

window.showToast = function(message, type) {
  const stack = document.getElementById('toastStack');
  if (!stack) return;
  const toast = document.createElement('div');
  toast.className = 'toast show toast--' + (type || 'success');
  toast.innerHTML = `<div class="toast__content"><div class="toast__title">${message}</div></div>`;
  stack.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('is-leaving');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
};

/* ---- Navbar scroll effect ---- */
function wireNavbar() {
  const nav = document.getElementById('siteNavbar');
  const hamburger = document.getElementById('hamburgerBtn');
  const panel = document.getElementById('mobilePanel');

  if (nav) {
    window.addEventListener('scroll', () => {
      nav.classList.toggle('is-scrolled', window.scrollY > 12);
    }, { passive: true });
  }

  if (hamburger && panel) {
    hamburger.addEventListener('click', () => {
      const open = panel.classList.toggle('is-open');
      hamburger.classList.toggle('is-open', open);
      hamburger.setAttribute('aria-expanded', String(open));
    });
    panel.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
      panel.classList.remove('is-open');
      hamburger.classList.remove('is-open');
      hamburger.setAttribute('aria-expanded', 'false');
    }));
    // Close on outside click
    document.addEventListener('click', (e) => {
      if (panel.classList.contains('is-open') && !nav.contains(e.target)) {
        panel.classList.remove('is-open');
        hamburger.classList.remove('is-open');
        hamburger.setAttribute('aria-expanded', 'false');
      }
    });
  }
}

/* ---- Button ripple feedback ---- */
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.btn');
  if (!btn || btn.disabled) return;
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const ripple = document.createElement('span');
  ripple.className = 'ripple';
  ripple.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX - rect.left - size/2}px;top:${e.clientY - rect.top - size/2}px`;
  btn.appendChild(ripple);
  setTimeout(() => ripple.remove(), 650);
});

/* ---- Scroll reveal ---- */
function initReveal() {
  const targets = document.querySelectorAll('.reveal:not(.is-observed), .reveal-stagger:not(.is-observed)');
  if (!targets.length) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
  targets.forEach(t => {
    t.classList.add('is-observed');
    io.observe(t);
  });
}
window.initReveal = initReveal;

/* ---- Auto-dismiss Django messages (toast notifications) ---- */
function autoDismissMessages() {
  const container = document.querySelector('.messages-container');
  if (!container) return;
  setTimeout(() => {
    container.querySelectorAll('.toast').forEach(t => {
      t.classList.add('is-leaving');
      setTimeout(() => t.remove(), 300);
    });
    setTimeout(() => {
      if (!container.querySelector('.toast')) container.remove();
    }, 400);
  }, 4000);
}

/* ---- PDP: thumbnail gallery, qty stepper, size/color swatches ---- */
function initPDP() {
  // Thumbnail gallery
  const mainImgWrap = document.querySelector('.pdp-main-image-wrap img');
  const thumbs = document.querySelectorAll('.pdp-thumbs .pdp-thumb');
  thumbs.forEach(btn => {
    btn.addEventListener('click', () => {
      thumbs.forEach(t => t.classList.remove('is-active'));
      btn.classList.add('is-active');
      if (mainImgWrap && btn.querySelector('img')) {
        mainImgWrap.src = btn.querySelector('img').src;
        mainImgWrap.alt = btn.querySelector('img').alt;
      }
    });
  });

  // Qty stepper (type="button" in template prevents form submit)
  const qtyInput = document.querySelector('#pdpForm .qty-input');
  const qtyMinus = document.querySelector('#pdpForm .qty-btn:first-child');
  const qtyPlus  = document.querySelector('#pdpForm .qty-btn:last-child');
  if (qtyInput && qtyMinus && qtyPlus) {
    qtyMinus.addEventListener('click', () => {
      let v = parseInt(qtyInput.value) || 1;
      if (v > 1) qtyInput.value = v - 1;
    });
    qtyPlus.addEventListener('click', () => {
      let v = parseInt(qtyInput.value) || 1;
      const max = parseInt(qtyInput.max) || 999;
      if (v < max) qtyInput.value = v + 1;
    });
  }

  // Visual swatch selection (the radio inputs handle the actual value)
  document.querySelectorAll('.swatch-label').forEach(label => {
    const input = label.querySelector('input[type="radio"]');
    const swatch = label.querySelector('.swatch-size, .swatch-color');
    if (!input || !swatch) return;
    input.addEventListener('change', () => {
      const group = input.name;
      document.querySelectorAll(`input[name="${group}"]`).forEach(r => {
        const s = r.closest('.swatch-label')?.querySelector('.swatch-size, .swatch-color');
        if (s) s.classList.remove('is-selected');
      });
      swatch.classList.add('is-selected');
    });
  });

  // Accordion
  document.querySelectorAll('.accordion__toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const accordion = btn.closest('.accordion');
      const isOpen = accordion.classList.contains('is-open');
      const content = accordion.querySelector('.accordion__content');
      if (isOpen) {
        accordion.classList.remove('is-open');
        content.style.maxHeight = '0';
        btn.setAttribute('aria-expanded', 'false');
      } else {
        accordion.classList.add('is-open');
        content.style.maxHeight = content.scrollHeight + 'px';
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });
}

/* ---- Cart page: qty steppers ---- */
function initCartPage() {
  const cartItems = document.querySelector('.cart-items');
  if (!cartItems) return;
  // Qty steppers submit their own form on click — handled server-side.
  // Nothing extra needed; the form buttons POST to update_cart view.
}

/* ---- Address autofill on checkout ---- */
function initCheckout() {
  document.querySelectorAll('.js-autofill-address').forEach(btn => {
    btn.addEventListener('click', () => {
      const fields = {
        'id_shipping_name':          btn.dataset.name,
        'id_shipping_phone':         btn.dataset.phone,
        'id_shipping_address_line1': btn.dataset.line1,
        'id_shipping_address_line2': btn.dataset.line2 || '',
        'id_shipping_city':          btn.dataset.city,
        'id_shipping_state':         btn.dataset.state,
        'id_shipping_pincode':       btn.dataset.pincode,
      };
      Object.entries(fields).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) el.value = val;
      });
    });
  });
}

/* ---- Page transition (subtle fade) ---- */
function initPageTransition() {
  let overlay = document.querySelector('.page-transition');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'page-transition';
    document.body.appendChild(overlay);
  }
  document.querySelectorAll('a[href]').forEach(a => {
    if (a.dataset.transitionWired) return;
    a.dataset.transitionWired = '1';
    const href = a.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('http') ||
        href.startsWith('mailto') || href.startsWith('tel') ||
        href.startsWith('javascript') || a.target === '_blank') return;
    a.addEventListener('click', (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      overlay.classList.add('is-active');
      setTimeout(() => { window.location.href = href; }, 260);
    });
  });
}

/* ---- Category page filter panel (mobile) ---- */
function initFiltersPanel() {
  const openBtn  = document.getElementById('openFiltersBtn');
  const closeBtn = document.getElementById('closeFiltersBtn');
  const panel    = document.getElementById('filtersPanel');
  if (!panel) return;
  openBtn?.addEventListener('click', () => panel.classList.add('is-open'));
  closeBtn?.addEventListener('click', () => panel.classList.remove('is-open'));
  // Close on outside click
  document.addEventListener('click', (e) => {
    if (panel.classList.contains('is-open') && !panel.contains(e.target) && e.target !== openBtn) {
      panel.classList.remove('is-open');
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  wireNavbar();
  autoDismissMessages();
  setTimeout(initReveal, 80);
  initPDP();
  initCartPage();
  initCheckout();
  initFiltersPanel();
  initPageTransition();
});
