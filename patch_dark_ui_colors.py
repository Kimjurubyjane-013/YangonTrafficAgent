import re

with open('web/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    # Line 42 Dark Mode Header/Nav
    'border-color:#30413f': 'border-color:rgba(148,163,184,0.14)',
    'color:#eff5f3': 'color:#F8FAFC',
    'color:#93a5a2': 'color:#94A3B8',
    'color:#a9b8b5!important': 'color:#94A3B8!important',
    'background:#263734!important;color:#f1f6f4!important': 'background:rgba(139,92,246,0.10)!important;color:#8B5CF6!important',
    'border-color:#3e504d!important': 'border-color:rgba(148,163,184,0.14)!important',
    
    # Line 44 Dark Mode Panel/UI Elements
    'border-color:#314340!important': 'border-color:rgba(148,163,184,0.14)!important',
    'color:#b3c1be!important': 'color:#94A3B8!important',
    'border-color:#3b4c49!important': 'border-color:rgba(148,163,184,0.14)!important',
    'color:#c9d5d2!important': 'color:#94A3B8!important',
    'border-color:#3a4c49!important': 'border-color:rgba(148,163,184,0.14)!important',
    'background:#18342c!important;border-color:#3d8c72!important': 'background:#131924!important;border-color:#8B5CF6!important',
    'background:#20322e;color:#c9d7d3': 'background:#131924;color:#cbd0d5',
    'border-color:#344541;color:#9eaeaa': 'border-color:rgba(148,163,184,0.14);color:#94A3B8',
    'color:#b8cbc6': 'color:#a9c5de',
}

for old, new in replacements.items():
    content = content.replace(old, new)
    
with open('web/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("Remaining dark theme UI colors patched.")

