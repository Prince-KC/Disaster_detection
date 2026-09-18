// components.js - Reusable UI Components

function renderSidebar() {
  const currentPath = window.location.pathname.split('/').pop() || 'dashboard.html';
  
  const sidebarHTML = `
    <aside class="sidebar" id="sidebar">
      <a class="brand" href="landingpage.html">
        <span class="brand-mark" aria-hidden="true"><svg class="brand-symbol" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 4C12 4 5 8 4 19c6-1 11-5 16-15Z"></path><path d="M4 19c4-4 7-7 12-10"></path></svg></span>
        <span>KhetRakshak</span>
      </a>
      <nav class="sidebar-nav">
        <a class="nav-item ${currentPath === 'dashboard.html' ? 'active' : ''}" href="dashboard.html">
          <i class="icon">⌂</i><span>Dashboard</span>
        </a>
        <a class="nav-item ${currentPath === 'live-monitoring.html' ? 'active' : ''}" href="live-monitoring.html">
          <i class="icon">◉</i><span>Live Monitoring</span>
        </a>
        <a class="nav-item ${currentPath === 'warning-light-status.html' ? 'active' : ''}" href="warning-light-status.html">
          <i class="icon">◐</i><span>Deterrent Light</span>
        </a>
        <a class="nav-item ${currentPath === 'speaker-status.html' ? 'active' : ''}" href="speaker-status.html">
          <i class="icon">◖</i><span>Speaker Status</span>
        </a>
        <a class="nav-item ${currentPath === 'detection-history.html' ? 'active' : ''}" href="detection-history.html">
          <i class="icon">↺</i><span>History</span>
        </a>
        <a class="nav-item ${currentPath === 'notifications.html' ? 'active' : ''}" href="notifications.html">
          <i class="icon">♢</i><span>Notifications</span>
        </a>
        <a class="nav-item ${currentPath === 'analytics.html' ? 'active' : ''}" href="analytics.html">
          <i class="icon">▥</i><span>Analytics</span>
        </a>
        <a class="nav-item ${currentPath === 'profile.html' ? 'active' : ''}" href="profile.html">
          <i class="icon">○</i><span>Profile</span>
        </a>
        <a class="nav-item ${currentPath === 'settings.html' ? 'active' : ''}" href="settings.html">
          <i class="icon">⚙</i><span>Settings</span>
        </a>
      </nav>
      <div class="sidebar-bottom">
        <a class="nav-item" href="logout-confirmation.html">
          <i class="icon">↪</i><span>Logout</span>
        </a>
        <button class="collapse-btn" id="collapseButton">
          <i class="collapse-icon" aria-hidden="true"></i><span>Collapse</span>
        </button>
      </div>
    </aside>
  `;
  
  const container = document.getElementById('sidebar-container');
  if (container) {
    container.innerHTML = sidebarHTML;
  }
}

function renderTopbar(title) {
  const topbarHTML = `
    <header class="topbar">
      <div style="display:flex;align-items:center;gap:12px">
        <button class="mobile-menu" id="mobileMenu" aria-label="Open navigation">☰</button>
        <h1 class="page-title">${title}</h1>
      </div>
      <div class="top-actions">
        <label class="search">
          <span>⌕</span>
          <input type="search" placeholder="Search dashboard...">
        </label>
        <span class="date" id="currentDate"></span>
        <button class="bell" aria-label="Notifications" onclick="window.location.href='notifications.html'">
          ♢<b></b>
        </button>
        <button class="theme-toggle" id="themeToggleBtn" aria-label="Toggle Theme" style="background:transparent; border:none; font-size:18px;">
          <span id="themeIcon">🌙</span>
        </button>
        <div class="profile" id="profileButton">
          <span class="profile-text">
            <strong>Welcome Back, <span class="user-display-name">Arjun Sharma</span>!</strong>
            <span>Farm Owner</span>
          </span>
          <span class="avatar">AS</span>
          <div class="profile-menu">
            <a href="profile.html">My Profile</a>
            <a href="settings.html">Settings</a>
            <a href="logout-confirmation.html">Logout</a>
          </div>
        </div>
      </div>
    </header>
  `;
  
  const container = document.getElementById('topbar-container');
  if (container) {
    container.innerHTML = topbarHTML;
  }
}

function initDashboardEvents() {
  const sidebar = document.getElementById('sidebar');
  const collapseBtn = document.getElementById('collapseButton');
  const mobileMenuBtn = document.getElementById('mobileMenu');
  const profileBtn = document.getElementById('profileButton');
  
  if (collapseBtn && sidebar) {
    collapseBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    });
    
    // Restore state
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
      sidebar.classList.add('collapsed');
    }
  }
  
  if (mobileMenuBtn && sidebar) {
    mobileMenuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
  }
  
  if (profileBtn) {
    profileBtn.addEventListener('click', (event) => {
      if (event.target.closest('.profile-menu a')) return;
      profileBtn.classList.toggle('open');
    });
    
    document.addEventListener('click', (event) => {
      if (!event.target.closest('#profileButton')) {
        profileBtn.classList.remove('open');
      }
    });
  }
  
  const dateEl = document.getElementById('currentDate');
  if (dateEl) {
    dateEl.textContent = new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  }
}

// Automatically initialize if elements exist
document.addEventListener('DOMContentLoaded', () => {
  // If the page defines a global PAGE_TITLE variable, use it. Otherwise guess from URL.
  let title = window.PAGE_TITLE || 'Dashboard';
  renderSidebar();
  renderTopbar(title);
  initDashboardEvents();
});
