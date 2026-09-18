(function() {
  function getStoredUser() {
    const email = localStorage.getItem('userEmail') || '';
    let name = localStorage.getItem('userName') || '';
    
    if (!name || !name.trim()) {
      if (email && email.trim()) {
        const prefix = email.split('@')[0];
        name = prefix
          .split(/[._-]/)
          .filter(Boolean)
          .map(w => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' ');
      }
      if (!name || !name.trim()) {
        name = 'Arjun Sharma';
      }
    }
    
    const parts = name.trim().split(/\s+/);
    let initials = 'AS';
    if (parts.length >= 2) {
      initials = (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    } else if (parts.length === 1 && parts[0].length > 0) {
      initials = parts[0].substring(0, Math.min(2, parts[0].length)).toUpperCase();
    }
    
    return { name, email: email || 'arjun@example.com', initials };
  }

  function applyUserSession() {
    const { name, email, initials } = getStoredUser();

    // 1. Update all avatar circles (.avatar, .large-avatar)
    document.querySelectorAll('.avatar, .large-avatar').forEach(el => {
      el.textContent = initials;
    });

    // 2. Update profile topbar greeting
    document.querySelectorAll('.profile-text strong').forEach(el => {
      el.textContent = `Welcome Back, ${name}!`;
    });

    // 3. Update main welcome headers
    document.querySelectorAll('h1').forEach(h1 => {
      if (h1.textContent.includes('Welcome Back') || h1.textContent.includes('Welcome back')) {
        h1.textContent = `Welcome Back, ${name}!`;
      }
    });

    // 4. Update profile page summary name
    document.querySelectorAll('.summary-person h2').forEach(h2 => {
      h2.textContent = name;
    });

    // 5. Update full name & email inputs/labels if on profile/settings
    const fullNameInput = document.getElementById('fullName');
    if (fullNameInput && fullNameInput.tagName === 'INPUT' && !fullNameInput.closest('form#registrationForm')) {
      fullNameInput.value = name;
    }
    const emailInput = document.getElementById('email');
    if (emailInput && emailInput.tagName === 'INPUT' && !emailInput.closest('form#loginForm') && !emailInput.closest('form#registrationForm')) {
      emailInput.value = email;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyUserSession);
  } else {
    applyUserSession();
  }

  window.getStoredUser = getStoredUser;
  window.applyUserSession = applyUserSession;
})();
