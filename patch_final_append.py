import re

append_css = """
/* --- FINAL VISUAL IDENTITY OVERRIDES --- */

:root {
  --page-bg: #F8F7FC;
  --surface: #FFFFFF;
  --surface-soft: #F6F3FC;
  --text-primary: #171526;
  --text-secondary: #625D73;
  --text-muted: #8A8497;
  --border: #E5DFF0;
  --border-purple: #D8CCEE;
  --brand-700: #6D28D9;
  --brand-600: #7C3AED;
  --brand-500: #8B5CF6;
  --canvas: #F8F7FC;
  --ink: #171526;
  --muted: #8A8497;
  --line: #E5DFF0;
  --accent: #6D28D9;
  --accent-secondary: #7C3AED;
}

body {
  background: var(--page-bg) !important;
  color: var(--text-primary) !important;
}

.brand-mark {
  background: linear-gradient(145deg, #7C3AED, #6D28D9) !important;
  border: 1px solid rgba(109,40,217,0.20) !important;
  box-shadow: 0 6px 18px rgba(109,40,217,0.16) !important;
}

.app-nav .nav-link.active,
.app-nav button.active {
  background: #EDE9FE !important;
  color: #6D28D9 !important;
  border: 1px solid #DDD6FE !important;
}

.app-nav .nav-link:hover,
.app-nav button:hover {
  color: #8B5CF6 !important;
}

.eyebrow, .panel-kicker, .agent-name { color: #6D28D9 !important; }
.eyebrow > span { background: #8B5CF6 !important; }
.primary-action {
  background: linear-gradient(135deg, #6D28D9, #7C3AED) !important;
  color: #FFFFFF !important;
  box-shadow: 0 10px 32px rgba(109, 40, 217, 0.13) !important;
}
.text-action { color: #7C3AED !important; }
.trust-row span::before, .feature-icon { color: #6D28D9 !important; }

.robot-body, .robot-head {
  border-color: #6D28D9 !important;
}
.robot-body { background: #6D28D9 !important; }
.robot-head { background: #F7F3FF !important; box-shadow: 0 14px 0 rgba(109,40,217,0.10) !important; }
.robot-head i { background: #8B5CF6 !important; box-shadow: 0 0 0 7px #EDE9FE !important; }
.robot-body span:first-of-type { background: #A78BFA !important; }
.robot-body span:nth-of-type(2) { background: #7C3AED !important; }
.agent-orbit { border-color: rgba(124,58,237,0.22) !important; }
.agent-scene { background: #F1ECFF !important; }

.home-features article { background: #FFFFFF !important; border-color: #D8CCEE !important; box-shadow: 0 8px 28px rgba(76, 29, 149, 0.07) !important; }

.badge-inferred, .badge, .status-badge, .evaluation-notice.inferred {
  background: #F3E8FF !important;
  color: #6D28D9 !important;
  border: 1px solid #C4B5FD !important;
}

.btn-find { background: linear-gradient(135deg, #6D28D9, #7C3AED) !important; color: #FFFFFF !important; }
.btn-sim { background: #7C3AED !important; color: #FFFFFF !important; }
.btn-reset { background: #F6F3FC !important; color: #171526 !important; border: 1px solid #E5DFF0 !important; }
.swap-route, .dashboard-retry { color: #7C3AED !important; }
.swap-route:hover { background: #EDE9FE !important; }

body[data-theme=dark] {
  --page-bg: #090A12;
  --surface: #11131D;
  --surface-soft: #151827;
  --surface-elevated: #191C2C;
  --text-primary: #F8F7FC;
  --text-secondary: #B9B4C8;
  --text-muted: #858095;
  --border: rgba(196,181,253,0.13);
  --border-purple: rgba(167,139,250,0.24);
  --canvas: #090A12;
  --ink: #F8F7FC;
  --line: rgba(196,181,253,0.13);
  --accent: #8B5CF6;
  --accent-secondary: #A855F7;
  background: var(--page-bg) !important;
  color: var(--text-primary) !important;
}

body[data-theme=dark] .brand-mark {
  background: linear-gradient(145deg, #241542, #6D28D9) !important;
  border: 1px solid rgba(167,139,250,0.35) !important;
  box-shadow: 0 0 22px rgba(139,92,246,0.20) !important;
}
body[data-theme=dark] .app-header { background: #0C0E16 !important; border-bottom: 1px solid var(--border) !important; }

body[data-theme=dark] .app-nav .nav-link.active,
body[data-theme=dark] .app-nav button.active {
  background: rgba(139,92,246,0.16) !important;
  color: #C4B5FD !important;
  border: 1px solid rgba(167,139,250,0.20) !important;
}
body[data-theme=dark] .app-nav .nav-link:hover,
body[data-theme=dark] .app-nav button:hover {
  color: #A855F7 !important;
}

body[data-theme=dark] .eyebrow, body[data-theme=dark] .panel-kicker, body[data-theme=dark] .agent-name { color: #A855F7 !important; }
body[data-theme=dark] .primary-action { background: linear-gradient(135deg, #7C3AED, #A855F7) !important; }
body[data-theme=dark] .trust-row span::before, body[data-theme=dark] .feature-icon { color: #8B5CF6 !important; }

body[data-theme=dark] .robot-head { background: #F4F1FA !important; border-color: #8B5CF6 !important; box-shadow: 0 14px 0 rgba(139,92,246,0.10) !important; }
body[data-theme=dark] .robot-body { background: linear-gradient(180deg, #6D28D9, #4C1D95) !important; border-color: #6D28D9 !important; }
body[data-theme=dark] .robot-head i { background: #8B5CF6 !important; box-shadow: 0 0 0 7px rgba(139,92,246,0.15) !important; }
body[data-theme=dark] .robot-body span:first-of-type { background: #A78BFA !important; }
body[data-theme=dark] .robot-antenna::after { background: #A855F7 !important; }
body[data-theme=dark] .robot-antenna b { background: #A855F7 !important; }
body[data-theme=dark] .agent-orbit { border-color: rgba(167,139,250,0.25) !important; }
body[data-theme=dark] .agent-scene {
  background: radial-gradient(circle, rgba(109,40,217,0.15), rgba(17,19,29,0.20)) !important;
  filter: drop-shadow(0 0 24px rgba(139,92,246,0.15));
}

body[data-theme=dark] .panel, 
body[data-theme=dark] .ai-panel,
body[data-theme=dark] .home-features article,
body[data-theme=dark] .quick-start,
body[data-theme=dark] .result p, 
body[data-theme=dark] .route-option,
body[data-theme=dark] .analysis-summary {
  background: #11131D !important;
  border-color: rgba(196,181,253,0.13) !important;
}

body[data-theme=dark] .badge-inferred, 
body[data-theme=dark] .badge, 
body[data-theme=dark] .status-badge, 
body[data-theme=dark] .evaluation-notice.inferred,
body[data-theme=dark] .analysis-traffic {
  background: rgba(139,92,246,0.15) !important;
  color: #C4B5FD !important;
  border: 1px solid rgba(167,139,250,0.28) !important;
}

body[data-theme=dark] .btn-find { background: linear-gradient(135deg, #7C3AED, #8B5CF6) !important; }
body[data-theme=dark] .btn-sim { background: #8B5CF6 !important; color: #FFFFFF !important; }
body[data-theme=dark] .btn-reset { background: #151827 !important; color: #B9B4C8 !important; border-color: rgba(196,181,253,0.13) !important; }
body[data-theme=dark] .swap-route, body[data-theme=dark] .dashboard-retry { color: #A855F7 !important; }
body[data-theme=dark] .swap-route:hover { background: rgba(139,92,246,0.15) !important; }

.leaflet-tile-pane img, .leaflet-tile {
    filter: saturate(0.72) brightness(1.04) contrast(0.95) hue-rotate(8deg) !important;
}
body[data-theme=dark] .leaflet-tile-pane img, body[data-theme=dark] .leaflet-tile {
    filter: invert(0.92) hue-rotate(180deg) brightness(0.42) contrast(1.15) saturate(0.72) sepia(0.12) !important;
}
#map { border: 1px solid #E5DFF0 !important; }
body[data-theme=dark] #map { border: 1px solid rgba(167,139,250,0.20) !important; }

input:focus, select:focus {
  border-color: #8B5CF6 !important;
  box-shadow: 0 0 0 3px rgba(124,58,237,0.13) !important;
}
body[data-theme=dark] input:focus, body[data-theme=dark] select:focus {
  border-color: #8B5CF6 !important;
  box-shadow: 0 0 0 3px rgba(139,92,246,0.22) !important;
}

::-webkit-scrollbar-track { background: #F5F3FF !important; }
::-webkit-scrollbar-thumb { background: #B9A6DB !important; }
body[data-theme=dark] ::-webkit-scrollbar-track { background: #11131D !important; }
body[data-theme=dark] ::-webkit-scrollbar-thumb { background: #5D4B7F !important; }

.route-option.recommended {
  border-left: 3px solid #7C3AED !important;
  background: #F3E8FF !important;
}
body[data-theme=dark] .route-option.recommended {
  border-left: 3px solid #A855F7 !important;
  background: #1B1530 !important;
}

.route-option.active {
  border-color: #8B5CF6 !important;
  box-shadow: 0 0 0 2px rgba(124,58,237,0.13) !important;
}
body[data-theme=dark] .route-option.active {
  border-color: #8B5CF6 !important;
  background: #191C2C !important;
  box-shadow: 0 0 0 2px rgba(139,92,246,0.22) !important;
}

.sim-hud { background: rgba(255,255,255,0.94) !important; border: 1px solid #E5DFF0 !important; }
body[data-theme=dark] .sim-hud { background: rgba(17,19,29,0.94) !important; border: 1px solid rgba(167,139,250,0.16) !important; color: #FFFFFF !important; }

.sim-controls button { background: #6D28D9 !important; color: #FFFFFF !important; }
.sim-controls [data-action="pause"] { background: #4C1D95 !important; }
.sim-controls [data-action="exit"] { background: #D94A45 !important; }
body[data-theme=dark] .sim-controls button { background: #8B5CF6 !important; }
body[data-theme=dark] .sim-controls [data-action="pause"] { background: #4C1D95 !important; }
body[data-theme=dark] .sim-controls [data-action="exit"] { background: #D94A45 !important; }
"""

with open('web/styles.css', 'a', encoding='utf-8') as f:
    f.write(append_css)

with open('web/app.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Also inject into the end of the <style> tag in app.html to override any inline specifics
html = html.replace('</style>', append_css + '\n</style>')

with open('web/app.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("CSS appended to styles.css and app.html.")

