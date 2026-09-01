(function () {
    'use strict';
    let loadingPromise = null, initialized = false, dashboardMap = null, trafficLayer = null;
    const byId = id => document.getElementById(id);
    const setText = (id, value) => { const node = byId(id); if (node) node.textContent = value; };
    const trafficLevel = value => YangonTrafficColors.normalize(value) || 'Unknown';
    const getTrafficColor = value => YangonTrafficColors.getTrafficColor(value);
    const titleCase = value => String(value || '—').toLowerCase().replace(/(^|_)([a-z])/g, (_m, sep, letter) => `${sep ? ' ' : ''}${letter.toUpperCase()}`);

    // ----------------------------------------------------------------
    // Source label helpers
    // ----------------------------------------------------------------
    function trafficModeLabel(data) {
        const modeLabel = String(data.traffic_mode_label || data.mode || '').toLowerCase();
        const source = String(data.traffic_source || data.source || '').toLowerCase();
        if (modeLabel === 'real-time' || modeLabel === 'real provider' || source === 'here') return 'Real-Time';
        if (modeLabel === 'mixed' || source.includes('+')) return 'Mixed';
        if (modeLabel === 'inferred' || source.includes('inferred') || source.includes('academic')) return 'Inferred';
        if (modeLabel === 'unknown' || source.includes('unknown')) return 'Unknown';
        return 'Inferred';
    }

    function providerStatusNote(data) {
        const mode = trafficModeLabel(data);
        if (mode === 'Real-Time') return 'HERE real-time traffic is active for all monitored roads.';
        if (mode === 'Real Provider') return 'HERE real-time traffic active — all data is provider-backed.';
        if (mode === 'Mixed') {
            const pct = Number(data.provider_coverage_percent || 0);
            const ipct = Number(data.inferred_coverage_percent || 0);
            return `HERE matched ${pct.toFixed(0)}% of roads. Remaining ${ipct.toFixed(0)}% estimated by inferred traffic model.`;
        }
        return 'HERE traffic unavailable — all data estimated by inferred traffic model based on time-of-day, road type, and context.';
    }

    function roadSourceBadge(road) {
        const src = String(road.source || road.traffic_source || '').toLowerCase();
        if (src.includes('here')) return 'HERE';
        if (src.includes('inferred') || src.includes('academic')) return 'INFERRED';
        if (src.includes('unknown')) return 'UNKNOWN';
        return 'INFERRED';
    }

    function formatTime(value) {
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Yangon' });
    }

    function currentYangonTime() {
        return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Yangon' });
    }

    // ----------------------------------------------------------------
    // Health explanation from effective traffic data
    // ----------------------------------------------------------------
    function healthExplanation(data) {
        const total = Number(data.total_roads || (data.roads || []).length || 0);
        const heavy = Number(data.heavy_count || 0);
        const moderate = Number(data.moderate_count || 0);
        const light = Number(data.light_count || 0);
        if (!total) return 'No traffic data available for this period.';
        if (heavy / total >= 0.35) return 'Heavy congestion affects a significant share of monitored roads.';
        if ((heavy + moderate) / total >= 0.5) return 'Several roads are experiencing slower movement.';
        if (light / total >= 0.6) return 'Most monitored roads are flowing freely.';
        return 'Traffic conditions are mixed across monitored roads.';
    }

    // ----------------------------------------------------------------
    // Average speed from road data
    // ----------------------------------------------------------------
    function computeAverageSpeed(roads) {
        const withSpeed = (roads || []).filter(r => r.average_speed_kmh != null && r.average_speed_kmh > 0);
        if (!withSpeed.length) return null;
        return Math.round(withSpeed.reduce((sum, r) => sum + r.average_speed_kmh, 0) / withSpeed.length);
    }

    function ensureTrafficMap() {
        if (dashboardMap || !window.L || !byId('dashboard-traffic-map')) return dashboardMap;
        dashboardMap = L.map('dashboard-traffic-map', { zoomControl: true, attributionControl: true })
            .setView([16.8409, 96.1735], 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors',
        }).addTo(dashboardMap);
        trafficLayer = L.layerGroup().addTo(dashboardMap);
        return dashboardMap;
    }

    function renderTrafficMap(roads) {
        const map = ensureTrafficMap();
        if (!map || !trafficLayer) return;
        trafficLayer.clearLayers();
        const bounds = [];
        (roads || []).forEach(road => {
            if (!Array.isArray(road.coordinates) || road.coordinates.length < 2) return;
            const points = road.coordinates.filter(point => Array.isArray(point) && point.length >= 2);
            if (points.length < 2) return;
            const level = trafficLevel(road.traffic_level);
            const line = L.polyline(points, {
                color: getTrafficColor(level), weight: 6, opacity: .88,
                lineCap: 'round', lineJoin: 'round',
            });
            const popup = document.createElement('div');
            const name = document.createElement('strong');
            const detail = document.createElement('span');
            name.textContent = road.road_name || 'Unnamed Road';
            detail.textContent = `${level} Â· ${road.average_speed_kmh ?? 'â€”'} km/h Â· ${roadSourceBadge(road)}`;
            popup.append(name, document.createElement('br'), detail);
            line.bindPopup(popup).addTo(trafficLayer);
            bounds.push(...points);
        });
        if (bounds.length) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 13 });
        setTimeout(() => map.invalidateSize(false), 0);
    }

    function renderDistribution(data) {
        const node = byId('traffic-distribution');
        if (!node) return;
        node.replaceChildren();
        const total = Math.max(1, Number(data.total_roads || 0));
        [['Light', data.light_count], ['Moderate', data.moderate_count], ['Heavy', data.heavy_count]].forEach(([label, raw]) => {
            const value = Number(raw || 0), pct = value / total * 100;
            const row = document.createElement('div');
            row.className = `distribution-row ${label.toLowerCase()}`;
            const copy = document.createElement('span'); copy.textContent = label;
            const bar = document.createElement('i'); bar.style.setProperty('--distribution', `${pct}%`);
            const metric = document.createElement('strong'); metric.textContent = `${value} / ${Number(data.total_roads || 0)}`;
            row.append(copy, bar, metric); node.appendChild(row);
        });
    }

    function renderWeather(data) {
        const live = data && data.status === 'live' && !data.error;
        byId('weather-card')?.classList.toggle('is-unavailable', !live);
        setText('weather-status', live ? 'Live Weather' : 'Unavailable');
        if (!live) {
            setText('weather-condition', 'Weather Temporarily Unavailable');
            setText('weather-temperature', 'â€”');
            setText('weather-humidity', 'â€”'); setText('weather-wind', 'â€”'); setText('weather-precipitation', 'â€”');
            setText('weather-risk', 'Not Evaluated');
            setText('weather-reason', 'Routing and traffic analysis remain available. No weather values are fabricated.');
            setText('weather-updated', 'Open-Meteo unavailable');
            window.YangonWeatherSnapshot = null;
            return;
        }
        window.YangonWeatherSnapshot = data;
        setText('weather-condition', data.condition);
        setText('weather-temperature', `${Number(data.temperature_c).toFixed(1)}Â°C`);
        setText('weather-humidity', `${data.humidity_percent}%`);
        setText('weather-wind', `${data.wind_speed_kmh} km/h`);
        setText('weather-precipitation', `${data.precipitation_mm} mm`);
        setText('weather-risk', `${data.traffic_impact?.risk || 'Unknown'} Risk`);
        setText('weather-reason', data.traffic_impact?.reason || 'No weather rule explanation is available.');
        setText('weather-updated', `Updated ${formatTime(data.observed_at)}`);
    }

    // ----------------------------------------------------------------
    // Road list rows (hotspots / best flowing)
    // ----------------------------------------------------------------
    function renderRoadList(id, roads, kind) {
        const container = byId(id);
        if (!container) return;
        container.replaceChildren();
        (roads || []).slice(0, 5).forEach((road, index) => {
            const level = trafficLevel(road.traffic_level);
            const row = document.createElement('article');
            row.className = `ranked-road dashboard-road-row level-${level.toLowerCase()}`;

            const rank = document.createElement('b');
            rank.textContent = String(index + 1).padStart(2, '0');

            const indicator = document.createElement('i');
            indicator.className = 'road-level-indicator';
            indicator.style.backgroundColor = getTrafficColor(level);

            const copy = document.createElement('span');
            const name = document.createElement('strong');
            const detail = document.createElement('small');
            name.textContent = road.road_name || 'Unnamed Road';

            const details = [level];
            if (road.average_speed_kmh != null) details.push(`${road.average_speed_kmh} km/h`);
            if (kind === 'hotspot' && Number(road.estimated_delay_minutes) > 0) {
                details.push(`+${Number(road.estimated_delay_minutes).toFixed(1)} min`);
            }

            // Source badge
            const srcBadge = document.createElement('span');
            srcBadge.className = `road-src-badge road-src-${roadSourceBadge(road).toLowerCase()}`;
            srcBadge.textContent = roadSourceBadge(road);

            detail.textContent = details.join(' · ');
            copy.append(name, detail);
            row.append(rank, indicator, copy, srcBadge);
            container.appendChild(row);
        });

        // Empty state
        if (!roads || roads.length === 0) {
            const empty = document.createElement('p');
            empty.className = 'ranked-road-empty';
            empty.textContent = kind === 'hotspot' ? 'No congestion data available.' : 'No flow data available.';
            container.appendChild(empty);
        }
    }

    // ----------------------------------------------------------------
    // Coverage bars
    // ----------------------------------------------------------------
    function renderCoverageBars(data) {
        const container = byId('coverage-bars');
        if (!container) return;
        container.replaceChildren();

        const provPct = Number(data.provider_coverage_percent || 0);
        const infPct = Number(data.inferred_coverage_percent || 0);
        const unkPct = Number.isFinite(Number(data.unknown_coverage_percent))
            ? Number(data.unknown_coverage_percent)
            : Math.max(0, 100 - provPct - infPct);

        const bars = [
            { label: 'HERE', pct: provPct, cls: 'cov-provider' },
            { label: 'Inferred', pct: infPct, cls: 'cov-inferred' },
            { label: 'Unknown', pct: unkPct, cls: 'cov-unknown' },
        ];

        bars.forEach(({ label, pct, cls }) => {
            if (pct <= 0) return;
            const item = document.createElement('div');
            item.className = `coverage-item ${cls}`;

            const bar = document.createElement('div');
            bar.className = 'coverage-bar-track';
            const fill = document.createElement('div');
            fill.className = 'coverage-bar-fill';
            fill.style.width = `${pct}%`;
            bar.appendChild(fill);

            const labelEl = document.createElement('span');
            labelEl.className = 'coverage-label';
            labelEl.textContent = label;

            const pctEl = document.createElement('span');
            pctEl.className = 'coverage-pct';
            pctEl.textContent = `${pct.toFixed(0)}%`;

            const meta = document.createElement('div');
            meta.className = 'coverage-meta';
            meta.append(labelEl, pctEl);

            item.append(meta, bar);
            container.appendChild(item);
        });
    }

    // ----------------------------------------------------------------
    // Main render — always renders if any data is present
    // ----------------------------------------------------------------
    function render(data) {
        // Always show dashboard with available data (inferred or real)
        byId('dashboard-available').hidden = false;
        byId('dashboard-error-row').hidden = true;

        const mode = trafficModeLabel(data);
        const now = currentYangonTime();

        // Status row
        setText('context-snapshot', formatTime(data.yangon_local_time || data.snapshot_time) || now);
        setText('context-live', mode);
        setText('context-period', titleCase(data.time_period));
        setText('context-rush', data.rush_hour ? 'Active' : 'Inactive');
        setText('context-provider-updated', data.provider_updated_at ? formatTime(data.provider_updated_at) : '—');

        // Traffic Health
        const score = Number(data.traffic_health_score);
        setText('health-score', Number.isFinite(score) ? score.toFixed(0) : '—');
        setText('health-label', data.traffic_health_label || 'Current Conditions');
        setText('health-explanation', healthExplanation(data));
        setText('health-period', `${titleCase(data.time_period)} Traffic Period`);
        const gauge = byId('health-meter-fill');
        if (gauge) gauge.style.setProperty('--health-value', `${Math.max(0, Math.min(100, score || 0)) * 1.8}deg`);

        // Metric cards
        setText('light-count', data.light_count ?? 0);
        setText('moderate-count', data.moderate_count ?? 0);
        setText('heavy-count', data.heavy_count ?? 0);

        // Average speed
        const avgSpeed = computeAverageSpeed(data.roads);
        setText('avg-speed', avgSpeed != null ? String(avgSpeed) : '—');

        // Hotspots and best flowing
        const hotspots = data.hotspots || data.most_congested || [];
        const best = data.best_flowing || [];
        const bestAreHeavy = best.length > 0 && best.every(road => trafficLevel(road.traffic_level) === 'Heavy');
        setText('best-flow-title', bestAreHeavy ? 'Best Available Flow' : 'Best Flowing Roads');
        renderRoadList('hotspot-list', hotspots, 'hotspot');
        renderRoadList('best-flow-list', best, 'best');

        // Source badges on card heads
        const srcBadgeText = mode === 'Real-Time' ? 'HERE' : mode === 'Mixed' ? 'MIXED' : mode === 'Unknown' ? 'UNKNOWN' : 'INFERRED';
        ['hotspot-source-badge', 'best-flow-source-badge', 'health-source-badge', 'coverage-source-badge'].forEach(id => {
            const sourceBadge = byId(id);
            if (sourceBadge) {
                sourceBadge.textContent = srcBadgeText;
                sourceBadge.className = `source-badge src-badge-${srcBadgeText.toLowerCase()}`;
            }
        });

        // Coverage bars
        renderCoverageBars(data);
        renderDistribution(data);
        renderTrafficMap(data.roads);

        // Provider status note
        setText('provider-status-note', providerStatusNote(data));

        // Subtitle
        setText('dashboard-subtitle', mode === 'Real-Time'
            ? 'Live traffic conditions powered by HERE real-time data.'
            : mode === 'Mixed'
                ? 'Traffic conditions from HERE provider and inferred model.'
                : 'Traffic conditions estimated by inferred traffic model — not live provider data.');
        setState('', 'ready');
    }

    function renderError(message) {
        byId('dashboard-available').hidden = true;
        const errRow = byId('dashboard-error-row');
        if (errRow) {
            errRow.hidden = false;
            setText('dashboard-error-msg', message || 'Traffic data temporarily unavailable.');
        }
        setText('context-snapshot', currentYangonTime());
        setText('context-live', '—');
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
        setState('Refreshing traffic intelligence…', 'loading');
        if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
        loadingPromise = Promise.allSettled([
            force ? YangonApi.trafficOverview(true) : YangonApi.trafficOverview(),
            YangonApi.weather(force),
        ]).then(([trafficResult, weatherResult]) => {
                renderWeather(weatherResult.status === 'fulfilled' ? weatherResult.value : null);
                if (trafficResult.status === 'rejected') throw trafficResult.reason;
                const data = trafficResult.value;
                if (!data || data.error) throw new Error(data?.error || 'No traffic data returned.');
                // Accept data if roads array exists OR if health score is present (inferred mode)
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
        window.addEventListener('resize', () => dashboardMap?.invalidateSize(false));
    }

    window.YangonDashboard = Object.freeze({ refresh, getTrafficColor });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true }); else bind();
}());
