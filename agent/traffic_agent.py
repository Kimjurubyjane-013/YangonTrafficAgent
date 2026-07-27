class TrafficAgent:

    def __init__(self):
        self.name = "Yangon Traffic AI Agent"


    def analyze_request(self, vehicle, start, destination):

        if vehicle == "Car":
            priority = "fastest route"

        elif vehicle == "Bus":
            priority = "avoid heavy traffic"

        elif vehicle == "Motorbike":
            priority = "shortest route"

        else:
            priority = "balanced route"


        return {
            "vehicle": vehicle,
            "start": start,
            "destination": destination,
            "priority": priority
        }


    def explain_result(self, route, distance, time):

        return f"""
AI Recommendation:

Route:
{' → '.join(route)}

Distance:
{distance} km

Estimated Time:
{time} minutes

Reason:
This route is selected based on traffic optimization.
"""