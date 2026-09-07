(function () {
    'use strict';
    let loadingPromise = null, initialized = false;
    const byId = id => document.getElementById(id);
    const setText = (id, value) => { const node = byId(id); if (node) node.textContent = value; };
    const trafficLevel = value => YangonTrafficColors.normalize(value) || 'Unknown';
    const getTrafficColor = value => YangonTrafficColors.getTrafficColor(value);
    const titleCase = value => String(value || '—').toLowerCase().replace(/(^|_)([a-z])/g, (_m, sep, letter) => `${sep ? ' ' : ''}${letter.toUpperCase()}`);

    function trafficModeLabel(data) {
        const modeLabel = String(data.traffic_mode_label || data.mode || '').toLowerCase();
        const source = String(data.traffic_source || data.source || '').toLowerCase();
        if (modeLabel === 'real-time' || modeLabel === 'real provider' || source === 'here') return 'Real-Time';
        if (modeLabel === 'mixed' || source.includes('+')) return 'Mixed';
        if (modeLabel === 'inferred' || source.includes('inferred') || source.includes('academic')) return 'Inferred';
        if (modeLabel === 'unknown' || source.includes('unknown')) return 'Unknown';
        return 'Inferred';
    }

    function formatTime(value) {
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Yangon' });
    }

    function currentYangonTime() {
        return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Yangon' });
    }

    function renderRoadList(id, roads, kind) {
        const container = byId(id);
        if (!container) return;
        container.innerHTML = '';
        if (!roads || roads.length === 0) {
            const emptyRow = document.createElement('tr');
            emptyRow.innerHTML = `<td colspan="4" class="empty-state">No relevant data</td>`;
            container.appendChild(emptyRow);
            return;
        }

        roads.forEach((road, index) => {
            const row = document.createElement('tr');
            
            const levelClass = trafficLevel(road.traffic_level).toLowerCase();
            const badge = `<span class="traffic-badge ${levelClass}">● ${road.traffic_level}</span>`;
            
            row.innerHTML = `
                <td><strong>${String(index + 1).padStart(2, '0')}</strong></td>
                <td><strong>${road.road_name || road.name || road.road_id}</strong></td>
                <td class="muted-text">${road.township || 'Yangon Area'}</td>
                <td>${badge}</td>
            `;
            container.appendChild(row);
        });
    }

    // New function for View All toggling
    window.toggleRoadList = function(listId, btn) {
        const list = byId(listId);
        if (!list) return;
        const isCollapsed = list.classList.contains('collapsed');
        if (isCollapsed) {
            list.classList.remove('collapsed');
            btn.innerHTML = 'Show less &uarr;';
        } else {
            list.classList.add('collapsed');
            btn.innerHTML = 'View all &rarr;';
        }
    };

    function render(data) {
        byId('dashboard-available').hidden = false;
        byId('dashboard-error-row').hidden = true;

        const mode = trafficModeLabel(data);
        const now = currentYangonTime();

        // Title Pill
        setText('traffic-mode-pill', '● ' + mode);
        const pill = byId('traffic-mode-pill');
        if (pill) {
            pill.className = `traffic-mode-pill mode-${mode.toLowerCase()}`;
        }

        // Status row (if still present in HTML, though we removed traffic-context)
        setText('last-updated-time', formatTime(data.yangon_local_time || data.snapshot_time) || now);

        // New KPI Cards
        const overallCondition = data.overall_condition || 'Light';
        setText('overall-condition', overallCondition);
        const conditionCard = byId('overall-condition-card');
        if (conditionCard) {
            conditionCard.className = `traffic-stat kpi-${overallCondition.toLowerCase()}`;
        }

        const supportedTownships = Number(data.supported_townships) || 0;
        const supportedSegments = Number(data.supported_segments) || 0;
        setText('township-count', supportedTownships);
        setText('segment-count', supportedSegments);

        // Hotspots and best flowing
        const hotspots = data.hotspots || data.most_congested || [];
        const best = data.best_flowing || [];
        const bestAreHeavy = best.length > 0 && best.every(road => trafficLevel(road.traffic_level) === 'Heavy');
        setText('best-flow-title', bestAreHeavy ? 'Best Available Flow' : 'Best Flowing Roads');
        renderRoadList('hotspot-list', hotspots, 'hotspot');
        renderRoadList('best-flow-list', best, 'best');

        setText('dashboard-subtitle', 'Current conditions across supported Yangon areas.');
        setState('', 'ready');
    }

    function renderError(message) {
        byId('dashboard-available').hidden = true;
        const errRow = byId('dashboard-error-row');
        if (errRow) {
            errRow.hidden = false;
            setText('dashboard-error-msg', message || 'Traffic data temporarily unavailable.');
        }
        setText('last-updated-time', currentYangonTime());
        setText('traffic-mode-pill', '● Error');
        setState('', 'ready');
    }

    function setState(message, type = 'ready') {
        const node = byId('dashboard-state');
        if (!node) return;
        node.textContent = message;
        node.dataset.state = type;
        node.hidden = (type === 'ready' || !message);
        byId('dashboard-view')?.classList.toggle('is-loading', type === 'loading');
    }

    async function refresh(force = false) {
        if (loadingPromise) return loadingPromise;
        const button = byId('refresh-traffic');
        if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
        loadingPromise = (force ? YangonApi.trafficOverview(true) : YangonApi.trafficOverview())
            .then(data => {
                if (!data || data.error) throw new Error(data?.error || 'No traffic data returned.');
                const hasData = Array.isArray(data.roads) && data.roads.length > 0;
                const hasHealth = data.traffic_health_score != null;
                if (!hasData && !hasHealth) throw new Error('No traffic data available.');
                render(data);
                initialized = true;
                return data;
            })
            .catch(error => {
                console.error('Traffic dashboard load failed:', error);
                renderError('Unable to load traffic data. Please retry.');
                return null;
            })
            .finally(() => {
                if (button) { button.disabled = false; button.removeAttribute('aria-busy'); }
                loadingPromise = null;
            });
        return loadingPromise;
    }

    function bind() {
        byId('refresh-traffic')?.addEventListener('click', () => refresh(true));
        byId('retry-traffic')?.addEventListener('click', () => refresh(true));
        if (window.location.protocol !== 'file:' || window.__yangonBridgeReady || window.pywebview?.api) refresh();
        window.addEventListener('pywebviewready', () => { if (!initialized) refresh(); });
        window.addEventListener('yangonbridgeavailable', () => { if (!initialized) refresh(); });
    }

    window.YangonDashboard = Object.freeze({ refresh, getTrafficColor });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true }); else bind();
}());
