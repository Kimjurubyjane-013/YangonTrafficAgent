import re

with open('web/app.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    'background: #137798;': 'background: #7C3AED;',
    'color:#0078A8': 'color:#7C3AED',
    "'#1f4461'": "'#6D28D9'", # Map circle
    "'#52718f'": "'#A78BFA'", # Map route
    "'#26343d'": "'#6D28D9'", # Outline
    'rgba(8,24,38,.92)': 'rgba(13,17,23,0.92)', # Sim controls dark bg
}

for old, new in replacements.items():
    content = content.replace(old, new)
    
with open('web/app.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.html extra inline colors patched.")

