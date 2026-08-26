(function () {
    'use strict';

    const COLORS = Object.freeze({ Light: '#2f9e68', Moderate: '#d88918', Heavy: '#d94b42' });
    const YANGON_CENTER = [16.82, 96.15];
    let overview = null;
    let dashboardMap = null;
    let trafficMap = null;
    let dashboardLayers = [];
    let trafficLayers = [];
    let activeFilter = 'All';
    let loadingPromise = null;
    let initialized = false;

    const byId = id => document.getElementById(id);
    const text = (id, value) => { const node = byId(id); if (node) node.textContent = value; };
    const titleCase = value => String(value || '—').toLowerCase().replace(/(^|_)([a-z])/g, (_m, space, letter) => `${space ? ' ' : ''}${letter.toUpperCase()}`);
    const sourceLabel = value => value === 'here' ? 'HERE Traffic' : value === 'academic_simulation' ? 'Academic Simulation' : titleCase(value);
    const formatTime = value => {
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };
    const formatDelay = value => `${Number(value || 0).toFixed(1)} min`;

    function setDashboardState(message, type = 'ready') {
        const node = byId('dashboard-state');
        if (!node) return;
        node.textContent = message;
        node.dataset.state = type;
        node.hidden = type === 'ready';
    }

    function createMap(id, fallbackId) {
        const container = byId(id);
        if (!container || typeof L === 'undefined') return null;
        const instance = L.map(container, { zoomControl: true, preferCanvas: true }).setView(YANGON_CENTER, 12);
        const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors', maxZoom: 19,
        });
        let failures = 0;
        tiles.on('tileerror', () => {
            failures += 1;
            if (failures >= 3 && fallbackId) {
                const fallback = byId(fallbackId);
                if (fallback) fallback.hidden = false;
            }
        });
        tiles.addTo(instance);
        return instance;
    }

    function ensureMaps() {
        if (!dashboardMap) dashboardMap = createMap('dashboard-map', 'dashboard-map-fallback');
        if (!trafficMap) trafficMap = createMap('traffic-map');
    }

    function clearLayers(map, layers) {
        if (map) layers.forEach(layer => map.removeLayer(layer));
        layers.length = 0;
    }

    function renderRoadLayers(map, layers, filter, detailTarget) {
        if (!map || !overview) return;
        clearLayers(map, layers);
        const bounds = [];
        overview.roads
            .filter(road => filter === 'All' || road.traffic_level === filter)
            .forEach(road => {
                if (!Array.isArray(road.coordinates) || road.coordinates.length < 2) return;
                const color = COLORS[road.traffic_level] || '#647681';
                const casing = L.polyline(road.coordinates, { color: '#ffffff', weight: 8, opacity: 0.88, interactive: false }).addTo(map);
                const line = L.polyline(road.coordinates, { color, weight: 5, opacity: 0.92 }).addTo(map);
                line.bindTooltip(`${road.road_name} · ${road.traffic_level} · ${road.traffic_score}`, { sticky: true });
                line.on('click', () => renderRoadDetail(road, detailTarget));
                layers.push(casing, line);
                road.coordinates.forEach(point => bounds.push(point));
            });
        if (bounds.length) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14 });
    }

    function metric(label, value) {
        const row = document.createElement('div');
        const name = document.createElement('span');
        const content = document.createElement('strong');
        name.textContent = label;
        content.textContent = value;
        row.append(name, content);
        return row;
    }

    function renderRoadDetail(road, target = 'road-detail') {
        const container = byId(target);
        if (!container) return;
        if (target === 'road-detail') {
            byId('road-detail-empty').hidden = true;
            container.hidden = false;
        }
        container.replaceChildren();
        container.className = 'road-detail-content';
        const head = document.createElement('div');
        head.className = 'road-detail-head';
        const heading = document.createElement('h3');
        heading.textContent = road.road_name;
        const badge = document.createElement('span');
        badge.className = `traffic-badge ${String(road.traffic_level).toLowerCase()}`;
        badge.textContent = road.traffic_level;
        head.append(heading, badge);
        const grid = document.createElement('div');
        grid.className = 'road-metric-grid';
        [
            ['Road Type', titleCase(road.road_type)], ['Traffic Score', `${road.traffic_score} / 100`],
            ['Vehicle Density', `${road.vehicle_density}`], ['Congestion Pressure', `${Number(road.congestion_pressure || 0).toFixed(2)}`],
            ['Average Speed', `${road.average_speed_kmh} km/h`], ['Estimated Delay', formatDelay(road.estimated_delay_minutes)],
            ['Traffic Trend', titleCase(road.trend)], ['Traffic Source', sourceLabel(road.source)],
        ].forEach(([label, value]) => grid.appendChild(metric(label, value)));
        const why = document.createElement('div');
        why.className = 'road-reasons';
        const whyTitle = document.createElement('strong');
        whyTitle.textContent = 'Why this condition';
        const list = document.createElement('ul');
        (road.reasons || []).slice(0, 5).forEach(reason => {
            const item = document.createElement('li');
            item.textContent = reason;
            list.appendChild(item);
        });
        why.append(whyTitle, list);
        container.append(head, grid, why);
    }

    function renderRankedList(id, roads, kind) {
        const container = byId(id);
        if (!container) return;
        container.replaceChildren();
        if (!roads.length) {
            const empty = document.createElement('p');
            empty.className = 'dashboard-empty';
            empty.textContent = 'No road data is available for this ranking.';
            container.appendChild(empty);
            return;
        }
        roads.slice(0, 5).forEach((road, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'ranked-road';
            const rank = document.createElement('b');
            rank.textContent = String(index + 1).padStart(2, '0');
            const copy = document.createElement('span');
            const name = document.createElement('strong');
            name.textContent = road.road_name;
            const detail = document.createElement('small');
            detail.textContent = kind === 'hotspot'
                ? `${road.traffic_score} · ${road.traffic_level} · ${formatDelay(road.estimated_delay_minutes)} delay · ${titleCase(road.trend)}`
                : `${road.traffic_score} · ${road.average_speed_kmh} km/h · ${road.traffic_level}`;
            copy.append(name, detail);
            button.append(rank, copy);
            button.addEventListener('click', () => {
                renderRoadDetail(road, 'road-detail');
                byId('road-detail-card')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            });
            container.appendChild(button);
        });
    }

    function renderTrends(roads) {
        const counts = { worsening: 0, stable: 0, improving: 0 };
        roads.forEach(road => {
            if (Object.prototype.hasOwnProperty.call(counts, road.trend)) counts[road.trend] += 1;
        });
        const container = byId('trend-summary');
        if (!container) return;
        container.replaceChildren();
        [['Worsening', counts.worsening], ['Stable', counts.stable], ['Improving', counts.improving]].forEach(([label, count]) => {
            const item = document.createElement('div');
            item.className = `trend-item ${label.toLowerCase()}`;
            const value = document.createElement('strong');
            const caption = document.createElement('span');
            value.textContent = count;
            caption.textContent = label;
            item.append(value, caption);
            container.appendChild(item);
        });
    }

    function renderSummary(data) {
        text('health-score', Number(data.traffic_health_score || 0).toFixed(0));
        text('health-label', data.traffic_health_label || 'Unknown');
        text('health-period', `${titleCase(data.time_period)} · ${data.rush_hour ? 'Rush Hour Active' : 'Normal Demand'}`);
        const fill = byId('health-meter-fill');
        if (fill) fill.style.width = `${Math.max(0, Math.min(100, Number(data.traffic_health_score || 0)))}%`;
        text('heavy-count', data.heavy_count ?? 0);
        text('moderate-count', data.moderate_count ?? 0);
        text('light-count', data.light_count ?? 0);
        text('average-score', Number(data.average_traffic_score || 0).toFixed(1));
        text('context-period', titleCase(data.time_period));
        text('context-source', sourceLabel(data.source || data.model_type));
        text('context-snapshot', formatTime(data.snapshot_time || data.generated_at));
        text('context-rush', data.rush_hour ? 'Active' : 'Inactive');
        text('traffic-map-context', `${titleCase(data.time_period)} · ${sourceLabel(data.source || data.model_type)} · ${formatTime(data.snapshot_time)}`);
        renderRankedList('hotspot-list', data.hotspots || data.most_congested || [], 'hotspot');
        renderRankedList('best-flow-list', data.best_flowing || [], 'best');
        renderTrends(data.roads || []);
    }

    async function refresh() {
        if (loadingPromise) return loadingPromise;
        setDashboardState('Refreshing current traffic intelligence…', 'loading');
        const refreshButtons = [byId('refresh-traffic'), byId('traffic-map-refresh')].filter(Boolean);
        refreshButtons.forEach(button => { button.disabled = true; button.setAttribute('aria-busy', 'true'); });
        loadingPromise = YangonApi.trafficOverview()
            .then(data => {
                if (!data || data.error || !Array.isArray(data.roads)) throw new Error(data?.error || 'No traffic road data was returned.');
                overview = data;
                ensureMaps();
                renderSummary(data);
                renderRoadLayers(dashboardMap, dashboardLayers, 'All', 'road-detail');
                renderRoadLayers(trafficMap, trafficLayers, activeFilter, 'traffic-map-detail');
                setDashboardState('', 'ready');
                initialized = true;
                return data;
            })
            .catch(error => {
                console.error('Traffic dashboard load failed:', error);
                setDashboardState('Traffic intelligence is temporarily unavailable. Check the application connection and try Refresh Traffic.', 'error');
                throw error;
            })
            .finally(() => {
                refreshButtons.forEach(button => { button.disabled = false; button.removeAttribute('aria-busy'); });
                loadingPromise = null;
            });
        return loadingPromise;
    }

    function resizeMaps() {
        setTimeout(() => {
            dashboardMap?.invalidateSize();
            trafficMap?.invalidateSize();
        }, 50);
    }

    function bind() {
        byId('refresh-traffic')?.addEventListener('click', () => refresh().catch(() => {}));
        byId('traffic-map-refresh')?.addEventListener('click', () => refresh().catch(() => {}));
        document.querySelectorAll('[data-traffic-filter]').forEach(button => button.addEventListener('click', () => {
            activeFilter = button.dataset.trafficFilter;
            document.querySelectorAll('[data-traffic-filter]').forEach(item => item.classList.toggle('active', item === button));
            renderRoadLayers(trafficMap, trafficLayers, activeFilter, 'traffic-map-detail');
        }));
        const canUseHttp = window.location.protocol !== 'file:';
        if (canUseHttp || window.__yangonBridgeReady || window.pywebview?.api) refresh().catch(() => {});
        window.addEventListener('pywebviewready', () => { if (!initialized) refresh().catch(() => {}); });
        window.addEventListener('yangonbridgeavailable', () => { if (!initialized) refresh().catch(() => {}); });
    }

    window.YangonDashboard = Object.freeze({ refresh, resizeMaps, getOverview: () => overview });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true });
    else bind();
}());
