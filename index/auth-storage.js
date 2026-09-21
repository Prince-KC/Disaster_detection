/**
 * विपद्Sathi Web Storage Authentication & Auto-Login Service
 * Automatically persists credentials for both Authority and Citizen in browser localStorage
 * and handles seamless, one-click or automatic login.
 */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.VipadAuth = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    const STORAGE_KEY_AUTH = 'vipadsathi_auth_credentials';
    const STORAGE_KEY_CITIZEN = 'vipadsathi_citizen_credentials';
    const STORAGE_KEY_AUTOLOGIN = 'vipadsathi_auto_login_enabled';

    const DEFAULT_AUTHORITY = {
        identifier: 'alex.sharma@nepalpolice.gov.np',
        password: 'Inspector@2026',
        name: 'Alex Sharma',
        designation: 'Traffic Inspector',
        organization: 'Nepal Traffic Police',
        employeeId: 'NTP-KTM-0472'
    };

    const DEFAULT_CITIZEN = {
        name: 'Alex Sharma',
        phone: '9841234567',
        password: 'Citizen@2026'
    };

    function safeGet(key, fallback) {
        try {
            const raw = localStorage.getItem(key);
            if (!raw) return fallback;
            return JSON.parse(raw);
        } catch (e) {
            console.warn('[VipadAuth] Storage read error for', key, e);
            return fallback;
        }
    }

    function safeSet(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.warn('[VipadAuth] Storage write error for', key, e);
            return false;
        }
    }

    // Auto-seed defaults into web storage if not present
    if (!localStorage.getItem(STORAGE_KEY_AUTH)) {
        safeSet(STORAGE_KEY_AUTH, DEFAULT_AUTHORITY);
    }
    if (!localStorage.getItem(STORAGE_KEY_CITIZEN)) {
        safeSet(STORAGE_KEY_CITIZEN, DEFAULT_CITIZEN);
    }
    if (localStorage.getItem(STORAGE_KEY_AUTOLOGIN) === null) {
        localStorage.setItem(STORAGE_KEY_AUTOLOGIN, 'true');
    }

    function showToast(msg) {
        const existing = document.getElementById('vipad-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.id = 'vipad-toast';
        toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1A252C;color:#F5F1E7;border:1px solid rgba(227,166,61,0.4);border-radius:30px;padding:10px 22px;font-size:14px;font-family:Inter,sans-serif;font-weight:500;box-shadow:0 8px 30px rgba(0,0,0,0.35);z-index:99999;display:flex;align-items:center;gap:10px;pointer-events:none;transition:opacity 0.25s ease;';
        toast.innerHTML = '<span style="color:#48bb78;font-size:16px;">✓</span> ' + msg;
        document.body.appendChild(toast);
        setTimeout(function () {
            toast.style.opacity = '0';
            setTimeout(function () { toast.remove(); }, 300);
        }, 1500);
    }

    const VipadAuth = {
        // Authority
        getAuthorityCredentials: function () {
            return safeGet(STORAGE_KEY_AUTH, DEFAULT_AUTHORITY);
        },

        saveAuthorityCredentials: function (identifier, password, extra) {
            const current = this.getAuthorityCredentials();
            const updated = Object.assign({}, current, {
                identifier: (identifier && identifier.trim()) ? identifier.trim() : current.identifier,
                password: (password && password.trim()) ? password.trim() : current.password,
                updatedAt: new Date().toISOString()
            }, extra || {});
            safeSet(STORAGE_KEY_AUTH, updated);
            localStorage.setItem(STORAGE_KEY_AUTOLOGIN, 'true');
            return updated;
        },

        // Citizen
        getCitizenCredentials: function () {
            return safeGet(STORAGE_KEY_CITIZEN, DEFAULT_CITIZEN);
        },

        saveCitizenCredentials: function (name, phone, password, extra) {
            const current = this.getCitizenCredentials();
            const updated = Object.assign({}, current, {
                name: (name && name.trim()) ? name.trim() : current.name,
                phone: (phone && phone.trim()) ? phone.trim() : current.phone,
                password: (password && password.trim()) ? password.trim() : current.password,
                updatedAt: new Date().toISOString()
            }, extra || {});
            safeSet(STORAGE_KEY_CITIZEN, updated);
            return updated;
        },

        isAutoLoginEnabled: function () {
            return localStorage.getItem(STORAGE_KEY_AUTOLOGIN) !== 'false';
        },

        setAutoLoginEnabled: function (val) {
            localStorage.setItem(STORAGE_KEY_AUTOLOGIN, val ? 'true' : 'false');
        },

        // Fast actions
        loginAsAuthority: function (customId, customPwd) {
            if (customId || customPwd) {
                this.saveAuthorityCredentials(customId, customPwd);
            }
            showToast('Logging in automatically with saved credentials...');
            setTimeout(function () {
                window.location.href = 'response-dashboard.html';
            }, 180);
        },

        goToCitizenReport: function () {
            // Ensure citizen credentials exist
            if (!localStorage.getItem(STORAGE_KEY_CITIZEN)) {
                safeSet(STORAGE_KEY_CITIZEN, DEFAULT_CITIZEN);
            }
            showToast('Logged in as Citizen — opening incident report...');
            setTimeout(function () {
                window.location.href = 'incident-report-page.html';
            }, 180);
        }
    };

    // Page event attachments
    document.addEventListener('DOMContentLoaded', function () {
        const rawPath = window.location.pathname.toLowerCase();
        const page = rawPath.split('/').pop() || 'landing-page.html';

        // 1. LANDING PAGE
        if (page === 'landing-page.html' || page === 'home-landing-page.html' || page === '' || page === 'index.html') {
            // A. Authority login buttons -> Auto login
            const allLinks = document.querySelectorAll('a');
            allLinks.forEach(function (link) {
                const href = (link.getAttribute('href') || '').toLowerCase();
                const text = link.textContent.toLowerCase().trim();

                // Authority login triggers
                if (href.includes('login-page') || text === 'log in' || text === 'authority log in' || text === 'sign in as an authority') {
                    link.addEventListener('click', function (e) {
                        e.preventDefault();
                        VipadAuth.loginAsAuthority();
                    });
                }

                // Citizen report triggers
                if (text === 'report an incident' || (href.includes('signup-role-selection') && text.includes('report'))) {
                    link.addEventListener('click', function (e) {
                        e.preventDefault();
                        VipadAuth.goToCitizenReport();
                    });
                }
            });
        }

        // 2. LOGIN PAGE
        if (page === 'login-page.html') {
            const urlParams = new URLSearchParams(window.location.search);
            const isLogout = urlParams.get('logout') === 'true' || urlParams.get('logout') === '1';

            const idInput = document.getElementById('loginIdentifier');
            const pwdInput = document.getElementById('password');
            const form = document.querySelector('.login-form') || document.querySelector('form');
            const authCreds = VipadAuth.getAuthorityCredentials();

            if (idInput && pwdInput) {
                idInput.value = authCreds.identifier || '';
                pwdInput.value = authCreds.password || '';

                // Show auto-saved status indicator
                const hint = document.createElement('div');
                hint.id = 'auth-saved-badge';
                hint.style.cssText = 'background:rgba(43,114,87,0.1);border:1px solid rgba(43,114,87,0.3);border-radius:8px;padding:10px 14px;margin-bottom:18px;font-size:13px;color:#24382f;display:flex;align-items:center;gap:9px;';
                hint.innerHTML = '<span style="color:#2b7257;font-weight:bold;font-size:15px;">✓</span> <span>Credentials auto-saved in web storage for <strong>' + (authCreds.name || 'Alex Sharma') + '</strong>.</span>';
                if (form) {
                    form.insertBefore(hint, form.firstChild);
                }
            }

            if (form) {
                form.onsubmit = function (e) {
                    e.preventDefault();
                    const enteredId = idInput ? idInput.value : '';
                    const enteredPwd = pwdInput ? pwdInput.value : '';
                    VipadAuth.saveAuthorityCredentials(enteredId, enteredPwd);
                    window.location.href = 'response-dashboard.html';
                    return false;
                };
            }

            // If not explicit logout, auto-redirect automatically!
            if (!isLogout && VipadAuth.isAutoLoginEnabled()) {
                const timer = setTimeout(function () {
                    if (idInput && pwdInput && idInput.value && pwdInput.value) {
                        VipadAuth.loginAsAuthority(idInput.value, pwdInput.value);
                    }
                }, 350);
                if (idInput) idInput.addEventListener('input', function () { clearTimeout(timer); });
                if (pwdInput) pwdInput.addEventListener('input', function () { clearTimeout(timer); });
            }
        }

        // 3. CITIZEN SIGNUP PAGE
        if (page === 'citizen-signup-page.html') {
            const urlParams = new URLSearchParams(window.location.search);
            const isEdit = urlParams.get('edit') === 'true';

            const nameInput = document.getElementById('citizenName');
            const phoneInput = document.getElementById('citizenPhone');
            const pwdInput = document.getElementById('citizenPassword');
            const confirmInput = document.getElementById('citizenConfirm');
            const form = document.querySelector('form.stack-form') || document.querySelector('form');
            const citizenCreds = VipadAuth.getCitizenCredentials();

            if (nameInput && phoneInput && pwdInput && confirmInput) {
                nameInput.value = citizenCreds.name || '';
                phoneInput.value = citizenCreds.phone || '';
                pwdInput.value = citizenCreds.password || '';
                confirmInput.value = citizenCreds.password || '';

                const hint = document.createElement('div');
                hint.style.cssText = 'background:rgba(43,114,87,0.1);border:1px solid rgba(43,114,87,0.3);border-radius:8px;padding:10px 14px;margin-bottom:18px;font-size:13px;color:#24382f;display:flex;align-items:center;gap:9px;';
                hint.innerHTML = '<span style="color:#2b7257;font-weight:bold;font-size:15px;">✓</span> <span>Citizen credentials auto-saved in web storage for <strong>' + (citizenCreds.name || 'Alex Sharma') + '</strong>.</span>';
                if (form) {
                    form.insertBefore(hint, form.firstChild);
                }
            }

            if (form) {
                form.onsubmit = function (e) {
                    e.preventDefault();
                    if (nameInput && phoneInput && pwdInput) {
                        VipadAuth.saveCitizenCredentials(nameInput.value, phoneInput.value, pwdInput.value);
                    }
                    window.location.href = 'incident-report-page.html';
                    return false;
                };
            }

            // Auto-continue to incident report if credentials already exist and not editing
            if (!isEdit && citizenCreds && citizenCreds.name && citizenCreds.phone) {
                const autoTimer = setTimeout(function () {
                    window.location.href = 'incident-report-page.html';
                }, 350);
                if (nameInput) nameInput.addEventListener('input', function () { clearTimeout(autoTimer); });
            }
        }

        // 4. SIGNUP ROLE SELECTION PAGE
        if (page === 'signup-role-selection.html') {
            const citizenCard = document.querySelector('a[href*="citizen-signup-page"]');
            if (citizenCard) {
                citizenCard.addEventListener('click', function (e) {
                    e.preventDefault();
                    VipadAuth.goToCitizenReport();
                });
            }

            const authorityCard = document.querySelector('a[href*="authority-signup-page"]');
            if (authorityCard) {
                authorityCard.addEventListener('click', function (e) {
                    e.preventDefault();
                    VipadAuth.loginAsAuthority();
                });
            }
        }

        // 5. INCIDENT REPORT PAGE
        if (page === 'incident-report-page.html') {
            const citizenCreds = VipadAuth.getCitizenCredentials();
            const nav = document.querySelector('.site-header .nav');
            if (nav && !document.getElementById('citizenReporterBadge')) {
                const badge = document.createElement('div');
                badge.id = 'citizenReporterBadge';
                badge.style.cssText = 'display:inline-flex;align-items:center;gap:8px;background:rgba(245,241,231,0.12);border:1px solid rgba(245,241,231,0.25);padding:5px 12px;border-radius:20px;font-size:12px;color:#F5F1E7;margin-left:auto;margin-right:12px;';
                badge.innerHTML = '<span style="width:20px;height:20px;border-radius:50%;background:#C23B22;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;">' + (citizenCreds.name ? citizenCreds.name.substring(0, 2).toUpperCase() : 'AS') + '</span><span>' + (citizenCreds.name || 'Alex Sharma') + ' · Verified Citizen</span>';

                const backHome = nav.querySelector('.back-home');
                if (backHome) {
                    nav.insertBefore(badge, backHome);
                } else {
                    nav.appendChild(badge);
                }
            }
        }

        // 6. LOGOUT LINKS
        document.querySelectorAll('a.header-logout, a.logout-link, a[href="login-page.html"]').forEach(function (link) {
            if (link.textContent.toLowerCase().includes('log out') || link.classList.contains('header-logout') || link.classList.contains('logout-link')) {
                link.href = 'login-page.html?logout=true';
            }
        });
    });

    return VipadAuth;
}));
