import re

def update_colors():
    with open('web/styles.css', 'r', encoding='utf-8') as f:
        css = f.read()

    # We previously used:
    # Light:
    # F8F9FC -> F7F5FC
    # F5F3FF -> F3F0FA
    # 111827 -> 171526
    # 64748B -> 6B6880
    # E5E7EB -> E6E1EF
    # 7C3AED (was Primary) -> 6D28D9 (new Primary) / 7C3AED (Bright)
    # 6D28D9 (was Dark) -> 5B21B6 (Hover)
    # 8B5CF6 -> 8B5CF6
    
    # Let's map exactly based on the new palette requests
    replacements = {
        # Light Theme Core
        '#F8F9FC': '#F7F5FC',
        '#F5F3FF': '#F3F0FA',
        '#111827': '#171526',
        '#64748B': '#6B6880',
        '#E5E7EB': '#E6E1EF',
        
        # Dark Theme Core
        '#080A0F': '#090A0F',
        '#0D1117': '#0F1118',
        '#111620': '#141722',
        '#131924': '#181B27',
        '#F8FAFC': '#F7F6FB',
        '#94A3B8': '#B1ACC2',
        'rgba(148,163,184,0.14)': 'rgba(167,139,250,0.16)',
        'rgba(148, 163, 184, 0.14)': 'rgba(167, 139, 250, 0.16)',
        
        # We need to selectively fix the Robot and specific elements
        # It might be easier to use regex for the root variables first
        '--ink:#171526': '--ink:#171526', # ensure idempotence if we run again
    }
    
    for old, new in replacements.items():
        css = css.replace(old, new)
        
    # We will do more specific replacements using regex or precise strings
    
    # Light Mode Button (Primary)
    css = css.replace('background:#7C3AED!important', 'background:#6D28D9!important')
    # Dark Mode Button (Primary)
    css = css.replace('background:#8B5CF6!important', 'background:#8B5CF6!important')
    
    # Active Navigation Light
    css = css.replace('background:rgba(124,58,237,0.10)!important;color:#8B5CF6!important', 'background:#EDE9FE!important;color:#6D28D9!important')
    
    # Active Navigation Dark (in body[data-theme=dark] .app-nav ...)
    css = css.replace('background:rgba(139,92,246,0.10)!important;color:#8B5CF6!important', 'background:rgba(139,92,246,0.16)!important;color:#A78BFA!important')
    
    # Focus rings
    css = css.replace('rgba(124,58,237,.28)', 'rgba(109,40,217,0.18)')
    css = css.replace('rgba(139,92,246,.30)', 'rgba(139,92,246,0.22)')
    
    # Root vars Light
    css = css.replace('--ink:#111827', '--ink:#171526')
    css = css.replace('--muted:#64748B', '--muted:#8C879D')
    css = css.replace('--line:#E5E7EB', '--line:#E6E1EF')
    css = css.replace('--canvas:#F8F9FC', '--canvas:#F7F5FC')
    css = css.replace('--blue:#7C3AED', '--blue:#6D28D9')
    css = css.replace('--blue-dark:#6D28D9', '--blue-dark:#5B21B6')
    css = css.replace('--teal:#8B5CF6', '--teal:#7C3AED')
    
    # Root vars Dark
    css = css.replace('--ink:#F8FAFC', '--ink:#F7F6FB')
    css = css.replace('--muted:#94A3B8', '--muted:#827D91')
    css = css.replace('--line:rgba(148,163,184,0.14)', '--line:rgba(167,139,250,0.16)')
    css = css.replace('--canvas:#080A0F', '--canvas:#090A0F')
    css = css.replace('--blue:#8B5CF6', '--blue:#8B5CF6')
    css = css.replace('--blue-dark:#7C3AED', '--blue-dark:#6D28D9')
    css = css.replace('--teal:#A855F7', '--teal:#A855F7')

    # Robot Light Mode fixes
    # body: #6D28D9 / #7C3AED, face: #F4F1FF, outline: #6D28D9, eyes: #7C3AED, orbit: light lavender
    # currently robot body is #6D28D9. Face is #F3F0FA (was F5F3FF). Outline is #6D28D9.
    css = css.replace('background:#F3F0FA;box-shadow:0 14px 0 rgba(109,40,217,0.10)', 'background:#F4F1FF;box-shadow:0 14px 0 rgba(109,40,217,0.10)')

    # Robot Dark Mode fixes
    # face/background shell: #171A25 / #1D2030, body: #25174A, outline: #8B5CF6, eyes: #A78BFA
    # In styles.css, it was:
    # body[data-theme=dark] .robot-head{background:#0D1117;border-color:#111620} -> needs to be #171A25 and #8B5CF6
    css = css.replace('body[data-theme=dark] .robot-head{background:#0F1118;border-color:#141722}', 'body[data-theme=dark] .robot-head{background:#171A25;border-color:#8B5CF6}')
    # body[data-theme=dark] .robot-body{background:#111620} -> needs to be #25174A
    css = css.replace('body[data-theme=dark] .robot-body{background:#141722}', 'body[data-theme=dark] .robot-body{background:#25174A}')
    # body[data-theme=dark] .robot-head i{background:#8B5CF6;box-shadow:0 0 0 7px rgba(139,92,246,0.15)} -> eyes: #A78BFA
    css = css.replace('body[data-theme=dark] .robot-head i{background:#8B5CF6;box-shadow:0 0 0 7px rgba(139,92,246,0.15)}', 'body[data-theme=dark] .robot-head i{background:#A78BFA;box-shadow:0 0 0 7px rgba(167,139,250,0.15)}')
    # body[data-theme=dark] .robot-body span{background:#8B5CF6} -> maybe #8B5CF6 is fine
    # body[data-theme=dark] .agent-scene{background:#111620} -> #1D2030
    css = css.replace('body[data-theme=dark] .agent-scene{background:#141722}', 'body[data-theme=dark] .agent-scene{background:#1D2030}')
    # body[data-theme=dark] .agent-orbit{border-color:rgba(148,163,184,0.14)} -> rgba(167,139,250,0.16)
    # already done globally
    
    # Map filters
    # Light map: filter: saturate(0.65) contrast(0.95) brightness(1.05) hue-rotate(8deg)
    # Dark map: charcoal muted map
    # We can inject this into .leaflet-tile
    
    if '.leaflet-tile { filter:' not in css:
        map_filter_css = "\n.leaflet-tile { filter: saturate(0.65) contrast(0.95) brightness(1.05) hue-rotate(8deg); }\nbody[data-theme=dark] .leaflet-tile { filter: invert(1) hue-rotate(180deg) brightness(0.7) contrast(1.15) sepia(0.2) hue-rotate(230deg) saturate(0.6); }\n"
        css += map_filter_css

    with open('web/styles.css', 'w', encoding='utf-8') as f:
        f.write(css)

    # Now app.html
    with open('web/app.html', 'r', encoding='utf-8') as f:
        html = f.read()

    html_replacements = {
        '#F8F9FC': '#F7F5FC',
        '#F5F3FF': '#F3F0FA',
        '#111827': '#171526',
        '#64748B': '#6B6880',
        '#E5E7EB': '#E6E1EF',
        
        '#080A0F': '#090A0F',
        '#0D1117': '#0F1118',
        '#111620': '#141722',
        '#131924': '#181B27',
        
        # Primary buttons
        'background: #7C3AED;': 'background: #6D28D9;',
        # Dark map overlay
        'background: #111620;outline-offset:1px': 'background: #090A0F;outline-offset:1px',
    }

    for old, new in html_replacements.items():
        html = html.replace(old, new)
        
    with open('web/app.html', 'w', encoding='utf-8') as f:
        f.write(html)

update_colors()
print("Final polish applied.")

