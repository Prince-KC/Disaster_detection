// theme.js - Global Dark Mode handler

function initTheme() {
  const currentTheme = localStorage.getItem('theme') || 'light';
  
  if (currentTheme === 'dark') {
    document.body.classList.add('dark');
  } else {
    document.body.classList.remove('dark');
  }
  
  updateThemeIcon(currentTheme);
  
  // Attach event listener once DOM is loaded, or if already loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachThemeListener);
  } else {
    attachThemeListener();
  }
}

function attachThemeListener() {
  const toggleBtn = document.getElementById('themeToggleBtn') || document.getElementById('themeToggle');
  if (toggleBtn) {
    // Prevent multiple bindings
    toggleBtn.removeEventListener('click', toggleTheme);
    toggleBtn.addEventListener('click', toggleTheme);
  }
}

function toggleTheme() {
  const isDark = document.body.classList.toggle('dark');
  const newTheme = isDark ? 'dark' : 'light';
  localStorage.setItem('theme', newTheme);
  updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
  const themeIcon = document.getElementById('themeIcon');
  if (themeIcon) {
    themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
  }
  
  // Update lucide icons if they exist
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle && window.lucide) {
    themeToggle.innerHTML = theme === 'dark' ? '<i data-lucide="moon"></i>' : '<i data-lucide="sun"></i>';
    lucide.createIcons();
  }
}

// Run immediately to prevent flash of wrong theme
initTheme();
