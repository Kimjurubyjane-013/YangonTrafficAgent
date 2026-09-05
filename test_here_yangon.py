import sys
import os
import requests
from dotenv import load_dotenv

sys.path.append(os.getcwd())
try:
    load_dotenv()
    from services.here_traffic_service import fetch_traffic_aware_routes
    routes = fetch_traffic_aware_routes([16.8, 96.1], [16.85, 96.15])
    print("SUCCESS")
    print(routes)
except Exception as e:
    print("ERROR", e)

