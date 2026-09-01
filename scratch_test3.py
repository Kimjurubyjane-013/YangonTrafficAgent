import requests
print(requests.get("https://router.project-osrm.org/route/v1/driving/96.1288,16.828;96.1319,16.816", params={"alternatives": False}).json())
print(requests.get("https://router.project-osrm.org/route/v1/driving/96.1288,16.828;96.1319,16.816", params={"alternatives": "false"}).json())
