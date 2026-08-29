(function () {
    'use strict';
    let loadingPromise = null, initialized = false;
    const byId = id => document.getElementById(id);
    const setText = (id, value) => { const node = byId(id); if (node) node.textContent = value; };
    const trafficLevel = value => YangonTrafficColors.normalize(value) || 'Unknown';
    const getTrafficColor = value => YangonTrafficColors.getTrafficColor(value);
    const titleCase = value => String(value || '—').toLowerCase().replace(/(^|_)([a-z])/g, (_match, separator, letter) => `${separator ? ' ' : ''}${letter.toUpperCase()}`);

    function sourceLabel(value) {
        const source = String(value || '').toLowerCase();
        if (source.includes('here')) return 'HERE';
        if (source.includes('academic') || source === 'simulation') return 'Academic Simulation';
        return 'HERE';
    }

    function formatTime(value) {
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Yangon' });
    }

    function setState(message, type = 'ready') {
        const node = byId('dashboard-state');
        if (!node) return;
        node.textContent = message;
        node.dataset.state = type;
        node.classList.toggle('error', type === 'error');
        node.hidden = type === 'ready';
        byId('dashboard-view')?.classList.toggle('is-loading', type === 'loading');
    }

    function healthExplanation(data) {
        const total = Number(data.matched_road_count || data.roads?.length || 0);
        const heavy = Number(data.heavy_count || 0), moderate = Number(data.moderate_count || 0);
        if (!total) return 'No monitored roads were matched in this refresh.';
        if (heavy / total >= 0.35) return 'Heavy congestion affects a significant share of monitored roads.';
        if ((heavy + moderate) / total >= 0.5) return 'Several monitored roads are experiencing slower movement.';
        return 'Most monitored roads are flowing normally.';
    }

    function renderRoadList(id, roads, kind) {
        const container = byId(id);
        if (!container) return;
        container.replaceChildren();
        roads.slice(0, 5).forEach((road, index) => {
            const level = trafficLevel(road.traffic_level);
            const row = document.createElement('article');
            row.className = `ranked-road dashboard-road-row level-${level.toLowerCase()}`;
            const rank = document.createElement('b');
            rank.textContent = String(index + 1).padStart(2, '0');
            const indicator = document.createElement('i');
            indicator.className = 'road-level-indicator';
            indicator.style.backgroundColor = getTrafficColor(level);
            const copy = document.createElement('span'), name = document.createElement('strong'), detail = document.createElement('small');
            name.textContent = road.road_name || 'Unnamed Monitored Road';
            const details = [level];
            if (road.average_speed_kmh != null) details.push(`${road.average_speed_kmh} km/h`);
            if (kind === 'hotspot' && Number(road.estimated_delay_minutes) > 0) details.push(`+${Number(road.estimated_delay_minutes).toFixed(1)} min delay`);
            detail.textContent = details.join(' • ');
            copy.append(name, detail);
            row.append(rank, indicator, copy);
            container.appendChild(row);
        });
    }

    function renderUnavailable(data) {
        byId('dashboard-available').hidden = true;
        byId('traffic-unavailable').hidden = false;
        byId('traffic-context').classList.add('is-unavailable');
        setText('dashboard-subtitle', 'Smart route planning remains available while live traffic is offline.');
        setText('context-live', 'Unavailable');
        setText('context-period', titleCase(data.time_period));
        setText('context-source', sourceLabel(data.provider || data.source || data.traffic_source || data.model_type));
        const currentTime = formatTime(data.yangon_local_time || data.snapshot_time || data.generated_at || new Date());
        setText('context-snapshot', currentTime);
        setText('context-provider-updated', '—');
        setText('context-rush', data.rush_hour ? 'Active' : 'Inactive');
        setText('unavailable-time', currentTime);
        setText('unavailable-provider', sourceLabel(data.provider || data.source || data.traffic_source || data.model_type));
        setState('', 'ready');
    }

    function renderAvailable(data) {
        byId('traffic-unavailable').hidden = true;
        byId('dashboard-available').hidden = false;
        byId('traffic-context').classList.remove('is-unavailable');
        setText('dashboard-subtitle', 'Real-time traffic insights and smart route recommendations.');
        const score = Number(data.traffic_health_score);
        setText('health-score', Number.isFinite(score) ? score.toFixed(0) : '—');
        setText('health-label', data.traffic_health_label || 'Current Conditions');
        setText('health-explanation', healthExplanation(data));
        setText('health-period', `${titleCase(data.time_period)} Traffic Period`);
        const gauge = byId('health-meter-fill');
        if (gauge) gauge.style.setProperty('--health-value', `${Math.max(0, Math.min(100, score || 0)) * 1.8}deg`);
        setText('light-count', data.light_count ?? 0);
        setText('moderate-count', data.moderate_count ?? 0);
        setText('heavy-count', data.heavy_count ?? 0);
        setText('context-live', 'Live Traffic');
        setText('context-period', titleCase(data.time_period));
        setText('context-source', sourceLabel(data.provider || data.source || data.traffic_source || data.model_type));
        setText('context-snapshot', formatTime(data.yangon_local_time || data.snapshot_time || data.generated_at));
        setText('context-provider-updated', formatTime(data.provider_updated_at));
        setText('context-rush', data.rush_hour ? 'Active' : 'Inactive');
        renderRoadList('hotspot-list', data.hotspots || data.most_congested || [], 'hotspot');
        renderRoadList('best-flow-list', data.best_flowing || [], 'best');
        setState('', 'ready');
    }

    function render(data) {
        const available = data.available !== false && Array.isArray(data.roads) && data.roads.length > 0;
        if (available) renderAvailable(data); else renderUnavailable(data);
    }

    async function refresh(force = false) {
        if (loadingPromise) return loadingPromise;
        const button = byId('refresh-traffic');
        setState('Refreshing traffic intelligence…', 'loading');
        if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
        loadingPromise = (force ? YangonApi.trafficOverview(true) : YangonApi.trafficOverview())
            .then(data => {
                if (!data || data.error || !Array.isArray(data.roads)) throw new Error(data?.error || 'No traffic data returned.');
                render(data);
                initialized = true;
                return data;
            })
            .catch(error => {
                console.error('Traffic dashboard load failed:', error);
                renderUnavailable({ source: 'unavailable', generated_at: new Date().toISOString() });
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
