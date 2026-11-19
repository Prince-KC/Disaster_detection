(() => {
    const profilesKey = 'vipsathi.profiles';
    const activeProfileKey = 'vipsathi.activeProfile';
    const incidentReportsKey = 'vipsathi.incidentReports';

    const readProfiles = () => {
        try {
            return JSON.parse(localStorage.getItem(profilesKey) || '{}');
        } catch {
            return {};
        }
    };

    const normalize = value => String(value || '').trim().toLowerCase();

    const initialsFor = name => name
        .trim()
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map(part => part[0].toUpperCase())
        .join('') || 'GU';

    const saveProfile = (profile, identifiers) => {
        const profiles = readProfiles();
        const savedProfile = { ...profile, identifiers: identifiers.map(normalize).filter(Boolean) };
        savedProfile.identifiers.forEach(identifier => { profiles[identifier] = savedProfile; });
        localStorage.setItem(profilesKey, JSON.stringify(profiles));
        return savedProfile;
    };

    const getIncidentReports = () => {
        try {
            const reports = JSON.parse(localStorage.getItem(incidentReportsKey) || '[]');
            return Array.isArray(reports) ? reports : [];
        } catch {
            return [];
        }
    };

    const saveIncidentReport = report => {
        const savedReport = { ...report, createdAt: new Date().toISOString() };
        const reports = [savedReport, ...getIncidentReports()].slice(0, 100);
        localStorage.setItem(incidentReportsKey, JSON.stringify(reports));
        return savedReport;
    };

    const renderHeaders = () => {
        let profile = null;
        try {
            profile = JSON.parse(localStorage.getItem(activeProfileKey) || 'null');
        } catch {
            profile = null;
        }

        const name = profile?.name || 'Guest';
        const title = profile?.title || (profile?.role === 'citizen' ? 'Citizen reporter' : 'Response member');
        document.querySelectorAll('.authority-user, .profile-chip').forEach(header => {
            const initials = header.querySelector('span');
            const displayName = header.querySelector('strong');
            const role = header.querySelector('small');
            if (initials) initials.textContent = initialsFor(name);
            if (displayName) displayName.textContent = name;
            if (role) role.textContent = title;
        });
    };

    const profileFromIdentifier = identifier => {
        const emailName = identifier.includes('@') ? identifier.split('@')[0] : '';
        const readableName = emailName
            .replace(/[._-]+/g, ' ')
            .replace(/\b\w/g, character => character.toUpperCase());
        return {
            name: readableName || 'Guest',
            role: 'authority',
            title: 'Response member',
            identifiers: [normalize(identifier)],
        };
    };

    const login = event => {
        event.preventDefault();
        const identifier = document.getElementById('loginIdentifier').value.trim();
        const profile = readProfiles()[normalize(identifier)] || profileFromIdentifier(identifier);
        localStorage.setItem(activeProfileKey, JSON.stringify(profile));
        window.location.href = 'response-dashboard.html';
    };

    const registerCitizen = event => {
        event.preventDefault();
        const profile = saveProfile({
            name: document.getElementById('citizenName').value.trim(),
            role: 'citizen',
            title: 'Citizen reporter',
        }, [document.getElementById('citizenPhone').value]);
        localStorage.setItem(activeProfileKey, JSON.stringify(profile));
        window.location.href = 'incident-report-page.html';
    };

    const registerAuthority = () => {
        saveProfile({
            name: document.getElementById('authorityName').value.trim(),
            role: 'authority',
            title: document.getElementById('designation').value.trim() || 'Response member',
        }, [
            document.getElementById('authorityEmail').value,
            document.getElementById('authorityPhone').value,
            document.getElementById('employeeId').value,
        ]);
    };

    document.querySelectorAll('.header-logout, .logout-link').forEach(link => {
        link.addEventListener('click', () => localStorage.removeItem(activeProfileKey));
    });

    window.VipsathiIdentity = {
        login,
        registerCitizen,
        registerAuthority,
        renderHeaders,
        getIncidentReports,
        saveIncidentReport,
    };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', renderHeaders, { once: true });
    } else {
        renderHeaders();
    }
})();