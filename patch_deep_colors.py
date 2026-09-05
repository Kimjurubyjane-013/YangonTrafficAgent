import os

with open('web/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    # 1. Light Mode Brand Text / Eyebrows / Accents
    'color:#397063': 'color:#7C3AED',           # Teal eyebrow
    'background:#63a795': 'background:#A78BFA', # Teal eyebrow line
    'color:#122d3b': 'color:#111827',           # Hero H1
    'color:#5b6a70': 'color:#64748B',           # Hero p
    'color:#315e58': 'color:#7C3AED',           # Text action
    'color:#64747a': 'color:#64748B',           # Trust row text
    'color:#358670': 'color:#7C3AED',           # Trust row checkmarks
    'border-top:1px solid #ccd8d2': 'border-top:1px solid #E5E7EB',
    'background:#F5F3FF': 'background:#F5F3FF', # Just to document
    'color:#3a8f7a': 'color:#7C3AED',           # Feature icon / agent eye
    'color:#66757a': 'color:#64748B',           # Feature p
    'color:#91c7bb': 'color:#A78BFA',           # Quick start eyebrow
    'color:#397d6b': 'color:#7C3AED',           # Panel kicker / agent name
    'color:#64776f': 'color:#64748B',           # Agent ready text
    'color:#354d48': 'color:#111827',           # AI text
    'border-top:1px solid #e4e7e2': 'border-top:1px solid #E5E7EB',
    'color:#61716f': 'color:#64748B',           # Decision details text
    'color:#45635d': 'color:#111827',           # Decision details summary
    
    # 2. Light Mode Primary Surfaces & Buttons
    'background:#173a4c': 'background:#6D28D9', # Primary blue/teal
    'border-color:#dcddd8!important': 'border-color:#E5E7EB!important',
    'background:#f7f6f1': 'background:#F5F3FF', # Avatar bg
    'border-bottom:2px solid #173a4c': 'border-bottom:2px solid #6D28D9',
    'background:#edf3ef': 'background:#F5F3FF', # AI text bg

    # 3. Light Mode Robot / Graphics
    'background:#dfeae4': 'background:#F5F3FF', # Agent scene bg
    'rgba(37,91,79,.16)': 'rgba(124,58,237,0.16)', # Orbit border
    'border:8px solid #173a4c': 'border:8px solid #6D28D9', # Head border
    'box-shadow:0 14px 0 rgba(23,58,76,.10)': 'box-shadow:0 14px 0 rgba(109,40,217,0.10)',
    'box-shadow:0 0 0 7px #d9eee8': 'box-shadow:0 0 0 7px #EDE9FE', # Eye shadow
    'border-bottom:3px solid #173a4c': 'border-bottom:3px solid #6D28D9', # Head mouth
    'background:#8bd5c7': 'background:#A78BFA', # Robot small light
    'background:#df745b': 'background:#8B5CF6', # Robot orange light -> purple bright
    'rgba(31,66,59,.12)': 'rgba(17,24,39,0.05)', # Bubble shadow
    'color:#68777b': 'color:#64748B', # Bubble span
    'border-bottom:3px dashed rgba(46,116,98,.45)': 'border-bottom:3px dashed rgba(124,58,237,0.45)', # Route sketch
    'border:4px solid #fff': 'border:4px solid #FFFFFF',
    'border:3px solid #173a4c': 'border:3px solid #6D28D9', # Route sketch dot border
    
    # 4. Dark Mode Texts & Accents
    'color:#e9efed': 'color:#F8FAFC',
    'color:#eef4f2': 'color:#F8FAFC',
    'color:#9cadaa': 'color:#94A3B8',
    'color:#e6efec': 'color:#F8FAFC',
    'color:#a0b0ad': 'color:#94A3B8',
    'color:#e8efed!important': 'color:#F8FAFC!important',
    'color:#98a9a6': 'color:#94A3B8',
    'color:#a7adb5': 'color:#94A3B8',
    'color:#6fa0ce': 'color:#8B5CF6', # Blue checkmark -> bright purple
    'color:#a5abb3': 'color:#94A3B8',
    'color:#78a8d3': 'color:#8B5CF6', # Feature icon
    'color:#82aeda': 'color:#8B5CF6', # Eyebrow
    'color:#edf0f2': 'color:#F8FAFC',
    'color:#aeb4bb': 'color:#94A3B8',

    # 5. Dark Mode Surfaces & Borders
    'background:#253b37': 'background:#111620', # Agent scene
    'border-color:#49645f': 'border-color:rgba(148,163,184,0.14)', # Orbit
    'background:#172527': 'background:#131924', # Bubble bg
    'background:#172124': 'background:#111620', # Feature article
    'border-color:#36504a': 'border-color:rgba(148,163,184,0.14)',
    'background:#21322f': 'background:#111620', # Quick start
    'background:#242a30': 'background:#131924',
    'background:#82aeda': 'background:#8B5CF6',
    'border-color:#82aeda': 'border-color:#8B5CF6',
    'background:#111620': 'background:#111620',
    'border-color:#343a41': 'border-color:rgba(148,163,184,0.14)',
    'background:#dfe3e7': 'background:#0D1117',
    'border-color:#262c32': 'border-color:#111620',
    'background:#3276b1': 'background:#8B5CF6', # Robot eye
    'box-shadow:0 0 0 7px #c7d6e4': 'box-shadow:0 0 0 7px rgba(139,92,246,0.15)',
    'background:#262c32': 'background:#111620',
    'background:#262a2f': 'background:#131924',
    'border:1px solid #343940': 'border:1px solid rgba(148,163,184,0.14)',
    'box-shadow:0 12px 28px rgba(0,0,0,.25)': 'box-shadow:0 12px 28px rgba(0,0,0,0.4)',
    'background:#20252a': 'background:#131924',
    'border-color:#708090': 'border-color:rgba(148,163,184,0.14)',
    'background:#74a7d3': 'background:#8B5CF6',
    'border-color:#9aabb9': 'border-color:rgba(148,163,184,0.14)',
    
    # 6. Navigation
    'background:var(--blue)': 'background:var(--blue)', # Already handled via variables
    
    # Missing variable fallbacks from my previous patches
    # The active nav link has a background.
    'background:rgba(18,101,165,.10)': 'background:rgba(124,58,237,0.10)', # Radial gradient bg
    'box-shadow:0 7px 16px rgba(18,101,165,.23)': 'box-shadow:0 7px 16px rgba(124,58,237,0.23)', # Brand mark shadow
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open('web/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("styles.css deeply patched for old colors.")

