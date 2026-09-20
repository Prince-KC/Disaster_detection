document.addEventListener('DOMContentLoaded', () => {
    document.title = document.title.replace(/Rakshak/g, 'विपद्Sathi');
    const textWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    while (textWalker.nextNode()) textNodes.push(textWalker.currentNode);
    textNodes.forEach((node) => { node.nodeValue = node.nodeValue.replace(/Rakshak/g, 'विपद्Sathi'); });
    document.querySelectorAll('.authority-brand b').forEach((brand) => { brand.textContent = 'विपद्Sathi'; brand.style.color = '#ad503d'; brand.style.fontSize = '29px'; });
    document.querySelectorAll('.authority-brand .brand-mark').forEach((mark) => {
        mark.textContent = '';
        mark.style.width = '68px';
        mark.style.height = '68px';
        mark.style.background = "transparent url('../images/logo.png') center / contain no-repeat";
        mark.style.boxShadow = 'none';
    });
    if (!document.querySelector('.rakshak-site-footer')) {
        const footer = document.createElement('footer');
        footer.className = 'rakshak-site-footer';
        footer.innerHTML = '<div class="rakshak-footer-inner"><div class="rakshak-footer-brand"><a href="landing-page.html" class="rakshak-footer-logo"><span>R</span><strong>विपद्Sathi</strong></a><p>A shared line between cameras, citizens, and the authorities who respond.</p><div class="rakshak-footer-status"><i></i> Response network operational</div></div><div class="rakshak-footer-column"><h2>Operations</h2><a href="response-dashboard.html">Overview</a><a href="incident-alerts.html">Incident alerts</a><a href="live-map.html">Live map</a></div><div class="rakshak-footer-column"><h2>Network</h2><a href="live-cameras.html">Live cameras</a><a href="incident-history.html">Incident history</a><a href="authority-profile.html">Authority profile</a></div><div class="rakshak-footer-column"><h2>Support</h2><a href="authority-settings.html">Settings</a><a href="landing-page.html#how">How it works</a><a href="login-page.html">Account access</a></div></div><div class="rakshak-footer-bottom"><span>© 2026 विपद्Sathi · Detect · Alert · Respond</span><span>Kathmandu, Nepal</span></div>';
        document.body.appendChild(footer);
    }

    if (!document.querySelector('#rakshak-footer-style')) {
        const style = document.createElement('style');
        style.id = 'rakshak-footer-style';
        style.textContent = '.rakshak-site-footer{margin-top:28px;padding:52px 48px 24px;background:#eee8dd;border-top:4px solid #ad503d;color:#24382f}.rakshak-footer-inner{width:min(1260px,100%);margin:0 auto;display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:36px}.rakshak-footer-logo{display:inline-flex;align-items:center;gap:9px}.rakshak-footer-logo span{display:grid;place-items:center;width:30px;height:30px;border-radius:6px;background:#ad503d;color:#fff;font:600 18px Georgia,serif}.rakshak-footer-logo strong{font:600 20px Georgia,serif}.rakshak-footer-brand p{max-width:300px;margin:15px 0 0;color:#66736a;font-size:12px;line-height:1.65}.rakshak-footer-status{display:flex;align-items:center;gap:8px;margin-top:18px;color:#66736a;font-size:11px}.rakshak-footer-status i{width:7px;height:7px;border-radius:50%;background:#4b6b45;box-shadow:0 0 0 4px rgba(75,107,69,.12)}.rakshak-footer-column h2{margin:3px 0 15px;color:#4b6b45;font-size:10px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.rakshak-footer-column a{display:flex;gap:8px;width:max-content;margin-bottom:11px;color:#596960;font-size:12px}.rakshak-footer-column a:before{content:"→";color:#ad503d}.rakshak-footer-column a:hover{color:#1c2521}.rakshak-footer-bottom{width:min(1260px,100%);margin:38px auto 0;padding-top:17px;border-top:1px solid rgba(36,56,47,.16);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:#66736a;font-size:10px}@media(max-width:760px){.rakshak-site-footer{padding:40px 16px 22px}.rakshak-footer-inner{grid-template-columns:1fr 1fr;gap:28px}.rakshak-footer-brand{grid-column:1/-1}}@media(max-width:480px){.rakshak-footer-inner{grid-template-columns:1fr}.rakshak-footer-brand{grid-column:auto}.rakshak-footer-bottom{display:grid;gap:5px}}';
        document.head.appendChild(style);
    }

    document.querySelectorAll('[data-filter-target]').forEach((control) => {
        const target = document.querySelector(control.dataset.filterTarget);
        if (!target) return;
        const apply = () => {
            const query = control.value.toLowerCase().trim();
            target.querySelectorAll('[data-searchable]').forEach((item) => {
                item.hidden = query && !item.textContent.toLowerCase().includes(query);
            });
        };
        control.addEventListener('input', apply);
        control.addEventListener('change', apply);
    });
    document.querySelectorAll('[data-tabs]').forEach((tabs) => {
        const target = document.querySelector(tabs.dataset.tabs);
        if (!target) return;
        tabs.querySelectorAll('.filter-tab').forEach((tab) => tab.addEventListener('click', () => {
            tabs.querySelectorAll('.filter-tab').forEach((item) => item.classList.remove('active'));
            tab.classList.add('active');
            const value = tab.dataset.value;
            target.querySelectorAll('[data-status]').forEach((item) => {
                item.hidden = value !== 'all' && item.dataset.status !== value;
            });
        }));
    });
    document.querySelectorAll('[data-action]').forEach((button) => button.addEventListener('click', () => {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = button.dataset.action + ' recorded';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2200);
    }));
    document.querySelectorAll('.header-bell').forEach((button) => button.addEventListener('click', () => {
        window.location.href = 'incident-alerts.html';
    }));
});
