(function () {
    'use strict';
    function bind() {
        const homeView = document.getElementById('home-view');
        const trafficMapView = document.getElementById('traffic-map-view');
        const plannerView = document.getElementById('planner-view');
        const analysisView = document.getElementById('analysis-view');
        const homeNav = document.getElementById('nav-home');
        const trafficNav = document.getElementById('nav-traffic');
        const plannerNav = document.getElementById('nav-planner');
        const simulationNav = document.getElementById('nav-simulation');
        const themeToggle = document.getElementById('theme-toggle');

        function showView(name) {
            const plannerVisible = name === 'planner';
            const analysisVisible = name === 'analysis';
            const homeVisible = name === 'home';
            const trafficVisible = name === 'traffic';
            homeView.hidden = !homeVisible;
            trafficMapView.hidden = !trafficVisible;
            plannerView.hidden = !plannerVisible;
            analysisView.hidden = !analysisVisible;
            homeNav.classList.toggle('active', homeVisible);
            trafficNav.classList.toggle('active', trafficVisible);
            plannerNav.classList.toggle('active', plannerVisible || analysisVisible);
            simulationNav.classList.remove('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
            if (plannerVisible) {
                window.ensureMapInitialized().finally(() => {
                    setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
                });
            }
            if (homeVisible || trafficVisible) {
                window.YangonDashboard?.resizeMaps();
            }
        }

        function applyTheme(theme) {
            document.body.dataset.theme = theme;
            themeToggle.textContent = theme === 'dark' ? '☀' : '☾';
            themeToggle.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
            localStorage.setItem('yangon-route-theme', theme);
        }

        applyTheme(localStorage.getItem('yangon-route-theme') || 'light');
        homeNav.addEventListener('click', () => showView('home'));
        trafficNav.addEventListener('click', () => showView('traffic'));
        plannerNav.addEventListener('click', () => showView('planner'));
        simulationNav.addEventListener('click', () => {
            showView('planner');
            if (!document.getElementById('sim-btn').disabled) {
                simulationNav.classList.add('active');
                window.openSimulation();
                return;
            }
            document.getElementById('status').textContent = 'Find A Route Before Starting Simulation.';
            document.getElementById('find-btn').focus();
        });
        document.getElementById('home-plan-route').addEventListener('click', () => showView('planner'));
        document.getElementById('home-learn').addEventListener('click', () => document.getElementById('agent-method').scrollIntoView({ behavior: 'smooth' }));
        themeToggle.addEventListener('click', () => applyTheme(document.body.dataset.theme === 'dark' ? 'light' : 'dark'));
        document.querySelectorAll('[data-quick-destination]').forEach(button => button.addEventListener('click', () => {
            showView('planner');
            const destination = document.getElementById('destination');
            const desired = button.dataset.quickDestination;
            if ([...destination.options].some(option => option.value === desired)) destination.value = desired;
            destination.focus();
        }));

        document.getElementById('find-btn').addEventListener('click', window.findRoute);
        document.getElementById('reset-btn').addEventListener('click', window.resetAll);
        document.getElementById('sim-btn').addEventListener('click', window.openSimulation);
        document.getElementById('analysis-btn').addEventListener('click', () => showView('analysis'));
        document.getElementById('analysis-back').addEventListener('click', () => showView('planner'));
        document.getElementById('map-sim-pause').addEventListener('click', window.toggleMapSimulationPause);
        document.getElementById('map-sim-restart').addEventListener('click', window.restartMapSimulation);
        document.getElementById('map-sim-exit').addEventListener('click', () => window.exitMapSimulation());
        document.getElementById('vehicle').addEventListener('change', window.onVehicleChange);
        document.getElementById('swap-route').addEventListener('click', () => {
            const start = document.getElementById('start');
            const destination = document.getElementById('destination');
            const previous = start.value;
            start.value = destination.value;
            destination.value = previous;
            if (start.value && destination.value && start.value !== destination.value) window.findRoute();
        });
        const scenario = document.getElementById('scenario-mode');
        const closureField = document.getElementById('closure-field');
        scenario.addEventListener('change', () => {
            const mode = scenario.value;
            closureField.hidden = mode !== 'closure';
            if (mode !== 'closure') document.getElementById('closed-road').value = '';
            document.getElementById('departure-band').value = ['peak','incident','emergency'].includes(mode) ? 'peak' : '';
            document.getElementById('incident-level').value = ['incident','closure','emergency'].includes(mode) ? 'major' : 'none';
            if (mode === 'emergency') document.getElementById('vehicle').value = 'Ambulance';
        });
        YangonAppState.subscribe(({ phase }) => {
            const busy = phase === YangonAppState.phases.LOADING || phase === YangonAppState.phases.SIMULATING || phase === YangonAppState.phases.PAUSED;
            ['find-btn','start','destination','vehicle','swap-route','scenario-mode','departure-band','incident-level','closed-road'].forEach(id => { document.getElementById(id).disabled = busy; });
            document.body.dataset.phase = phase;
            document.getElementById('find-btn').setAttribute('aria-busy', String(phase === YangonAppState.phases.LOADING));
        });
        window.showYangonView = showView;
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once:true });
    else bind();
}());
