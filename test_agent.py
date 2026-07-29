from agent.traffic_agent import run_traffic_agent


result = run_traffic_agent(
    "Junction Square",
    "Yangon Airport",
    "Car"
)


print("\nROUTE:")
print(result["route"])


print("\nDISTANCE:")
print(result["distance"])


print("\nTIME:")
print(result["time"])


print("\nAI:")
print(result["ai_message"])