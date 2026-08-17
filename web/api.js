(function () {
    'use strict';
    function backend() {
        if (!window.pywebview || !window.pywebview.api) throw new Error('The application backend is not ready.');
        return window.pywebview.api;
    }
    window.YangonApi = Object.freeze({
        locations: () => backend().get_locations(),
        vehicles: () => backend().get_vehicles(),
        graph: () => backend().get_graph_data(),
        findRoute: ({ vehicle, start, destination, conditions }) => backend().find_route(vehicle, start, destination, conditions || {})
    });
}());
