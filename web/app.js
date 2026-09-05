(function () {
    'use strict';
    function bind() {
        const homeView = document.getElementById('home-view');
        const dashboardView = document.getElementById('dashboard-view');
        const plannerView = document.getElementById('planner-view');
        const analysisView = document.getElementById('analysis-view');
        const homeNav = document.getElementById('nav-home');
        const dashboardNav = document.getElementById('nav-dashboard');
        const plannerNav = document.getElementById('nav-planner');
        const themeToggle = document.getElementById('theme-toggle');

        function showView(name) {
            const plannerVisible = name === 'planner';
            const analysisVisible = name === 'analysis';
            const homeVisible = name === 'home';
            const dashboardVisible = name === 'dashboard';
            homeView.hidden = !homeVisible;
            dashboardView.hidden = !dashboardVisible;
            plannerView.hidden = !plannerVisible;
            analysisView.hidden = !analysisVisible;
            homeNav.classList.toggle('active', homeVisible);
            dashboardNav.classList.toggle('active', dashboardVisible);
            plannerNav.classList.toggle('active', plannerVisible || analysisVisible);
            window.scrollTo({ top: 0, behavior: 'smooth' });
            if (plannerVisible) {
                window.ensureMapInitialized().finally(() => {
                    setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
                });
            }
            if (dashboardVisible) setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
        }

        function applyTheme(theme) {
            document.body.dataset.theme = theme;
            themeToggle.textContent = theme === 'dark' ? '☀' : '☾';
            themeToggle.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
            localStorage.setItem('yangon-route-theme', theme);
        }

        applyTheme(localStorage.getItem('yangon-route-theme') || 'light');
        homeNav.addEventListener('click', () => showView('home'));
        dashboardNav.addEventListener('click', () => showView('dashboard'));
        plannerNav.addEventListener('click', () => showView('planner'));
        document.getElementById('home-plan-route').addEventListener('click', () => showView('planner'));
        document.getElementById('home-dashboard').addEventListener('click', () => showView('dashboard'));
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
        async function refreshRouteOutlook() {
            const output = document.getElementById('forecast-result');
            const route = window.getSelectedRoute?.();
            if (!route) { output.hidden = true; return; }
            const period = document.getElementById('forecast-period').value;
            output.hidden = false;
            output.textContent = 'Updating Traffic Outlook...';
            try {
                const data = await YangonApi.routeTrafficOutlook(route, period);
                if (!data || typeof data !== 'object') throw new Error('Traffic Outlook returned an invalid response.');
                if (data.error) throw new Error(data.error_details?.message || (typeof data.error === 'string' ? data.error : 'Traffic Outlook is temporarily unavailable.'));
                const traffic = YangonTrafficColors.normalize(data.traffic);
                const travelTime = Number(data.estimated_eta);
                const expectedDelay = Number(data.expected_delay);
                if (!traffic || !Number.isFinite(travelTime) || !Number.isFinite(expectedDelay)) {
                    throw new Error('Traffic Outlook returned incomplete route information.');
                }
                output.replaceChildren();

                const formatFn = typeof window.formatRouteDuration === 'function'
                    ? window.formatRouteDuration
                    : (m) => `${Math.round(m)} min`;
                const metrics = [
                    ['Expected Traffic', String(traffic)],
                    ['Travel Time', String(formatFn(travelTime))]
                ];
                metrics.forEach(([label, value], index) => {
                    const item = document.createElement('span');
                    if (index === 0) {
                        item.dataset.level = traffic;
                        item.style.setProperty('--route-traffic-color', YangonTrafficColors.css(traffic));
                    }
                    const heading = document.createElement('small'); heading.textContent = String(label);
                    const detail = document.createElement('strong'); detail.textContent = String(value);
                    item.append(heading, detail); output.appendChild(item);
                });

                if (period !== 'now' && typeof data.reason === 'string' && data.reason.trim()) {
                    const reasonBox = document.createElement('span');
                    reasonBox.className = 'reason-box';
                    const rHeading = document.createElement('small'); rHeading.textContent = 'Reason';
                    const rDetail = document.createElement('strong'); rDetail.style.fontWeight = 'normal'; rDetail.textContent = String(data.reason).trim();
                    reasonBox.append(rHeading, rDetail);
                    output.appendChild(reasonBox);
                }
            } catch (error) { output.textContent = typeof error?.message === 'string' ? error.message : 'Traffic Outlook is temporarily unavailable.'; }
        }
        document.getElementById('forecast-period').addEventListener('change', refreshRouteOutlook);
        window.refreshRouteOutlook = refreshRouteOutlook;
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
            closureField.hidden = !['closure', 'accident'].includes(mode);
            document.getElementById('scenario-road-label').textContent = mode === 'closure' ? 'Closed Road Name' : 'Affected Road Name';
            if (!['closure', 'accident'].includes(mode)) document.getElementById('closed-road').value = '';
            document.getElementById('departure-band').value = mode === 'peak' ? 'peak' : '';
        });
        YangonAppState.subscribe(({ phase }) => {
            const busy = phase === YangonAppState.phases.LOADING || phase === YangonAppState.phases.SIMULATING || phase === YangonAppState.phases.PAUSED;
            ['find-btn','start','destination','vehicle','swap-route','scenario-mode','closed-road'].forEach(id => { document.getElementById(id).disabled = busy; });
            document.body.dataset.phase = phase;
            document.getElementById('find-btn').setAttribute('aria-busy', String(phase === YangonAppState.phases.LOADING));
        });
        window.showYangonView = showView;
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once:true });
    else bind();
}());
