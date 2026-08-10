priority(ambulance, _, 'Emergency priority - fastest route regardless of traffic.').
priority(fire_truck, _, 'Emergency priority - fastest route regardless of traffic.').
priority(police, _, 'Fastest route; authorized to use priority lanes.').

priority(bus, heavy, 'Avoid heavy traffic corridors; protect schedule reliability.').
priority(bus, moderate, 'Avoid heavy traffic corridors; protect schedule reliability.').
priority(bus, _, 'Maintain standard scheduled route.').

priority(taxi, heavy, 'Reroute around congestion; prioritize passenger comfort.').
priority(taxi, moderate, 'Reroute around congestion; prioritize passenger comfort.').
priority(taxi, _, 'Fastest route for passenger comfort.').

priority(car, heavy, 'Consider an alternate route to save time.').
priority(car, moderate, 'Minor delays possible; alternate route optional.').
priority(car, _, 'Fastest available route.').

priority(_, _, 'Balanced route based on current traffic.').

distance_note(Distance, 'Short trip - minimal fatigue expected.') :-
    Distance =< 5.

distance_note(Distance, 'Medium-length trip - plan for normal travel time.') :-
    Distance > 5, Distance =< 12.

distance_note(_, 'Long trip - consider rest stops or route breaks.').

safety_note(ambulance, _, 'Maintain siren/lights per protocol; other vehicles should yield.').
safety_note(fire_truck, _, 'Maintain siren/lights per protocol; other vehicles should yield.').
safety_note(police, _, 'Standard patrol caution applies.').

safety_note(_, heavy, 'Heavy congestion - maintain safe following distance.').
safety_note(_, moderate, 'Moderate traffic - stay alert for sudden stops.').
safety_note(_, _, 'Traffic conditions are favorable for normal driving.').

recommend(Vehicle, Traffic, Distance, Time, Report) :-
    priority(Vehicle, Traffic, Priority),
    distance_note(Distance, DistanceNote),
    safety_note(Vehicle, Traffic, SafetyNote),
    format(
        atom(Report),
        'Route Assessment~n~nVehicle: ~w~nTraffic Condition: ~w~nDistance: ~w km~nEstimated Time: ~w~n~n- Priority Action~n~w~n~n- Distance Insight~n~w~n~n- Safety Note~n~w',
        [Vehicle, Traffic, Distance, Time,
         Priority, DistanceNote, SafetyNote]
    ).