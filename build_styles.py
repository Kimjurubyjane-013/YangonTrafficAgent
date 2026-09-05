import os
import re

css_content = """/* ==========================================================================
   YANGON TRAFFIC INTELLIGENCE
   Purple Smart-City Navigation System (Design Tokens)
   ========================================================================== */

:root {
  /* Brand Purple Identity */
  --brand-purple: #6D28D9;
  --brand-purple-primary: #7C3AED;
  --brand-purple-bright: #8B5CF6;
  --brand-purple-light: #A78BFA;
  --brand-purple-soft: #EDE9FE;
  --brand-accent: #C084FC;

  /* Semantic Traffic Colors (Maintained) */
  --traffic-light: #2F9E68;
  --traffic-moderate: #D88918;
  --traffic-heavy: #D94B42;
  --traffic-unknown: #71808A;

  /* Light Theme Surfaces (Premium Clean) */
  --bg-page: #F8F9FC;
  --bg-surface: #FFFFFF;
  --bg-surface-elevated: #FFFFFF;
  --bg-surface-secondary: #F1F5F9;
  --bg-surface-subtle: #F8FAFC;
  --bg-surface-hover: #F8FAFC;

  /* Light Theme Text */
  --text-primary: #111827;
  --text-secondary: #64748B;
  --text-muted: #94A3B8;
  --text-inverse: #FFFFFF;

  /* Light Theme Borders */
  --border-default: #E5E7EB;
  --border-subtle: #F1F5F9;
  --border-focus: var(--brand-purple-light);

  /* Shared Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;

  /* Radii */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-full: 9999px;

  /* Shadows (Minimal, Professional) */
  --shadow-sm: 0 1px 2px 0 rgba(17, 24, 39, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(17, 24, 39, 0.05), 0 2px 4px -1px rgba(17, 24, 39, 0.03);
  --shadow-lg: 0 10px 15px -3px rgba(17, 24, 39, 0.05), 0 4px 6px -2px rgba(17, 24, 39, 0.025);
  --shadow-purple: 0 0 0 3px rgba(124, 58, 237, 0.2);
  
  --layout-max-width: 1600px;
}

body[data-theme="dark"] {
  /* Dark Theme Surfaces (Professional Command Center) */
  --bg-page: #080A0F;
  --bg-surface: #0D1117;
  --bg-surface-elevated: #131924;
  --bg-surface-secondary: #111620;
  --bg-surface-subtle: #0B0E14;
  --bg-surface-hover: #161D29;

  /* Dark Theme Text */
  --text-primary: #F8FAFC;
  --text-secondary: #94A3B8;
  --text-muted: #475569;
  --text-inverse: #F8FAFC;

  /* Dark Theme Borders */
  --border-default: rgba(148, 163, 184, 0.14);
  --border-subtle: rgba(148, 163, 184, 0.05);
  --border-focus: var(--brand-purple-bright);

  /* Dark Theme Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.6);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
  --shadow-purple: 0 0 0 3px rgba(139, 92, 246, 0.3);
}

/* ==========================================================================
   Global Reset & Base
   ========================================================================== */
*, *::before, *::after {
  box-sizing: border-box;
}
html, body {
  margin: 0;
  padding: 0;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: var(--bg-page);
  color: var(--text-primary);
  line-height: 1.5;
  transition: background-color 0.2s ease, color 0.2s ease;
  overflow-x: hidden;
}
[hidden] {
  display: none !important;
}

/* Typography */
h1, h2, h3, h4 { margin: 0; color: var(--text-primary); font-weight: 600; line-height: 1.25; }
h1 { font-size: 1.75rem; letter-spacing: -0.02em; }
h2 { font-size: 1.5rem; letter-spacing: -0.015em; }
h3 { font-size: 1.125rem; }
p { margin: 0 0 var(--space-md); color: var(--text-secondary); }
a { color: var(--brand-purple-primary); text-decoration: none; }
a:hover { text-decoration: underline; }

.eyebrow {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  color: var(--brand-purple-primary);
  margin-bottom: var(--space-xs);
}
.panel-kicker {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  color: var(--brand-purple-primary);
  margin-bottom: var(--space-sm);
}

/* ==========================================================================
   Navigation
   ========================================================================== */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-sm) max(var(--space-md), calc((100vw - var(--layout-max-width)) / 2));
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  position: sticky;
  top: 0;
  z-index: 1000;
  height: 64px;
}
.brand-lockup { display: flex; align-items: center; gap: var(--space-sm); }
.brand-mark {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--brand-purple-primary);
  display: flex; align-items: center; justify-content: center;
  color: white; font-weight: 700;
}
.brand-text strong { display: block; font-size: 1.1rem; line-height: 1.1; color: var(--text-primary); }
.brand-text span { display: block; font-size: 0.7rem; color: var(--text-muted); }

.app-nav { display: flex; align-items: center; gap: var(--space-xs); }
.nav-link {
  background: transparent; border: none; color: var(--text-secondary);
  padding: var(--space-sm) var(--space-md); border-radius: var(--radius-sm);
  font-size: 0.9rem; font-weight: 500; cursor: pointer; transition: 0.15s;
}
.nav-link:hover { background: var(--bg-surface-secondary); color: var(--text-primary); }
.nav-link.active {
  background: var(--brand-purple-soft);
  color: var(--brand-purple-primary);
}
body[data-theme="dark"] .nav-link.active {
  background: rgba(124, 58, 237, 0.15);
  color: var(--brand-purple-light);
}
.theme-toggle {
  background: transparent; border: 1px solid var(--border-default);
  color: var(--text-secondary); width: 36px; height: 36px;
  border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center;
  cursor: pointer; margin-left: var(--space-sm); transition: 0.15s;
}
.theme-toggle:hover { background: var(--bg-surface-secondary); }

/* ==========================================================================
   Shared Components (Cards, Buttons, Inputs)
   ========================================================================== */
.panel, .dashboard-card, .health-card, .traffic-stat, .analysis-summary {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  box-shadow: var(--shadow-sm);
}

label {
  display: block; font-size: 0.85rem; font-weight: 500;
  margin-bottom: var(--space-xs); margin-top: var(--space-md); color: var(--text-secondary);
}
select, input, .journey-conditions select {
  width: 100%; padding: 10px 12px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-default); background: var(--bg-surface);
  color: var(--text-primary); font-size: 0.9rem; transition: 0.15s;
}
select:focus, input:focus {
  outline: none; border-color: var(--border-focus); box-shadow: var(--shadow-purple);
}

button {
  font-family: inherit; font-size: 0.9rem; font-weight: 500;
  border-radius: var(--radius-sm); cursor: pointer; transition: 0.15s;
}
button:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary, .btn-find, .primary-action, .analysis-link {
  width: 100%; padding: 12px; background: var(--brand-purple-primary);
  color: white; border: none; font-weight: 600; margin-top: var(--space-md);
}
.btn-primary:hover, .btn-find:hover, .primary-action:hover, .analysis-link:hover {
  background: var(--brand-purple-bright);
}
.btn-secondary, .btn-reset, .btn-sim, .dashboard-refresh {
  width: 100%; padding: 10px; background: var(--bg-surface-secondary);
  color: var(--text-primary); border: 1px solid var(--border-default); margin-top: var(--space-md);
}
.btn-secondary:hover, .btn-reset:hover, .btn-sim:hover, .dashboard-refresh:hover {
  background: var(--bg-surface-hover);
}
.text-action { background: transparent; border: none; color: var(--brand-purple-primary); padding: 8px; }
.swap-route {
  width: 32px; height: 32px; margin: 4px 0 4px auto; background: var(--bg-surface-secondary);
  border: 1px solid var(--border-default); border-radius: 50%; color: var(--brand-purple-primary);
  display: flex; align-items: center; justify-content: center; padding: 0;
}
.swap-route:hover { background: var(--brand-purple-soft); }

/* ==========================================================================
   Home View
   ========================================================================== */
.home-view { max-width: 1200px; margin: 0 auto; padding: var(--space-xl) var(--space-md); }
.home-hero { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-xl); align-items: center; margin-bottom: var(--space-xl); }
.hero-copy h1 { font-size: clamp(2.5rem, 5vw, 4rem); color: var(--text-primary); margin-bottom: var(--space-md); }
.hero-copy p { font-size: 1.125rem; }
.hero-actions { display: flex; gap: var(--space-md); margin-top: var(--space-lg); margin-bottom: var(--space-lg); }
.hero-actions button { width: auto; margin-top: 0; padding: 12px 24px; }
.trust-row { display: flex; gap: var(--space-md); font-size: 0.85rem; color: var(--text-muted); }
.trust-row span::before { content: "✓ "; color: var(--brand-purple-primary); font-weight: bold; }
.agent-scene {
  background: var(--bg-surface-secondary); border-radius: var(--radius-lg);
  padding: var(--space-xl); text-align: center; border: 1px solid var(--border-default);
}
.home-features { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: var(--space-md); }
.home-features article { padding: var(--space-lg); background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--radius-md); }
.feature-icon { color: var(--brand-purple-primary); font-size: 1.5rem; margin-bottom: var(--space-sm); }
.home-features h2 { font-size: 1.25rem; margin-bottom: var(--space-xs); }

/* ==========================================================================
   Planner View
   ========================================================================== */
.planner-view {
  display: flex; flex-direction: column; min-height: calc(100vh - 64px);
}
.main {
  display: grid; grid-template-columns: 320px 1fr 340px; gap: var(--space-md);
  padding: var(--space-md) max(var(--space-md), calc((100vw - var(--layout-max-width)) / 2));
  flex: 1; align-items: start;
}
.control, .result { max-height: calc(100vh - 100px); overflow-y: auto; padding-right: 4px; }
.map-area { display: flex; flex-direction: column; height: calc(100vh - 100px); min-height: 600px; padding: var(--space-md); }

.primary-panel-title { font-size: 1.5rem; margin-bottom: var(--space-md); }
.journey-conditions {
  background: var(--bg-surface-secondary); border: 1px solid var(--border-default);
  border-radius: var(--radius-sm); padding: var(--space-md); margin-top: var(--space-md);
}
.journey-conditions summary { font-weight: 600; cursor: pointer; color: var(--text-primary); }
.condition-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-sm); margin-top: var(--space-md); }
.journey-conditions label { margin-top: 0; }

.status {
  padding: var(--space-md); background: var(--bg-surface-secondary); color: var(--text-secondary);
  border-radius: var(--radius-sm); margin-top: var(--space-md); font-size: 0.875rem;
}
body[data-phase="route-ready"] .status { background: rgba(47, 158, 104, 0.1); color: var(--traffic-light); border-left: 3px solid var(--traffic-light); }
body[data-phase="error"] .status { background: rgba(217, 75, 66, 0.1); color: var(--traffic-heavy); border-left: 3px solid var(--traffic-heavy); }

/* Result Options */
.result p { font-size: 0.875rem; color: var(--text-secondary); margin-bottom: var(--space-md); }
.route-why, .route-comparison, .route-provenance {
  background: var(--bg-surface-secondary); border-left: 3px solid var(--brand-purple-primary);
  padding: var(--space-md); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; margin-bottom: var(--space-md);
  font-size: 0.85rem; color: var(--text-secondary);
}
.route-why strong, .route-comparison strong { display: block; color: var(--text-primary); margin-bottom: var(--space-xs); font-size: 0.95rem; }

.route-option {
  background: var(--bg-surface); border: 1px solid var(--border-default);
  border-radius: var(--radius-md); padding: var(--space-md); margin-bottom: var(--space-sm);
  cursor: pointer; transition: 0.2s; position: relative;
}
.route-option:hover { border-color: var(--brand-purple-light); }
.route-option.active {
  background: var(--brand-purple-soft); border-color: var(--brand-purple-primary);
}
body[data-theme="dark"] .route-option.active { background: rgba(139, 92, 246, 0.1); }

.route-option b { display: block; font-size: 1.05rem; color: var(--text-primary); margin-bottom: var(--space-xs); }
.route-option .muted { font-size: 0.75rem; color: var(--text-muted); font-weight: normal; margin-left: 0; display: block; margin-bottom: var(--space-sm); }
.traffic-badge {
  display: inline-block; padding: 2px 8px; border-radius: var(--radius-full);
  font-size: 0.7rem; font-weight: 700; color: white; text-transform: uppercase;
}
.traffic-badge.light { background: var(--traffic-light); }
.traffic-badge.moderate { background: var(--traffic-moderate); }
.traffic-badge.heavy { background: var(--traffic-heavy); }

/* Map Area */
.map-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-sm); }
#map, #three-canvas {
  flex: 1; width: 100%; border-radius: var(--radius-sm); border: 1px solid var(--border-default);
  background: var(--bg-surface-secondary);
}
.leaflet-container { background: var(--bg-surface-secondary) !important; font-family: inherit !important; }
.leaflet-bar { border: 1px solid var(--border-default) !important; box-shadow: var(--shadow-sm) !important; }
.leaflet-bar a { background: var(--bg-surface) !important; color: var(--text-primary) !important; border-color: var(--border-default) !important; }
.leaflet-bar a:hover { background: var(--bg-surface-hover) !important; }
.legend {
  display: flex; gap: var(--space-sm); font-size: 0.75rem; color: var(--text-muted); margin-top: var(--space-md);
}
.legend span { display: flex; align-items: center; gap: 4px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }

/* Simulation Overlays */
.sim-hud {
  display: none; position: absolute; z-index: 400; top: 16px; left: 16px; width: min(400px, calc(100% - 32px));
  background: var(--bg-surface-elevated); border: 1px solid var(--border-default);
  padding: var(--space-md); border-radius: var(--radius-md); box-shadow: var(--shadow-lg);
  grid-template-columns: 1fr 1fr 1fr 1fr; gap: var(--space-sm);
}
.sim-hud.visible { display: grid; }
.sim-metric strong { display: block; font-size: 0.95rem; color: var(--text-primary); }
.sim-metric small { font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; }
.sim-metric.wide { grid-column: span 2; }
.sim-controls {
  display: none; position: absolute; z-index: 400; bottom: 16px; left: 16px; right: 16px;
  background: var(--bg-surface-elevated); border: 1px solid var(--border-default);
  padding: var(--space-sm); border-radius: var(--radius-md); box-shadow: var(--shadow-lg);
  align-items: center; gap: var(--space-sm);
}
.sim-controls.visible { display: flex; }
.sim-controls button, .sim-controls select { width: auto; margin: 0; padding: 6px 12px; min-height: 32px; }
.sim-controls [data-action="exit"] { margin-left: auto; background: var(--traffic-heavy); color: white; border: none; }

/* ==========================================================================
   Dashboard View
   ========================================================================== */
.traffic-dashboard { max-width: 1400px; margin: 0 auto; padding: var(--space-xl) var(--space-md); }
.dashboard-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-xl); }
.dashboard-refresh { width: auto; margin: 0; }
.dashboard-state { padding: var(--space-md); background: var(--bg-surface-secondary); border-radius: var(--radius-sm); margin-bottom: var(--space-md); }

.traffic-context { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: var(--space-md); margin-bottom: var(--space-xl); }
.health-card, .traffic-stat, .dashboard-card { display: flex; flex-direction: column; justify-content: center; }
.traffic-stat strong { display: block; font-size: 2rem; color: var(--text-primary); margin: var(--space-xs) 0; }
.traffic-stat small { font-size: 0.8rem; color: var(--text-muted); }
.traffic-stat.light { border-top: 4px solid var(--traffic-light); }
.traffic-stat.moderate { border-top: 4px solid var(--traffic-moderate); }
.traffic-stat.heavy { border-top: 4px solid var(--traffic-heavy); }
.traffic-stat.neutral { border-top: 4px solid var(--brand-purple-light); }

.dashboard-lists { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-lg); }
.dashboard-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-md); }
.dashboard-card-head h2 { font-size: 1.25rem; }

/* Ranked Roads List */
.ranked-road {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-sm); border-bottom: 1px solid var(--border-subtle); font-size: 0.9rem;
}
.ranked-road:last-child { border-bottom: none; }
.road-level-indicator { width: 10px; height: 10px; border-radius: 50%; margin-right: var(--space-sm); display: inline-block; }
.source-badge, .road-src-badge {
  font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; background: var(--bg-surface-secondary); color: var(--text-secondary); text-transform: uppercase;
}

/* Coverage Bars */
.coverage-item { margin-bottom: var(--space-sm); }
.coverage-label { display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px; }
.coverage-bar-track { height: 6px; background: var(--bg-surface-secondary); border-radius: 3px; overflow: hidden; }
.coverage-bar-fill { height: 100%; background: var(--brand-purple-primary); }

/* ==========================================================================
   Analysis View
   ========================================================================== */
.analysis-view { max-width: 1000px; margin: 0 auto; padding: var(--space-xl) var(--space-md); }
.analysis-page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-lg); }
.analysis-summary-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-md); border-bottom: 1px solid var(--border-default); padding-bottom: var(--space-md); }
.analysis-traffic { background: var(--bg-surface-secondary); padding: 4px 12px; border-radius: var(--radius-full); font-size: 0.85rem; font-weight: 600; }
.analysis-facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--space-md); margin-bottom: var(--space-lg); }
.analysis-facts div { text-align: center; }
.analysis-facts span { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: var(--space-xs); }
.analysis-facts strong { font-size: 1.5rem; color: var(--text-primary); }
.analysis-section { margin-bottom: var(--space-lg); }
.analysis-section p { margin-top: var(--space-xs); color: var(--text-secondary); line-height: 1.6; }
.ai-panel { margin-top: var(--space-xl); border-top: 2px solid var(--brand-purple-primary); }

/* ==========================================================================
   Responsive
   ========================================================================== */
@media (max-width: 1100px) {
  .main { grid-template-columns: 320px 1fr; }
  .result { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: var(--space-md); }
  .dashboard-lists { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .home-hero { grid-template-columns: 1fr; }
  .main { display: flex; flex-direction: column; padding: var(--space-sm); }
  .panel { width: 100%; padding: var(--space-md); }
  .map-area { order: 2; height: 50vh; min-height: 400px; }
  .result { order: 3; }
  .app-header { padding: var(--space-sm) var(--space-md); }
  .brand-text span { display: none; }
}
"""

with open('web/styles.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

print("Updated styles.css.")

# Remove <style> block from app.html
with open('web/app.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Using regex to remove <style>...</style> block
html = re.sub(r'<style>.*?</style>\s*', '', html, flags=re.DOTALL)
with open('web/app.html', 'w', encoding='utf-8') as f:
    f.write(html)
    
print("Cleaned up inline styles from app.html.")

