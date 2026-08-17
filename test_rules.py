from services.prolog_service import get_ai_recommendation

if __name__ == "__main__":
    vehicles = ['Car', 'Bus', 'Taxi', 'Ambulance', 'Fire Truck', 'Police']
    traffics = ['Light', 'Moderate', 'Heavy']
    for vehicle in vehicles:
        for traffic in traffics:
            result = get_ai_recommendation(vehicle, traffic, 10.0, '20 min')
            print(f'{vehicle:12} {traffic:9} -> {result.splitlines()[0]}')
