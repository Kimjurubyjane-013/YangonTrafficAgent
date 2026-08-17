import unittest

from agent.traffic_agent import run_traffic_agent
from services.route_decision_engine import RouteDecisionEngine


GRAPH = {"A":{"B":2,"C":2},"B":{"A":2,"D":2},"C":{"A":2,"D":2},"D":{"B":2,"C":2},"X":{}}


class HybridDecisionTests(unittest.TestCase):
    def setUp(self):
        self.fallback = RouteDecisionEngine(prefer_prolog=False)

    def decide(self, *args, **kwargs):
        kwargs.setdefault("graph", GRAPH); kwargs.setdefault("road_metadata", {})
        kwargs.setdefault("decision_engine", self.fallback)
        return run_traffic_agent(*args, **kwargs)

    def test_light_vs_heavy_traffic(self):
        light={edge:"Light" for edge in [("A","B"),("B","D"),("A","C"),("C","D")]}
        heavy=dict(light); heavy[("A","B")]=heavy[("B","D")]="Heavy"
        a=self.decide("A","D","Car",conditions={"segment_traffic":light})
        b=self.decide("A","D","Car",conditions={"segment_traffic":heavy})
        self.assertLess(a["decision"]["congestion_penalty"], b["alternatives"][0]["decision"]["congestion_penalty"])

    def test_peak_vs_off_peak(self):
        off=self.decide("A","D","Car",conditions={"time_band":"off_peak"})
        peak=self.decide("A","D","Car",conditions={"time_band":"peak"})
        self.assertGreater(peak["decision"]["other_rule_penalties"]["time"], off["decision"]["other_rule_penalties"]["time"])

    def test_vehicle_suitability(self):
        metadata={("A","B"):{"road_class":"local"},("B","D"):{"road_class":"local"}}
        result=self.decide("A","D","Bus",road_metadata=metadata)
        self.assertEqual(result["route"],["A","C","D"])

    def test_one_way_restriction(self):
        metadata={("A","B"):{"one_way":True,"allowed_direction":False}}
        result=self.decide("A","D","Car",road_metadata=metadata)
        self.assertEqual(result["route"],["A","C","D"])

    def test_prohibited_road(self):
        metadata={("A","B"):{"road_class":"highway"},("A","C"):{"road_class":"highway"}}
        result=self.decide("A","D","Bicycle",road_metadata=metadata)
        self.assertIn("error",result)

    def test_disconnected_and_malformed(self):
        self.assertIn("error",self.decide("A","X","Car"))
        self.assertIn("error",self.decide(None,"D","Car"))

    def test_deterministic_tie_break(self):
        conditions={"segment_traffic":{e:"Light" for e in [("A","B"),("B","D"),("A","C"),("C","D")]}}
        self.assertEqual(self.decide("A","D","Car",conditions=conditions)["route"],["A","B","D"])

    def test_fallback_diagnostic_and_contract(self):
        result=self.decide("A","D","Police")
        self.assertEqual(result["decision_engine"],"python-fallback")
        self.assertIn("total_score",result["decision"])

    def test_repeated_calls_do_not_leak(self):
        blocked={("A","B"):{"one_way":True,"allowed_direction":False}}
        fixed={"segment_traffic":{e:"Light" for e in [("A","B"),("B","D"),("A","C"),("C","D")]}}
        self.assertEqual(self.decide("A","D","Car",conditions=fixed,road_metadata=blocked)["route"],["A","C","D"])
        self.assertEqual(self.decide("A","D","Car",conditions=fixed,road_metadata={})["route"],["A","B","D"])


if __name__ == "__main__":
    unittest.main()
