import re

with open('web/app.html', 'r', encoding='utf-8') as f:
    content = f.read()

bad_html = '''        document.getElementById('analysis-assistant-rec').innerHTML = 
            <div class="assistant-card">
                <div class="assistant-card-header">
                    <span class="assistant-sparkle">✨</span> 
                    <h3>YGN Assistant Recommendation</h3>
                </div>
                <div class="assistant-card-body">
                    <div class="assistant-card-visual">
                        <div class="agent-robot" aria-hidden="true" style="transform: scale(0.65); transform-origin: top center; margin-bottom: -50px;">
                            <div class="robot-antenna"><b></b></div>
                            <div class="robot-head"><i></i><i></i><span></span></div>
                            <div class="robot-body"><b>YGN</b><span></span><span></span><span></span></div>
                        </div>
                        <div class="assistant-speech-bubble">Here's my<br>recommendation!</div>
                    </div>
                    
                    <div class="assistant-card-content">
                        <div class="assistant-card-col">
                            <strong>Recommended Route</strong>
                            <p>\\</p>
                        </div>
                        <div class="assistant-card-col">
                            <strong>Reason</strong>
                            <p>\\</p>
                        </div>
                        <div class="assistant-card-col">
                            <strong>What the System Considered</strong>
                            <div class="assistant-pill-container">
                                <span class="assistant-pill">Traffic Conditions</span>
                                <span class="assistant-pill">Travel Time</span>
                                <span class="assistant-pill">Distance</span>
                                <span class="assistant-pill">Road Suitability</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        ;'''

good_html = '''        document.getElementById('analysis-assistant-rec').innerHTML = 
            <div class="assistant-card">
                <div class="assistant-card-header">
                    <span class="assistant-sparkle">✨</span> 
                    <h3>YGN Assistant Recommendation</h3>
                </div>
                <div class="assistant-card-body">
                    <div class="assistant-card-visual">
                        <div class="agent-robot" aria-hidden="true" style="transform: scale(0.65); transform-origin: top center; margin-bottom: -50px;">
                            <div class="robot-antenna"><b></b></div>
                            <div class="robot-head"><i></i><i></i><span></span></div>
                            <div class="robot-body"><b>YGN</b><span></span><span></span><span></span></div>
                        </div>
                        <div class="assistant-speech-bubble">Here's my<br>recommendation!</div>
                    </div>
                    
                    <div class="assistant-card-content">
                        <div class="assistant-card-col">
                            <strong>Recommended Route</strong>
                            <p></p>
                        </div>
                        <div class="assistant-card-col">
                            <strong>Reason</strong>
                            <p></p>
                        </div>
                        <div class="assistant-card-col">
                            <strong>What the System Considered</strong>
                            <div class="assistant-pill-container">
                                <span class="assistant-pill">Traffic Conditions</span>
                                <span class="assistant-pill">Travel Time</span>
                                <span class="assistant-pill">Distance</span>
                                <span class="assistant-pill">Road Suitability</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        ;'''

content = content.replace(bad_html, good_html)

# Let's also check if it's <p></p> because fix_html4 did something?
# Actually fix_html4 replaced <p>\</p> with something? No it failed because it couldn't find it probably. 
# Wait! In the diff it said <p></p>. 
bad_html_2 = bad_html.replace("<p>\\</p>", "<p></p>")
content = content.replace(bad_html_2, good_html)


with open('web/app.html', 'w', encoding='utf-8') as f:
    f.write(content)

