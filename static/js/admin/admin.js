/* ============================================================
   SUTRA Admin — Core JavaScript
   Sidebar toggle, search, modals, table interactions, toasts
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initTopbarSearch();
  initTableCheckboxes();
  initModals();
  initTooltips();
  initDeleteConfirms();
  initAdminToast();
  initStatusDropdowns();
  initReveal();
});

/* ================= REVEAL ANIMATIONS ================= */
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
  }, { threshold: 0.12 });
  targets.forEach(t => {
    t.classList.add('is-observed');
    io.observe(t);
  });
}

/* ================= SIDEBAR ================= */
function initSidebar() {
  const layout = document.querySelector('.admin-layout');
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.admin-sidebar');
  const mobileOverlay = document.createElement('div');
  mobileOverlay.className = 'admin-sidebar-overlay';
  mobileOverlay.style.cssText = 'position:fixed;inset:0;background:rgba(17,17,17,0.4);z-index:99;display:none;transition:opacity 0.3s';
  document.body.appendChild(mobileOverlay);

  if (!toggleBtn || !layout) return;

  // Restore from localStorage
  const saved = localStorage.getItem('sutra_admin_sidebar');
  if (saved === 'collapsed' && window.innerWidth > 992) {
    layout.classList.add('is-collapsed');
  }

  toggleBtn.addEventListener('click', () => {
    if (window.innerWidth <= 992) {
      sidebar.classList.toggle('is-mobile-open');
      mobileOverlay.style.display = sidebar.classList.contains('is-mobile-open') ? 'block' : 'none';
    } else {
      layout.classList.toggle('is-collapsed');
      localStorage.setItem('sutra_admin_sidebar', layout.classList.contains('is-collapsed') ? 'collapsed' : 'expanded');
    }
  });

  mobileOverlay.addEventListener('click', () => {
    sidebar.classList.remove('is-mobile-open');
    mobileOverlay.style.display = 'none';
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 992) {
      sidebar.classList.remove('is-mobile-open');
      mobileOverlay.style.display = 'none';
    }
  });
}

/* ================= TOPBAR SEARCH ================= */
function initTopbarSearch() {
  const searchInput = document.getElementById('adminSearch');
  if (!searchInput) return;
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      showAdminToast('Search: "' + searchInput.value + '" — results would appear here.');
    }
  });
}

/* ================= TABLE CHECKBOXES ================= */
function initTableCheckboxes() {
  const selectAll = document.getElementById('selectAll');
  if (!selectAll) return;
  const checkboxes = document.querySelectorAll('.row-checkbox');
  selectAll.addEventListener('change', () => {
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
  });
  checkboxes.forEach(cb => {
    cb.addEventListener('change', () => {
      selectAll.checked = [...checkboxes].every(c => c.checked);
    });
  });
}

/* ================= MODALS ================= */
function initModals() {
  document.querySelectorAll('[data-modal-open]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.modalOpen);
      if (target) target.classList.add('is-open');
    });
  });
  document.querySelectorAll('[data-modal-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.admin-modal-overlay').classList.remove('is-open');
    });
  });
  document.querySelectorAll('.admin-modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.remove('is-open');
    });
  });
}

/* ================= TOAST ================= */
let toastStack;
function initAdminToast() {
  toastStack = document.getElementById('adminToastStack');
  if (!toastStack) {
    toastStack = document.createElement('div');
    toastStack.id = 'adminToastStack';
    toastStack.className = 'toast-stack';
    document.body.appendChild(toastStack);
  }
}

function showAdminToast(message) {
  if (!toastStack) initAdminToast();
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg><span>${message}</span>`;
  toastStack.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('is-leaving');
    setTimeout(() => toast.remove(), 220);
  }, 2600);
}

/* ================= DELETE CONFIRMS ================= */
function initDeleteConfirms() {
  document.querySelectorAll('[data-delete]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      if (confirm('Are you sure you want to delete this item?')) {
        const row = btn.closest('tr');
        if (row) {
          row.style.opacity = '0';
          row.style.transform = 'translateX(20px)';
          row.style.transition = 'all 0.3s';
          setTimeout(() => row.remove(), 300);
          showAdminToast('Item deleted successfully.');
        }
      }
    });
  });
}

/* ================= TOOLTIPS (simple title fallback) ================= */
function initTooltips() {
  // Using native title attributes - no custom JS needed
}

/* ================= STATUS DROPDOWNS ================= */
function initStatusDropdowns() {
  document.querySelectorAll('.status-select').forEach(select => {
    select.addEventListener('change', () => {
      showAdminToast('Status updated to "' + select.options[select.selectedIndex].text + '"');
    });
  });
}

/* ================= TABLE SEARCH FILTER ================= */
function filterTable(inputId, tableId) {
  const input = document.getElementById(inputId);
  const table = document.getElementById(tableId);
  if (!input || !table) return;
  input.addEventListener('input', () => {
    const val = input.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(row => {
      row.style.display = row.textContent.toLowerCase().includes(val) ? '' : 'none';
    });
  });
}

/* ================= FORM VALIDATION HELPER ================= */
function validateRequired(formId) {
  const form = document.getElementById(formId);
  if (!form) return false;
  let valid = true;
  form.querySelectorAll('[required]').forEach(field => {
    const error = field.parentElement.querySelector('.form-error');
    if (!field.value.trim()) {
      field.classList.add('is-invalid');
      if (error) error.classList.add('is-visible');
      valid = false;
    } else {
      field.classList.remove('is-invalid');
      if (error) error.classList.remove('is-visible');
    }
  });
  return valid;
}

/* ================= SORTABLE TABLE HEADERS ================= */
function initSortableHeaders() {
  document.querySelectorAll('.sortable').forEach(th => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {
      const table = th.closest('table');
      const tbody = table.querySelector('tbody');
      const index = [...th.parentElement.children].indexOf(th);
      const rows = [...tbody.querySelectorAll('tr')];
      const asc = th.dataset.sort !== 'asc';
      th.dataset.sort = asc ? 'asc' : 'desc';
      
      // Remove sort indicators from siblings
      th.parentElement.querySelectorAll('.sortable').forEach(s => {
        if (s !== th) delete s.dataset.sort;
      });

      rows.sort((a, b) => {
        const aVal = a.children[index]?.textContent.trim() || '';
        const bVal = b.children[index]?.textContent.trim() || '';
        const aNum = parseFloat(aVal.replace(/[₹,]/g, ''));
        const bNum = parseFloat(bVal.replace(/[₹,]/g, ''));
        if (!isNaN(aNum) && !isNaN(bNum)) return asc ? aNum - bNum : bNum - aNum;
        return asc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      });
      rows.forEach(row => tbody.appendChild(row));
    });
  });
}

document.addEventListener('DOMContentLoaded', initSortableHeaders);
