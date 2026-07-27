from agent.traffic_agent import TrafficAgent


agent = TrafficAgent()


request = {
    "vehicle": "Car",
    "start": "Junction Square",
    "destination": "Yangon Airport"
}


result = agent.solve(request)


print(result)