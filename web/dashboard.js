(function () {
    'use strict';
    let loadingPromise = null, initialized = false;
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
    function renderRoadList(id, roads, kind) {
        const container = byId(id);
        if (!container) return;
        container.innerHTML = '';
        if (!roads || roads.length === 0) {
            container.innerHTML = '<div class="empty-state">No relevant data</div>';
            return;
        }

        roads.forEach((road) => {
            const row = document.createElement('div');
            row.className = 'road-row';
            
            const levelClass = trafficLevel(road.traffic_level).toLowerCase();
            const badge = `<span class="traffic-badge ${levelClass}">${road.traffic_level}</span>`;
            
            row.innerHTML = `
                <div class="road-name-group">
                    <strong>${road.road_name || road.name || road.road_id}</strong>
                </div>
                ${badge}
            `;
            container.appendChild(row);
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

        // New KPI Cards
        const overallCondition = data.overall_condition || 'Light';
        setText('overall-condition', overallCondition);
        const conditionCard = byId('overall-condition-card');
        if (conditionCard) {
            conditionCard.className = `traffic-stat ${overallCondition.toLowerCase()}`;
        }

        const supportedTownships = Number(data.supported_townships) || 0;
        const supportedSegments = Number(data.supported_segments) || 0;
        setText('township-count', supportedTownships);
        setText('segment-count', supportedSegments);
        setText('traffic-source', mode === 'Real-Time' ? 'Live Provider' : mode === 'Mixed' ? 'Mixed' : 'Inferred');

        // Hotspots and best flowing
        const hotspots = data.hotspots || data.most_congested || [];
        const best = data.best_flowing || [];
        const bestAreHeavy = best.length > 0 && best.every(road => trafficLevel(road.traffic_level) === 'Heavy');
        setText('best-flow-title', bestAreHeavy ? 'Best Available Flow' : 'Best Flowing Roads');
        renderRoadList('hotspot-list', hotspots, 'hotspot');
        renderRoadList('best-flow-list', best, 'best');

        // Subtitle — always reflects supported coverage, never claims citywide
        setText('dashboard-subtitle', mode === 'Real-Time'
            ? 'Current traffic conditions in supported townships — powered by HERE real-time data.'
            : mode === 'Mixed'
                ? 'Current traffic in supported townships — HERE provider and inferred model combined.'
                : 'Traffic conditions estimated by inferred model for the supported coverage area. Not live provider data.');
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
        loadingPromise = (force ? YangonApi.trafficOverview(true) : YangonApi.trafficOverview())
            .then(data => {
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
    }

    window.YangonDashboard = Object.freeze({ refresh, getTrafficColor });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true }); else bind();
}());
