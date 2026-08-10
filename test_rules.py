from services.prolog_service import get_ai_recommendation

vehicles = ['Car', 'Bus', 'Taxi', 'Ambulance', 'Fire Truck', 'Police']
traffics = ['Light', 'Moderate', 'Heavy']

for v in vehicles:
    for t in traffics:
        r = get_ai_recommendation(v, t, 10.0, '20 min')
        print(f'{v:12} {t:9} -> {r.splitlines()[0]}')