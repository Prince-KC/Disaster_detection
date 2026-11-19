(() => {
    const alertList = document.querySelector('.alert-list');
    const situationStrip = document.querySelector('.situation-strip');
    if (!alertList || !situationStrip) return;

    const statusLabels = {
        unverified: 'Unverified',
        review: 'Under review',
        dispatched: 'Response dispatched',
        resolved: 'Resolved',
    };

    const normalizeStatus = value => String(value || 'unverified').toLowerCase();

    function getCitizenReports() {
        return (window.VipsathiIdentity?.getIncidentReports() || []).map(report => ({
            id: report.id,
            hrefId: report.id,
            source: report.source || 'Citizen report',
            sourceId: report.id,
            sourceType: 'citizen',
            title: report.type || 'Incident report',
            location: report.location || 'Location unavailable',
            description: report.description || 'No additional description was provided.',
            createdAt: report.createdAt,
            severity: report.severity || 'Medium',
            status: normalizeStatus(report.status),
        }));
    }

    async function getCameraDetections() {
        const apiBase = window.VIPSATHI_API_BASE_URL
            || `${window.location.protocol}//${window.location.hostname}:8000`;
        const response = await fetch(`${apiBase.replace(/\/$/, '')}/api/detections?limit=100`, {
            cache: 'no-store',
            headers: { Accept: 'application/json' },
        });
        if (!response.ok) throw new Error(`Detection API returned ${response.status}`);
        const payload = await response.json();
        const detections = Array.isArray(payload) ? payload : payload.detections || [];

        return detections.map(detection => {
            const metadata = detection.metadata || {};
            const createdAt = detection.created_at || metadata.timestamp || detection.timestamp;
            const device = detection.device_id || `CAM-0${metadata.cam_id || ''}`;
            const confidence = Number(detection.confidence);
            const confidencePercent = Number.isFinite(confidence)
                ? (confidence <= 1 ? confidence * 100 : confidence)
                : null;
            const title = String(detection.object_class || 'Disaster detected')
                .replace(/[_-]+/g, ' ')
                .replace(/\b\w/g, character => character.toUpperCase());

            return {
                id: `DET-${detection.id ?? `${device}-${createdAt || title}`}`,
                hrefId: `DET-${detection.id ?? `${device}-${createdAt || title}`}`,
                source: 'Camera detected',
                sourceId: device,
                sourceType: 'camera',
                title,
                location: metadata.location || metadata.location_name || 'Monitoring zone',
                description: confidencePercent === null
                    ? 'Disaster detected by camera AI.'
                    : `Disaster detected by camera AI · ${confidencePercent.toFixed(1)}% confidence`,
                createdAt,
                severity: confidencePercent >= 85 ? 'Critical' : confidencePercent >= 65 ? 'High' : 'Medium',
                status: 'unverified',
            };
        });
    }

    function timestamp(alert) {
        const value = new Date(alert.createdAt).getTime();
        return Number.isNaN(value) ? 0 : value;
    }

    function formatTime(value) {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return 'Time unavailable';
        return `${new Intl.DateTimeFormat('en-GB', {
            timeZone: 'Asia/Kathmandu', hour: '2-digit', minute: '2-digit',
        }).format(date)} NPT`;
    }

    function renderAlert(alert) {
        const row = document.createElement('a');
        row.href = `incident-detail.html?id=${encodeURIComponent(alert.hrefId)}`;
        row.className = `alert-row${alert.severity.toLowerCase() === 'critical' ? ' urgent' : ''}`;

        const source = document.createElement('div');
        source.className = `alert-source${alert.sourceType === 'citizen' ? ' citizen' : ''}`;
        source.appendChild(document.createElement('i'));
        const sourceName = document.createElement('span');
        sourceName.textContent = alert.source;
        const sourceId = document.createElement('small');
        sourceId.textContent = alert.sourceId || '';
        source.append(sourceName, sourceId);

        const main = document.createElement('div');
        main.className = 'alert-main';
        const title = document.createElement('strong');
        title.textContent = alert.title;
        const location = document.createElement('span');
        location.textContent = alert.location;
        const description = document.createElement('small');
        description.textContent = alert.description;
        main.append(title, location, description);

        const time = document.createElement('div');
        time.className = 'alert-time';
        const timeValue = document.createElement('span');
        timeValue.textContent = formatTime(alert.createdAt);
        const severity = document.createElement('b');
        severity.textContent = alert.severity;
        time.append(timeValue, severity);

        const status = document.createElement('div');
        status.className = `alert-status ${alert.status}`;
        status.textContent = statusLabels[alert.status] || 'Unverified';

        const arrow = document.createElement('span');
        arrow.className = 'row-arrow';
        arrow.textContent = '→';
        row.append(source, main, time, status, arrow);
        return row;
    }

    function updateMetrics(alerts) {
        const [activeMetric, unverifiedMetric, responseMetric, resolvedMetric] = situationStrip.children;
        const attentionCount = alerts.filter(alert => ['unverified', 'review'].includes(alert.status)).length;
        const unverifiedCount = alerts.filter(alert => alert.status === 'unverified').length;
        const cameraCount = alerts.filter(alert => alert.sourceType === 'camera' && alert.status === 'unverified').length;
        const responseCount = alerts.filter(alert => alert.status === 'dispatched').length;
        const resolvedCount = alerts.filter(alert => alert.status === 'resolved').length;
        const activeCount = alerts.length - resolvedCount;

        const updateMetric = (metric, label, value, detail) => {
            metric.querySelector('span').textContent = label;
            metric.querySelector('strong').textContent = value;
            metric.querySelector('small').textContent = detail;
        };

        updateMetric(activeMetric, 'Active incidents', activeCount, `${attentionCount} requiring attention`);
        updateMetric(unverifiedMetric, 'Unverified alerts', unverifiedCount, `${cameraCount} from cameras`);
        updateMetric(responseMetric, 'Responses in progress', responseCount, 'Status: response dispatched');
        updateMetric(resolvedMetric, 'Resolved incidents', resolvedCount, 'Based on incident status');
    }

    function updateOverviewTimestamp() {
        const eyebrow = document.querySelector('.authority-page-heading .eyebrow');
        if (!eyebrow) return;
        const now = new Date();
        eyebrow.textContent = `${new Intl.DateTimeFormat('en-GB', {
            timeZone: 'Asia/Kathmandu', weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        }).format(now)} NPT · Live incident picture`;
    }

    async function refreshOverview() {
        const alerts = getCitizenReports();
        try {
            alerts.push(...await getCameraDetections());
        } catch (error) {
            console.warn('Unable to refresh overview camera detections:', error);
        }

        alerts.sort((left, right) => timestamp(right) - timestamp(left));
        updateMetrics(alerts);
        alertList.replaceChildren();

        if (alerts.length === 0) {
            const empty = document.createElement('p');
            empty.textContent = 'No incident alerts yet.';
            alertList.appendChild(empty);
            return;
        }

        alerts.slice(0, 4).forEach(alert => alertList.appendChild(renderAlert(alert)));
    }

    updateOverviewTimestamp();
    refreshOverview();
    window.setInterval(refreshOverview, 15000);
})();