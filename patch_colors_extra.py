import re

with open('web/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    # Line 118 new overrides
    '--blue:#145f91': '--blue:#7C3AED',
    '--blue-dark:#145f91': '--blue-dark:#6D28D9',
    '--teal:#26766d': '--teal:#8B5CF6',
    
    # Specific colors
    'rgba(18,101,165,.23)': 'rgba(124,58,237,0.23)',
    '#087179': '#6D28D9',
    '#eef6fb': '#EDE9FE',
    
    # Line 189 theme
    '--ink:#202124': '--ink:#111827',
    '--muted:#5f6368': '--muted:#64748B',
    '--line:#dadce0': '--line:#E5E7EB',
    '--canvas:#f8f9fa': '--canvas:#F8F9FC',
    '--blue:#1a73e8': '--blue:#7C3AED',
    '--blue-dark:#1558b0': '--blue-dark:#6D28D9',
    '--teal:#007b83': '--teal:#8B5CF6',
    
    # Line 206 dark theme
    '--ink:#e8eaed': '--ink:#F8FAFC',
    '--muted:#9aa0a6': '--muted:#94A3B8',
    '--line:#3c4043': '--line:rgba(148,163,184,0.14)',
    '--canvas:#202124': '--canvas:#080A0F',
    '--blue:#8ab4f8': '--blue:#8B5CF6',
    '--blue-dark:#aecbfa': '--blue-dark:#7C3AED',
    '--teal:#81c995': '--teal:#A855F7',
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open('web/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("styles.css extra patches applied.")

