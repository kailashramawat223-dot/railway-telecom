// Railway Telecom AMS — Main JS

document.addEventListener('DOMContentLoaded', () => {

  // Auto-dismiss alerts after 4s
  document.querySelectorAll('.alert.fade.show').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      if (bsAlert) bsAlert.close();
    }, 4000);
  });

  // Mobile sidebar toggle
  const topbar = document.querySelector('.top-navbar');
  if (topbar) {
    const toggler = document.createElement('button');
    toggler.className = 'btn btn-sm btn-rail-outline d-lg-none me-2';
    toggler.innerHTML = '<i class="bi bi-list"></i>';
    toggler.style.cssText = 'padding:4px 8px;order:-1';
    toggler.addEventListener('click', () => {
      document.getElementById('sidebar')?.classList.toggle('open');
    });
    const brand = topbar.querySelector('.navbar-brand');
    if (brand) brand.before(toggler);
  }

  // Animate stat numbers on load
  document.querySelectorAll('.stat-number').forEach(el => {
    const target = parseInt(el.textContent, 10);
    if (isNaN(target) || target === 0) return;
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 30));
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 30);
  });

  // Highlight active sidebar link on sub-pages
  const path = window.location.pathname;
  document.querySelectorAll('.sidebar-link').forEach(link => {
    if (link.getAttribute('href') === path) {
      link.classList.add('active');
    }
  });

  // Confirm delete for inline forms (extra safety)
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', e => {
      if (!confirm(btn.dataset.confirm)) e.preventDefault();
    });
  });

});
