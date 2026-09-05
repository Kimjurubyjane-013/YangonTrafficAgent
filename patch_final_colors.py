import re

with open('web/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    # Dark mode button overrides
    'background:#2f6f9e!important': 'background:#7C3AED!important',
    'background:#356f9a!important': 'background:#8B5CF6!important',
    'background:#356f68!important': 'background:#7C3AED!important',
    
    # Active route option (dark)
    'background:#1b2732!important;border-color:#4b83b5!important;box-shadow:0 0 0 2px rgba(75,131,181,.12)': 
    'background:#131924!important;border-color:#8B5CF6!important;box-shadow:0 0 0 2px rgba(139,92,246,.15)',
    
    # Route comparison / why (dark)
    'border-color:#5e9185': 'border-color:#8B5CF6',
    'background:#222b28': 'background:#131924',
    'background:#202d2a': 'background:#131924',
    'color:#a8d5c8': 'color:#F8FAFC',
    
    # Root vars for dark theme (line 190)
    '--accent:#6298c0': '--accent:#8B5CF6',
    '--accent-secondary:#65a398': '--accent-secondary:#A855F7',
    '--focus:rgba(98,152,192,.25)': '--focus:rgba(139,92,246,.30)',
    '--accent:#79b9ad': '--accent:#8B5CF6',
    
    # Light mode route comparison (line 157)
    'border-left:3px solid #4f887c': 'border-left:3px solid #7C3AED',
    
    # Checkmark in dark mode
    'color:#6fa0ce': 'color:#8B5CF6',
    
    # Feature icon
    'color:#78a8d3': 'color:#8B5CF6',
    
    # Analysis traffic 
    'background:#20352f;color:#9bd1c0': 'background:#F5F3FF;color:#7C3AED', # Note: it's inside a dark theme block? Wait, no.
    # Ah, `body[data-theme=dark] .analysis-traffic{background:#20352f;color:#9bd1c0}` -> Should be purple highlight
    'background:#20352f;color:#9bd1c0': 'background:rgba(139,92,246,0.15);color:#8B5CF6',
    
    # Map controls links / dark overlays
    'border-color:#5a8cbb!important': 'border-color:#8B5CF6!important',
    'color:#8eb7dc!important': 'color:#A855F7!important',
    'background:#222930!important': 'background:rgba(139,92,246,0.10)!important',
    
    # Light mode extra replacements
    'background:#0B5394': 'background:#7C3AED', # Primary button in app.html? Wait, already patched app.html.
}

for old, new in replacements.items():
    content = content.replace(old, new)
    
with open('web/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("Final styles.css patches applied.")

