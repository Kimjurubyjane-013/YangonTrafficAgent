:- dynamic request_vehicle/1, request_condition/3, request_segment/5.

congestion_penalty(light, 0).
congestion_penalty(moderate, 3).
congestion_penalty(heavy, 9).

vehicle_road_penalty(bus, local, 7).
vehicle_road_penalty(fire_truck, local, 7).
vehicle_road_penalty(_, _, 0).

prohibited(bicycle, highway, bicycle_prohibited_on_highway).
prohibited(walking, highway, walking_prohibited_on_highway).
prohibited(walking, restricted, walking_prohibited_on_restricted_road).
prohibited(V, restricted, vehicle_prohibited_on_restricted_road) :- \+ memberchk(V, [ambulance,fire_truck,police]).

time_cost(peak, arterial, 4).
time_cost(_, _, 0).
weather_cost(clear, 0). weather_cost(rain, 4). weather_cost(storm, 12).
incident_cost(none, 0). incident_cost(minor, 6). incident_cost(major, 18).
preference_cost(true, -1.5). preference_cost(false, 0).

segment_rejection(_, I, one_way_restriction(I)) :- request_segment(I,_,_,_,false).
segment_rejection(V, I, Reason) :- request_segment(I,R,_,_,true), prohibited(V,R,Reason).

request_evaluation(Congestion, VehiclePenalty, TimePenalty, WeatherPenalty, IncidentPenalty, Preference, Rejections, Reasons) :-
    request_vehicle(V), request_condition(Band,Weather,Incident),
    findall(C, (request_segment(_,_,Traffic,_,_), congestion_penalty(Traffic,C)), Cs), sum_list(Cs,Congestion),
    findall(P, (request_segment(_,Road,_,_,_), vehicle_road_penalty(V,Road,P)), Ps), sum_list(Ps,VehiclePenalty),
    findall(T, (request_segment(_,Road,_,_,_), time_cost(Band,Road,T)), Ts), sum_list(Ts,TimePenalty),
    findall(F, (request_segment(_,_,_,Preferred,_), preference_cost(Preferred,F)), Fs), sum_list(Fs,Preference),
    weather_cost(Weather,WeatherPenalty), incident_cost(Incident,IncidentPenalty),
    findall(R, segment_rejection(V,_,R), Rejections),
    findall(X, explanation(X,Congestion,VehiclePenalty,TimePenalty,WeatherPenalty,IncidentPenalty,Preference), RawReasons),
    sort(RawReasons, Reasons).

explanation(congestion_penalty, C, _, _, _, _, _) :- C > 0.
explanation(vehicle_road_suitability_penalty, _, V, _, _, _, _) :- V > 0.
explanation(peak_arterial_penalty, _, _, T, _, _, _) :- T > 0.
explanation(adverse_weather_penalty, _, _, _, W, _, _) :- W > 0.
explanation(incident_avoidance_penalty, _, _, _, _, I, _) :- I > 0.
explanation(preferred_road_benefit, _, _, _, _, _, P) :- P < 0.

clear_request :-
    retractall(request_vehicle(_)), retractall(request_condition(_,_,_)), retractall(request_segment(_,_,_,_,_)).
