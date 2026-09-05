import sys

with open('web/app.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_html = '''    <section class="analysis-section">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <div class="route-agent-avatar" aria-hidden="true" style="width: 24px; height: 24px; min-width: 24px; margin: 0;"><i></i><i></i><span></span></div>
            <h3 style="margin: 0;">YGN Assistant Recommendation</h3>
        </div>
        <div id="analysis-assistant-rec" style="background: var(--surface-soft); padding: 12px; border-radius: 8px; border: 1px solid var(--border-soft); color: var(--text-secondary);">
            Find a route to see the assistant's recommendation.
        </div>
    </section>'''

new_html = '''    <section class="analysis-section" style="margin-top: 24px; margin-bottom: 24px;">
        <div id="analysis-assistant-rec">
            <div class="assistant-card" style="padding: 24px; border: 1px solid var(--border-soft); border-radius: 12px;">Find a route to see the assistant's recommendation.</div>
        </div>
    </section>'''

content = content.replace(old_html, new_html)

with open('web/app.html', 'w', encoding='utf-8') as f:
    f.write(content)

