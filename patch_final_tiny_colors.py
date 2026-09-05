import re

with open('web/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    # Line 133 Light mode focus
    'border-color:#4b7d9d!important;box-shadow:0 0 0 3px rgba(20,95,145,.10)': 
    'border-color:#7C3AED!important;box-shadow:0 0 0 3px rgba(124,58,237,.28)',
    
    # Line 189 root vars
    '--accent:#17638f': '--accent:#7C3AED',
    '--accent-secondary:#287c71': '--accent-secondary:#8B5CF6',
    '--focus:rgba(23,99,143,.18)': '--focus:rgba(124,58,237,.28)',
    
    # Check if there are any remaining rgba(..,..,..) blues.
    'rgba(20,95,145,.10)': 'rgba(124,58,237,.28)',
}

for old, new in replacements.items():
    content = content.replace(old, new)
    
with open('web/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("Final tiny patches applied.")

