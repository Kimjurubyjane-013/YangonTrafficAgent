import re

with open('web/app.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("document.getElementById('analysis-assistant-rec').innerHTML = \n            <div class=\"assistant-card\">", "document.getElementById('analysis-assistant-rec').innerHTML = \n            <div class=\"assistant-card\">")

content = content.replace("<p>\\</p>", "<p></p>", 1)
content = content.replace("<p>\\</p>", "<p></p>", 1)
content = content.replace("        ;", "        ;")

with open('web/app.html', 'w', encoding='utf-8') as f:
    f.write(content)

