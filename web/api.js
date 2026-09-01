(function () {
    'use strict';
    let weatherPromise = null;
    let weatherSnapshot = null;

    function desktopBackend() {
        return window.pywebview && window.pywebview.api ? window.pywebview.api : null;
    }

    async function request(path, options = {}) {
        const response = await fetch(`/api/${path}`, {
            ...options,
            headers: { 'Accept': 'application/json', ...(options.headers || {}) }
        });
        let payload;
        try { payload = await response.json(); }
        catch (_) { throw new Error(`The server returned an invalid response (${response.status}).`); }
        // Route validation responses are returned to the existing UI because
        // it already renders their structured error_details contract.
        if (!response.ok && payload && payload.error) return payload;
        if (!response.ok) throw new Error(payload?.detail || `Request failed (${response.status}).`);
        return payload;
    }

    function weather(refresh = false) {
        if (!refresh && weatherSnapshot) return Promise.resolve(weatherSnapshot);
        if (weatherPromise) return weatherPromise;
        const desktop = desktopBackend();
        const operation = desktop?.get_weather(refresh) || request(`weather?force=${refresh ? 'true' : 'false'}`);
        weatherPromise = Promise.resolve(operation)
            .then(data => { weatherSnapshot = data; return data; })
            .finally(() => { weatherPromise = null; });
        return weatherPromise;
    }

    window.YangonApi = Object.freeze({
        mode: () => desktopBackend() ? 'desktop' : 'http',
        locations: () => desktopBackend()?.get_locations() || request('locations'),
        vehicles: () => desktopBackend()?.get_vehicles() || request('vehicles'),
        graph: () => desktopBackend()?.get_graph_data() || request('graph'),
        trafficOverview: (refresh = false) => desktopBackend()?.get_traffic_overview(refresh) || request(`traffic?refresh=${refresh ? 'true' : 'false'}`),
        trafficHotspots: (limit = 8) => desktopBackend()?.get_congestion_hotspots(limit) || request(`traffic/hotspots?limit=${encodeURIComponent(limit)}`),
        bestFlowingRoads: (limit = 8) => desktopBackend()?.get_best_flowing_roads(limit) || request(`traffic/best-flowing?limit=${encodeURIComponent(limit)}`),
        roadTraffic: roadId => desktopBackend()?.get_road_traffic(roadId) || request(`traffic/${encodeURIComponent(roadId)}`),
        weather,
        findRoute: ({ vehicle, start, destination, conditions }) => {
            const desktop = desktopBackend();
            if (desktop) return desktop.find_route(vehicle, start, destination, conditions || {});
            return request('route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vehicle, start, destination, conditions: conditions || {} })
            });
        }
    });
}());
