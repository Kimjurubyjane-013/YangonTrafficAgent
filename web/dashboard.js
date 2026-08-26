(function () {
    'use strict';
    let loadingPromise = null;
    let initialized = false;
    const byId = id => document.getElementById(id);
    const setText = (id, value) => { const node = byId(id); if (node) node.textContent = value; };
    const titleCase = value => String(value || '—').toLowerCase().replace(/(^|_)([a-z])/g, (_m, separator, letter) => `${separator ? ' ' : ''}${letter.toUpperCase()}`);
    const sourceLabel = value => ['here', 'here-traffic'].includes(value) ? 'HERE Traffic' : 'Academic Simulation';
    const formatTime = value => { const date = new Date(value); return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); };

    function setState(message, type = 'ready') {
        const node = byId('dashboard-state');
        if (!node) return;
        node.textContent = message;
        node.classList.toggle('error', type === 'error');
        node.hidden = type === 'ready';
    }

    function renderRoadList(id, roads, kind) {
        const container = byId(id);
        if (!container) return;
        container.replaceChildren();
        roads.slice(0, 5).forEach((road, index) => {
            const row = document.createElement('article');
            row.className = 'ranked-road dashboard-road-row';
            const rank = document.createElement('b');
            rank.textContent = String(index + 1).padStart(2, '0');
            const copy = document.createElement('span');
            const name = document.createElement('strong');
            const detail = document.createElement('small');
            name.textContent = road.road_name;
            detail.textContent = kind === 'hotspot'
                ? `${road.traffic_level} · Score ${road.traffic_score} · +${Number(road.estimated_delay_minutes || 0).toFixed(1)} min`
                : `${road.traffic_level} · ${road.average_speed_kmh} km/h`;
            copy.append(name, detail);
            row.append(rank, copy);
            container.appendChild(row);
        });
    }

    function renderTrends(roads, trendType) {
        const counts = { improving: 0, stable: 0, worsening: 0 };
        roads.forEach(road => { if (Object.prototype.hasOwnProperty.call(counts, road.trend)) counts[road.trend] += 1; });
        const container = byId('trend-summary');
        if (!container) return;
        container.replaceChildren();
        ['Improving', 'Stable', 'Worsening'].forEach(label => {
            const item = document.createElement('div');
            item.className = `trend-item ${label.toLowerCase()}`;
            const value = document.createElement('strong');
            const caption = document.createElement('span');
            value.textContent = counts[label.toLowerCase()];
            caption.textContent = label;
            item.append(value, caption);
            container.appendChild(item);
        });
        const note = document.querySelector('.model-note');
        if (note) note.textContent = trendType === 'simulated_adjacent_window'
            ? 'Simulated Trend — deterministic adjacent model windows, not measured history.'
            : 'Provider-backed traffic trend.';
    }

    function render(data) {
        setText('health-score', Number(data.traffic_health_score || 0).toFixed(0));
        setText('health-label', data.traffic_health_label || 'Unknown');
        setText('health-period', titleCase(data.time_period));
        const fill = byId('health-meter-fill');
        if (fill) fill.style.width = `${Math.max(0, Math.min(100, Number(data.traffic_health_score || 0)))}%`;
        setText('heavy-count', data.heavy_count ?? 0);
        setText('moderate-count', data.moderate_count ?? 0);
        setText('light-count', data.light_count ?? 0);
        setText('average-score', Number(data.average_traffic_score || 0).toFixed(1));
        setText('context-period', titleCase(data.time_period));
        setText('context-source', sourceLabel(data.source || data.model_type));
        setText('context-snapshot', formatTime(data.snapshot_time || data.generated_at));
        setText('context-rush', data.rush_hour ? 'Active' : 'Inactive');
        renderRoadList('hotspot-list', data.hotspots || data.most_congested || [], 'hotspot');
        renderRoadList('best-flow-list', data.best_flowing || [], 'best');
        const heading = byId('best-flow-list')?.previousElementSibling?.querySelector('h2');
        const best = data.best_flowing || [];
        if (heading) heading.textContent = best.length && best.every(road => road.traffic_level === 'Heavy') ? 'Best Available Flow' : 'Best Flowing Roads';
        renderTrends(data.roads || [], data.trend_type);
    }

    async function refresh() {
        if (loadingPromise) return loadingPromise;
        const button = byId('refresh-traffic');
        setState('Refreshing traffic analysis…', 'loading');
        if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
        loadingPromise = YangonApi.trafficOverview().then(data => {
            if (!data || data.error || !Array.isArray(data.roads)) throw new Error(data?.error || 'No traffic data returned.');
            render(data); initialized = true; setState('', 'ready'); return data;
        }).catch(error => {
            console.error('Traffic dashboard load failed:', error);
            setState('Traffic analysis is temporarily unavailable. Try Refresh Traffic.', 'error');
            throw error;
        }).finally(() => {
            if (button) { button.disabled = false; button.removeAttribute('aria-busy'); }
            loadingPromise = null;
        });
        return loadingPromise;
    }

    function bind() {
        byId('refresh-traffic')?.addEventListener('click', () => refresh().catch(() => {}));
        if (window.location.protocol !== 'file:' || window.__yangonBridgeReady || window.pywebview?.api) refresh().catch(() => {});
        window.addEventListener('pywebviewready', () => { if (!initialized) refresh().catch(() => {}); });
        window.addEventListener('yangonbridgeavailable', () => { if (!initialized) refresh().catch(() => {}); });
    }
    window.YangonDashboard = Object.freeze({ refresh });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true }); else bind();
}());
