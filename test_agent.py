from agent.traffic_agent import run_traffic_agent


if __name__ == "__main__":
    result = run_traffic_agent("Junction Square", "Yangon Airport", "Car")
    print("\nROUTE:", result["route"])
    print("\nDISTANCE:", result["distance"])
    print("\nTIME:", result["time"])
    print("\nAI:", result["ai_message"])
