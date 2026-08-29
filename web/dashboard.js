(function () {
    'use strict';
    let loadingPromise = null, initialized = false, dashboardMap = null, roadLayer = null, graphData = null;
    const byId = id => document.getElementById(id);
    const setText = (id, value) => { const node = byId(id); if (node) node.textContent = value; };
    const trafficLevel = value => YangonTrafficColors.normalize(value) || 'Unknown';
    const getTrafficColor = value => YangonTrafficColors.getTrafficColor(value);
    const titleCase = value => String(value || '—').toLowerCase().replace(/(^|_)([a-z])/g, (_m, separator, letter) => `${separator ? ' ' : ''}${letter.toUpperCase()}`);
    const sourceLabel = value => {
        const source = String(value || '').toLowerCase();
        if (source.includes('here')) return 'HERE Real-Time Traffic';
        if (source.includes('academic') || source === 'simulation') return 'Academic Simulation';
        return 'Real-Time Traffic Unavailable';
    };
    const formatTime = value => {
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Yangon' });
    };

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
        if (data.available === false) return 'Real-time traffic data is currently unavailable.';
        const total = Number(data.matched_road_count || data.roads?.length || 0);
        if (!total) return 'No monitored roads were matched in this refresh.';
        const heavy = Number(data.heavy_count || 0), moderate = Number(data.moderate_count || 0);
        if (heavy / total >= 0.35) return 'Heavy congestion affects a significant share of monitored roads.';
        if ((heavy + moderate) / total >= 0.5) return 'Several monitored roads are experiencing slower movement.';
        return 'Most monitored roads are flowing normally.';
    }

    function renderRoadList(id, roads, kind) {
        const container = byId(id);
        if (!container) return;
        container.replaceChildren();
        if (!roads.length) {
            const empty = document.createElement('p');
            empty.className = 'ranked-road-empty';
            empty.textContent = 'No provider-backed road data is available.';
            container.appendChild(empty);
            return;
        }
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
            else if (kind === 'hotspot' && road.traffic_score != null) details.push(`Score ${road.traffic_score}`);
            detail.textContent = details.join(' • ');
            copy.append(name, detail);
            row.append(rank, indicator, copy);
            container.appendChild(row);
        });
    }

    function renderTrends(roads, trendType) {
        const counts = { improving: 0, stable: 0, worsening: 0 }, container = byId('trend-summary');
        roads.forEach(road => { if (Object.prototype.hasOwnProperty.call(counts, road.trend)) counts[road.trend] += 1; });
        if (!container) return;
        container.replaceChildren();
        if (!roads.length || trendType === 'unavailable') {
            const message = document.createElement('p');
            message.className = 'trend-empty';
            message.textContent = 'No provider trend evidence is available for this refresh.';
            container.appendChild(message);
            const note = document.querySelector('.model-note');
            if (note) note.textContent = 'Traffic trends appear only when supported by provider data or explicit simulation mode.';
            return;
        }
        const icons = { Improving: '↗', Stable: '→', Worsening: '↘' };
        ['Improving', 'Stable', 'Worsening'].forEach(label => {
            const item = document.createElement('div'), icon = document.createElement('i'), value = document.createElement('strong'), caption = document.createElement('span');
            item.className = `trend-item ${label.toLowerCase()}`;
            icon.textContent = icons[label]; value.textContent = counts[label.toLowerCase()]; caption.textContent = label;
            item.append(icon, value, caption); container.appendChild(item);
        });
        const note = document.querySelector('.model-note');
        if (note) note.textContent = trendType === 'simulated_adjacent_window'
            ? 'Simulated trend — deterministic adjacent model windows, not measured history.'
            : 'Provider-backed traffic trend for this refresh.';
    }

    function ensureMap() {
        if (dashboardMap || !window.L || !byId('dashboard-traffic-map')) return;
        dashboardMap = L.map('dashboard-traffic-map', { zoomControl: true, attributionControl: true, preferCanvas: true }).setView([16.8409, 96.1735], 12);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            maxZoom: 19, attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
        }).addTo(dashboardMap);
        roadLayer = L.featureGroup().addTo(dashboardMap);
    }

    function graphRoads() {
        if (!graphData?.coords || !Array.isArray(graphData?.edges)) return [];
        const seen = new Set(), roads = [];
        graphData.edges.forEach(([start, end]) => {
            const key = [start, end].sort().join('|');
            if (seen.has(key) || !graphData.coords[start] || !graphData.coords[end]) return;
            seen.add(key);
            roads.push({ road_name: `${start} — ${end}`, coordinates: [graphData.coords[start], graphData.coords[end]], traffic_level: 'Unknown' });
        });
        return roads;
    }

    function popupContent(road) {
        const wrapper = document.createElement('div'), title = document.createElement('strong');
        wrapper.className = 'traffic-road-popup'; title.textContent = road.road_name || 'Monitored Road'; wrapper.appendChild(title);
        const fields = [
            ['Traffic', trafficLevel(road.traffic_level)],
            ['Current Speed', road.average_speed_kmh == null ? null : `${road.average_speed_kmh} km/h`],
            ['Delay', road.estimated_delay_minutes == null ? null : `${Number(road.estimated_delay_minutes).toFixed(1)} min`],
            ['Traffic Score', road.traffic_score], ['Source', road.traffic_source || road.source],
        ];
        fields.filter(([, value]) => value != null && value !== '').forEach(([label, value]) => {
            const line = document.createElement('span'); line.textContent = `${label}: ${value}`; wrapper.appendChild(line);
        });
        return wrapper;
    }

    function renderMap(data) {
        ensureMap();
        if (!dashboardMap || !roadLayer) return;
        roadLayer.clearLayers();
        const providerRoads = (data.roads || []).filter(road => Array.isArray(road.coordinates) && road.coordinates.length > 1);
        const roads = providerRoads.length ? providerRoads : graphRoads();
        roads.forEach(road => {
            const color = getTrafficColor(trafficLevel(road.traffic_level));
            const outline = L.polyline(road.coordinates, { color: '#ffffff', weight: 8, opacity: 0.65, lineCap: 'round', interactive: false });
            const line = L.polyline(road.coordinates, { color, weight: 5, opacity: 0.94, lineCap: 'round' });
            line.bindTooltip(road.road_name || 'Monitored Road', { sticky: true }); line.bindPopup(popupContent(road));
            line.on('mouseover', () => line.setStyle({ weight: 7 })); line.on('mouseout', () => line.setStyle({ weight: 5 }));
            roadLayer.addLayer(outline); roadLayer.addLayer(line);
        });
        byId('dashboard-map-empty').hidden = roads.length > 0;
        if (roads.length) dashboardMap.fitBounds(roadLayer.getBounds(), { padding: [24, 24], maxZoom: 14 });
        window.setTimeout(() => dashboardMap.invalidateSize(false), 0);
    }

    function renderInsight(data) {
        const available = data.available !== false && Array.isArray(data.roads) && data.roads.length > 0;
        setText('matched-road-count', available ? (data.matched_road_count ?? data.roads.length) : '—');
        setText('flow-record-count', available ? (data.flow_record_count ?? '—') : '—');
        if (!available) {
            setText('city-insight', 'Real-time traffic evidence is unavailable. Monitored roads remain visible in neutral gray without inferred conditions.');
            return;
        }
        const counts = [['Light', Number(data.light_count || 0)], ['Moderate', Number(data.moderate_count || 0)], ['Heavy', Number(data.heavy_count || 0)]].sort((a, b) => b[1] - a[1]);
        const hotspot = (data.hotspots || data.most_congested || [])[0];
        const dominant = counts[0][1] > 0 ? `${counts[0][0].toLowerCase()} traffic` : 'mixed conditions';
        setText('city-insight', `Most matched monitored roads currently show ${dominant}.${hotspot?.road_name ? ` The highest current congestion is on ${hotspot.road_name}.` : ''}`);
    }

    function render(data) {
        const available = data.available !== false, score = available && data.traffic_health_score != null ? Number(data.traffic_health_score) : null;
        setText('health-score', score == null ? '—' : score.toFixed(0)); setText('health-label', data.traffic_health_label || 'Unavailable');
        setText('health-explanation', healthExplanation(data)); setText('health-period', `${titleCase(data.time_period)} Traffic Period`);
        const gauge = byId('health-meter-fill');
        if (gauge) gauge.style.setProperty('--health-value', `${Math.max(0, Math.min(100, score || 0)) * 1.8}deg`);
        setText('heavy-count', available ? (data.heavy_count ?? 0) : '—'); setText('moderate-count', available ? (data.moderate_count ?? 0) : '—');
        setText('light-count', available ? (data.light_count ?? 0) : '—'); setText('average-score', available && data.average_traffic_score != null ? Number(data.average_traffic_score).toFixed(1) : '—');
        setText('context-live', available ? 'Live Traffic' : 'Unavailable'); setText('context-period', titleCase(data.time_period));
        setText('context-source', sourceLabel(data.source || data.traffic_source || data.model_type));
        setText('context-snapshot', formatTime(data.yangon_local_time || data.snapshot_time || data.generated_at));
        setText('context-provider-updated', formatTime(data.provider_updated_at)); setText('context-rush', data.rush_hour ? 'Active' : 'Inactive');
        byId('traffic-context')?.classList.toggle('is-unavailable', !available);
        renderRoadList('hotspot-list', data.hotspots || data.most_congested || [], 'hotspot'); renderRoadList('best-flow-list', data.best_flowing || [], 'best');
        renderTrends(data.roads || [], data.trend_type); renderMap(data); renderInsight(data);
        if (!available) setState('Real-time traffic data is currently unavailable.', 'error');
    }

    async function refresh(force = false) {
        if (loadingPromise) return loadingPromise;
        const button = byId('refresh-traffic'); setState('Refreshing traffic intelligence…', 'loading');
        if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
        loadingPromise = Promise.all([force ? YangonApi.trafficOverview(true) : YangonApi.trafficOverview(), graphData ? Promise.resolve(graphData) : YangonApi.graph().catch(() => null)])
            .then(([data, graph]) => {
                if (!data || data.error || !Array.isArray(data.roads)) throw new Error(data?.error || 'No traffic data returned.');
                graphData = graph; render(data); initialized = true; if (data.available !== false) setState('', 'ready'); return data;
            }).catch(error => { console.error('Traffic dashboard load failed:', error); setState('Traffic intelligence could not be refreshed. Please try again.', 'error'); throw error; })
            .finally(() => { if (button) { button.disabled = false; button.removeAttribute('aria-busy'); } loadingPromise = null; });
        return loadingPromise;
    }

    function bind() {
        byId('refresh-traffic')?.addEventListener('click', () => refresh(true).catch(() => {}));
        if (window.location.protocol !== 'file:' || window.__yangonBridgeReady || window.pywebview?.api) refresh().catch(() => {});
        window.addEventListener('pywebviewready', () => { if (!initialized) refresh().catch(() => {}); });
        window.addEventListener('yangonbridgeavailable', () => { if (!initialized) refresh().catch(() => {}); });
        window.addEventListener('resize', () => dashboardMap?.invalidateSize(false));
    }
    window.YangonDashboard = Object.freeze({ refresh, getTrafficColor });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true }); else bind();
}());
