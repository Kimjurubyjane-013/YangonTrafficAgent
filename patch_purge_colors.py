import re

def purge_old_colors():
    with open('web/styles.css', 'r', encoding='utf-8') as f:
        css = f.read()

    # Map all legacy teal/blue hexes to purple equivalents
    replacements = {
        '#173a4c': '#6D28D9',
        '#3a8f7a': '#8B5CF6',
        '#397063': '#6D28D9',
        '#358670': '#7C3AED',
        '#2f6f9e': '#7C3AED',
        '#4b83b5': '#8B5CF6',
        '#122d3b': '#171526',
        '#356f9a': '#8B5CF6',
        '#17638f': '#7C3AED',
        '#287c71': '#8B5CF6',
        
        # Navigation/UI specifics missed
        '#e4ebe9': '#EDE9FE', # nav active bg light
        '#576a75': '#8A8497', # nav text
        '#ebeae5': '#F3F0FA', # nav hover bg
        '#d9dad5': '#E6E1EF', # theme toggle border
        
        # Journey conditions / eval summary
        '#d8e0de': '#E6E1EF',
        '#284a45': '#171526',
        '#81908d': '#8A8497',
        '#cdd8d5': '#E6E1EF',
        '#183238': '#171526',
        '#71807d': '#8A8497',
        '#bfd0cb': '#D8CCEE',
        '#f5f8f6': '#F6F3FC',
        '#315d54': '#6D28D9',
        '#d9e2df': '#E6E1EF',
        '#788783': '#8A8497',
        '#5f706c': '#8A8497',
        '#e0e6e3': '#E6E1EF',
        '#263f3a': '#171526',
        '#687773': '#8A8497',
    }
    
    for old, new in replacements.items():
        # Case insensitive replace for hexes just in case
        css = re.sub(old, new, css, flags=re.IGNORECASE)

    with open('web/styles.css', 'w', encoding='utf-8') as f:
        f.write(css)
        
    with open('web/app.html', 'r', encoding='utf-8') as f:
        html = f.read()

    for old, new in replacements.items():
        html = re.sub(old, new, html, flags=re.IGNORECASE)
        
    with open('web/app.html', 'w', encoding='utf-8') as f:
        f.write(html)
        
purge_old_colors()
print("Purged old brand colors completely.")

