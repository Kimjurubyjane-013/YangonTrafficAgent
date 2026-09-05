import re

with open('web/app.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace HTML
old_html = '''    <section class="analysis-section">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <div class="route-agent-avatar" aria-hidden="true" style="width: 24px; height: 24px; min-width: 24px; margin: 0;"><i></i><i></i><span></span></div>
            <h3 style="margin: 0;">YGN Assistant Recommendation</h3>
        </div>
        <div id="analysis-assistant-rec" style="background: var(--surface-soft); padding: 12px; border-radius: 8px; border: 1px solid var(--border-soft); color: var(--text-secondary);">
            Find a route to see the assistant's recommendation.
        </div>
    </section>'''

new_html = '''    <section class="analysis-section">
        <div id="analysis-assistant-rec">
        </div>
    </section>'''

content = content.replace(old_html, new_html)

# Replace JS logic
js_regex = re.compile(r"const routePosition = optionIndex === 0 \? 'This route is recommended' :.*?(?=const alternatives = document\.getElementById)", re.DOTALL)

new_js = '''let shortReason = '';
        let assistantText = '';
        if (optionIndex === 0) {
            if (allOptionsData.length <= 1) {
                assistantText = "This route is recommended as the most practical available option based on road accessibility, traffic conditions, and travel time.";
                shortReason = "This route is recommended. This is the only eligible real-road route returned for the journey.";
            } else {
                const alt = allOptionsData[1];
                const thisTrafficLevel = YangonTrafficColors.normalize(opt.traffic) || 'moderate';
                const altTrafficLevel = YangonTrafficColors.normalize(alt.traffic) || 'moderate';
                const trafficLevels = { 'light': 1, 'moderate': 2, 'heavy': 3 };
                const t1 = trafficLevels[thisTrafficLevel.toLowerCase()] || 2;
                const t2 = trafficLevels[altTrafficLevel.toLowerCase()] || 2;

                if (t1 < t2) {
                    assistantText = "This route is recommended because it avoids heavier congestion while maintaining a reasonable travel time and practical route.";
                    shortReason = "Recommended for avoiding heavier congestion on alternative routes.";
                } else if (t1 === t2) {
                    if (opt.time < alt.time) {
                        assistantText = "This route is recommended because traffic conditions are similar, while this option provides a faster and more direct journey.";
                        shortReason = "Recommended as the faster and more direct option among routes with similar traffic.";
                    } else {
                        assistantText = "This route is recommended because it offers a practical balance of traffic conditions, travel time, distance, and road accessibility.";
                        shortReason = "Recommended for its practical balance of traffic conditions and travel time.";
                    }
                } else {
                    assistantText = "Although traffic is currently heavy, this route remains the most suitable available option based on accessibility, travel time, and overall route practicality.";
                    shortReason = "Recommended as the most practical overall option despite current heavy traffic.";
                }
            }
        } else {
            assistantText = "This route is a valid alternative, but it may have heavier traffic or a longer travel time than the recommended path.";
            shortReason = "Alternative route.";
        }

        document.getElementById('analysis-reason').textContent = shortReason;

        const rules = opt.rules_fired || opt.decision?.rules_fired || [];
        document.getElementById('analysis-rules').textContent = rules.length
            ? rules.join(' · ')
            : 'No route restriction or penalty rule was activated.';

        const originName = route[0] || 'Origin';
        const destinationName = route.at(-1) || 'Destination';
        const rawRoads = (opt.road_names || route.slice(1, -1)).filter(Boolean);
        const deduplicatedRoads = [];
        for (const road of rawRoads) {
            if (deduplicatedRoads.length === 0 || deduplicatedRoads[deduplicatedRoads.length - 1] !== road) {
                deduplicatedRoads.push(road);
            }
        }
        
        const finalChain = [];
        for (const segment of [originName, ...deduplicatedRoads, destinationName]) {
            if (finalChain.length === 0 || finalChain[finalChain.length - 1] !== segment) {
                finalChain.push(segment);
            }
        }
        const routeString = finalChain.join(' ? ');
        document.getElementById('analysis-roads').textContent = routeString;

        document.getElementById('analysis-assistant-rec').innerHTML = 
            <div class="assistant-card">
                <div class="assistant-card-header">
                    <span style="color: #8B5CF6; font-size: 18px;">?</span> 
                    <h3>YGN Assistant Recommendation</h3>
                </div>
                <div class="assistant-card-body">
                    <div class="assistant-card-visual">
                        <div class="agent-robot" aria-hidden="true">
                            <div class="robot-antenna"><b></b></div>
                            <div class="robot-head"><i></i><i></i><span></span></div>
                            <div class="robot-body"><b>YGN</b><span></span><span></span><span></span></div>
                        </div>
                        <div class="assistant-speech-bubble">Here's my<br>recommendation!</div>
                    </div>
                    
                    <div class="assistant-card-content">
                        <div class="assistant-card-col">
                            <strong>Recommended Route</strong>
                            <p>\</p>
                        </div>
                        <div class="assistant-card-col">
                            <strong>Reason</strong>
                            <p>\</p>
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
        ;

        '''

content = js_regex.sub(new_js, content)

with open('web/app.html', 'w', encoding='utf-8') as f:
    f.write(content)

