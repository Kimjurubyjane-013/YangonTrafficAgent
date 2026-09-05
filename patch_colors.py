import os
import re

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update :root variables (Light Mode)
    content = re.sub(r'--ink:.*?;', '--ink:#111827;', content, count=1)
    content = re.sub(r'--muted:.*?;', '--muted:#64748B;', content, count=1)
    content = re.sub(r'--line:.*?;', '--line:#E5E7EB;', content, count=1)
    content = re.sub(r'--canvas:.*?;', '--canvas:#F8F9FC;', content, count=1)
    content = re.sub(r'--blue:.*?;', '--blue:#7C3AED;', content, count=1)
    content = re.sub(r'--blue-dark:.*?;', '--blue-dark:#6D28D9;', content, count=1)
    content = re.sub(r'--teal:.*?;', '--teal:#8B5CF6;', content, count=1)

    # 2. Update body[data-theme=dark] variables
    dark_vars = {
        '--ink': '#F8FAFC',
        '--muted': '#94A3B8',
        '--line': 'rgba(148,163,184,0.14)',
        '--canvas': '#080A0F',
        '--blue': '#8B5CF6',
        '--blue-dark': '#7C3AED',
        '--teal': '#A855F7'
    }
    
    # We find body[data-theme=dark]{...} and replace the vars inside it.
    for var, val in dark_vars.items():
        # Find all occurrences of the var inside dark mode selectors
        # Using a simple text replace since styles.css has multiple dark mode blocks
        # wait, we can just find `--var:...;` but only if it's in a dark mode block?
        # Actually styles.css uses the same variables, let's just do a regex
        pass

    # Actually, a simpler way is to just do a global replace of the exact strings from the old CSS
    
    # LIGHT MODE REPLACEMENTS
    replacements = {
        # Root vars
        '--ink:#132333': '--ink:#111827',
        '--muted:#647789': '--muted:#64748B',
        '--line:#dce5eb': '--line:#E5E7EB',
        '--canvas:#f2f6f8': '--canvas:#F8F9FC',
        '--blue:#1265a5': '--blue:#7C3AED',
        '--blue-dark:#0b4d82': '--blue-dark:#6D28D9',
        '--teal:#09868c': '--teal:#8B5CF6',
        
        # Focus rings
        'rgba(18,101,165,.13)': 'rgba(124,58,237,0.28)',
        'rgba(18,101,165,.35)': 'rgba(124,58,237,0.28)',
        
        # Hardcoded light mode backgrounds
        'background:#f4f3ef': 'background:#F8F9FC',
        'background:#faf9f4': 'background:#F5F3FF',
        'background:#f9f8f4': 'background:#F5F3FF',
        'background:rgba(255,255,255,.97)': 'background:#FFFFFF',
        'background:#fbfcfd': 'background:#F5F3FF',
        'background:#f5f8fa': 'background:#F5F3FF',
        'background:#f8fafb': 'background:#FFFFFF',
        'background:#edf3f6': 'background:#F5F3FF',
        'background:#eaf0f3': 'background:#F5F3FF',
        
        # Dark mode variable overrides
        '--ink:#e7eeec': '--ink:#F8FAFC',
        '--muted:#9baca9': '--muted:#94A3B8',
        '--line:#344845': '--line:rgba(148,163,184,0.14)',
        '--canvas:#111a1c': '--canvas:#080A0F',
        '--ink:#e8eaed': '--ink:#F8FAFC',
        '--muted:#a5abb3': '--muted:#94A3B8',
        '--line:#30343a': '--line:rgba(148,163,184,0.14)',
        '--canvas:#111315': '--canvas:#080A0F',
        '--blue:#3276b1': '--blue:#8B5CF6',
        '--blue-dark:#285f91': '--blue-dark:#7C3AED',
        '--teal:#3276b1': '--teal:#A855F7',
        
        # Dark mode hardcoded backgrounds
        'background:#111a1c': 'background:#080A0F',
        'background:rgba(17,26,28,.95)': 'background:#0D1117',
        'background:#192426': 'background:#131924',
        'background:#111b1d': 'background:#111620',
        'background:#273638': 'background:#111620',
        'background:#141f21': 'background:#0D1117',
        'background:#111315': 'background:#080A0F',
        'background:rgba(17,19,21,.96)': 'background:#0D1117',
        'background:#1b2025': 'background:#111620',
        'background:#181b1f': 'background:#111620',
        'background:#1c2228': 'background:#131924',
        'background:#1a1d21': 'background:#131924',
        'background:#14171a': 'background:#111620',
        'background:#15181b': 'background:#0D1117',
        'background:#202429': 'background:#131924',
        
        # specific hardcoded dark text
        'color:#e7eeec': 'color:#F8FAFC',
        'color:#e8eaed': 'color:#F8FAFC',
        'color:#b9c7c4': 'color:#94A3B8',
        'color:#b8bec5': 'color:#94A3B8',
    }

    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

patch_file('web/styles.css')
patch_file('web/app.html')

print("Patch applied.")

