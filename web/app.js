(function () {
    'use strict';
    function bind() {
        const homeView = document.getElementById('home-view');
        const plannerView = document.getElementById('planner-view');
        const homeNav = document.getElementById('nav-home');
        const plannerNav = document.getElementById('nav-planner');
        const themeToggle = document.getElementById('theme-toggle');

        function showView(name) {
            const plannerVisible = name === 'planner';
            homeView.hidden = plannerVisible;
            plannerView.hidden = !plannerVisible;
            homeNav.classList.toggle('active', !plannerVisible);
            plannerNav.classList.toggle('active', plannerVisible);
            window.scrollTo({ top: 0, behavior: 'smooth' });
            if (plannerVisible) {
                window.ensureMapInitialized().finally(() => {
                    setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
                });
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
        plannerNav.addEventListener('click', () => showView('planner'));
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
        const evaluationToggle = document.getElementById('evaluation-toggle');
        evaluationToggle.addEventListener('click', () => {
            const dashboard = document.getElementById('evaluation-dashboard');
            dashboard.hidden = !dashboard.hidden;
            evaluationToggle.setAttribute('aria-expanded', String(!dashboard.hidden));
            evaluationToggle.textContent = dashboard.hidden ? 'View decision evaluation' : 'Hide decision evaluation';
        });
        YangonAppState.subscribe(({ phase }) => {
            const busy = phase === YangonAppState.phases.LOADING || phase === YangonAppState.phases.SIMULATING || phase === YangonAppState.phases.PAUSED;
            ['find-btn','start','destination','vehicle','swap-route','scenario-mode','departure-band','incident-level','closed-road'].forEach(id => { document.getElementById(id).disabled = busy; });
            document.body.dataset.phase = phase;
            document.getElementById('find-btn').setAttribute('aria-busy', String(phase === YangonAppState.phases.LOADING));
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once:true });
    else bind();
}());
