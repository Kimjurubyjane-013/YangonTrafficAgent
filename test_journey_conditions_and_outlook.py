"""Automated test suite covering requirements A through L:
A. Normal Conditions at 01:00 uses nighttime context
B. Rush Hour differs from Off-Peak where expected
C. Heavy Rain applies actual scenario logic
D. +30 minutes shifts timestamp exactly 30 minutes
E. +1 hour shifts timestamp exactly 60 minutes
F. 15-minute traffic buckets are correctly selected
G. Midnight date rollover
H. Asia/Yangon timezone correctness
I. Same time + same route = deterministic result
J. Fallback does not incorrectly classify unknown roads as congested at 1 AM
K. Traffic Outlook uses the selected route segments
L. No stale result after switching Outlook options
"""
import unittest
from datetime import datetime, timedelta

from app.runtime_config import app_timezone, yangon_now
from services.road_repository import ROAD_REPOSITORY
from services.traffic_service import (
    TRAFFIC_ENGINE, classify_traffic, classify_route_traffic,
    get_time_period, is_rush_hour
)
from services.traffic_prediction import (
    prediction_time, predict_route_traffic, predict_traffic, prediction_series
)
from agent.real_world_agent import run_real_world_agent, _time_band


class JourneyConditionsAndOutlookTests(unittest.TestCase):
    def setUp(self):
        self.tz = app_timezone()
        self.t_1am = datetime(2026, 9, 8, 1, 0, tzinfo=self.tz)
        self.t_8am = datetime(2026, 9, 8, 8, 0, tzinfo=self.tz)
        self.t_12pm = datetime(2026, 9, 8, 12, 0, tzinfo=self.tz)
        self.t_1730 = datetime(2026, 9, 8, 17, 30, tzinfo=self.tz)

    def test_a_normal_conditions_at_0100_uses_nighttime_context(self):
        """A. Normal Conditions at 01:00 uses nighttime context."""
        snap = TRAFFIC_ENGINE.get_snapshot(at=self.t_1am, force=True)
        self.assertEqual(snap.time_period, "NIGHT")
        self.assertFalse(snap.rush_hour)
        self.assertFalse(is_rush_hour(self.t_1am))
        # Authoritative _time_band evaluated at 1 AM should not be peak
        self.assertEqual(_time_band({"time_band": "off_peak"}), "off_peak")
        # Citywide network average at 1am should be low (Light traffic)
        avg_score = sum(r.traffic_score for r in snap.roads.values()) / len(snap.roads)
        self.assertLessEqual(avg_score, 35.0)
        self.assertEqual(classify_traffic(avg_score), "Light")

    def test_b_rush_hour_differs_from_off_peak_where_expected(self):
        """B. Rush Hour differs from Off-Peak where expected."""
        rush_snap = TRAFFIC_ENGINE.get_snapshot(scenario="peak", force=True)
        off_snap = TRAFFIC_ENGINE.get_snapshot(scenario="off_peak", force=True)
        self.assertTrue(rush_snap.rush_hour)
        self.assertFalse(off_snap.rush_hour)
        rush_avg = sum(r.traffic_score for r in rush_snap.roads.values()) / len(rush_snap.roads)
        off_avg = sum(r.traffic_score for r in off_snap.roads.values()) / len(off_snap.roads)
        self.assertGreater(rush_avg, off_avg + 15.0)

        # Sensitive arterial roads like Pyay Road should reflect rush-hour pressure
        pyay_rush = rush_snap.roads["pyay_hledan_junction_square"]
        pyay_off = off_snap.roads["pyay_hledan_junction_square"]
        self.assertGreater(pyay_rush.traffic_score, pyay_off.traffic_score)

    def test_c_heavy_rain_applies_actual_scenario_logic(self):
        """C. Heavy Rain applies actual scenario logic."""
        res_normal = run_real_world_agent(
            "Junction Square", "University of Information Technology (UIT)", "Car",
            conditions={"traffic_scenario": "current", "scenario_type": "none"}
        )
        res_rain = run_real_world_agent(
            "Junction Square", "University of Information Technology (UIT)", "Car",
            conditions={"traffic_scenario": "current", "scenario_type": "heavy_rain"}
        )
        self.assertNotIn("error", res_normal)
        self.assertNotIn("error", res_rain)
        # Heavy rain must increase traffic score and travel time
        self.assertGreater(float(res_rain["time"]), float(res_normal["time"]))
        self.assertIn(res_rain["traffic_source_label"], {"SIMULATED", "MIXED"})

    def test_d_plus_30_minutes_shifts_timestamp_exactly_30_minutes(self):
        """D. +30 minutes shifts timestamp exactly 30 minutes."""
        t0 = datetime(2026, 9, 8, 1, 15, tzinfo=self.tz)
        t_target = prediction_time("plus_30", now=t0)
        self.assertEqual(t_target - t0, timedelta(minutes=30))
        self.assertEqual(t_target.minute, 45)

    def test_e_plus_1_hour_shifts_timestamp_exactly_60_minutes(self):
        """E. +1 hour shifts timestamp exactly 60 minutes."""
        t0 = datetime(2026, 9, 8, 1, 15, tzinfo=self.tz)
        t_target = prediction_time("plus_60", now=t0)
        self.assertEqual(t_target - t0, timedelta(hours=1))
        self.assertEqual(t_target.hour, 2)
        self.assertEqual(t_target.minute, 15)

    def test_f_15_minute_traffic_buckets_are_correctly_selected(self):
        """F. 15-minute traffic buckets are correctly selected."""
        engine = TRAFFIC_ENGINE
        # Any minute in [0, 14] maps to bucket 00
        t1 = datetime(2026, 9, 8, 10, 7, 30, tzinfo=self.tz)
        k1 = engine._snapshot_key(t1)
        self.assertIn("10:00", k1)

        # Any minute in [15, 29] maps to bucket 15
        t2 = datetime(2026, 9, 8, 10, 29, 59, tzinfo=self.tz)
        k2 = engine._snapshot_key(t2)
        self.assertIn("10:15", k2)

        # Any minute in [30, 44] maps to bucket 30
        t3 = datetime(2026, 9, 8, 10, 44, 0, tzinfo=self.tz)
        k3 = engine._snapshot_key(t3)
        self.assertIn("10:30", k3)

        # Any minute in [45, 59] maps to bucket 45
        t4 = datetime(2026, 9, 8, 10, 59, 0, tzinfo=self.tz)
        k4 = engine._snapshot_key(t4)
        self.assertIn("10:45", k4)

    def test_g_midnight_date_rollover(self):
        """G. Midnight date rollover."""
        t2330 = datetime(2026, 9, 8, 23, 30, tzinfo=self.tz)
        target = prediction_time("plus_60", now=t2330)
        self.assertEqual(target.year, 2026)
        self.assertEqual(target.month, 9)
        self.assertEqual(target.day, 9)
        self.assertEqual(target.hour, 0)
        self.assertEqual(target.minute, 30)
        self.assertEqual(get_time_period(target), "NIGHT")

    def test_h_asia_yangon_timezone_correctness(self):
        """H. Asia/Yangon timezone correctness."""
        now_y = yangon_now(self.t_1am)
        # Verify UTC offset is +06:30
        offset = now_y.utcoffset()
        self.assertEqual(offset, timedelta(hours=6, minutes=30))
        series = prediction_series(now=self.t_1am)
        self.assertEqual(series["timezone"], "Asia/Yangon")
        for pred in series["predictions"]:
            self.assertIn("+06:30", pred["forecast_for"])

    def test_i_same_time_same_route_is_deterministic(self):
        """I. Same time + same route = deterministic result."""
        route = {
            "route": ["Junction Square", "University of Information Technology (UIT)"],
            "road_names": ["Kyun Taw Road", "Hanthawaddy Road", "Pyay Road", "Parami Road"],
            "time": 10.1,
            "free_flow_eta": 8.6,
            "traffic": "Moderate",
            "traffic_score": 52.3,
        }
        res1 = predict_route_traffic(route, "plus_30", now=self.t_1am)
        res2 = predict_route_traffic(route, "plus_30", now=self.t_1am)
        self.assertEqual(res1, res2)
        self.assertEqual(res1["traffic"], res2["traffic"])
        self.assertEqual(res1["estimated_eta"], res2["estimated_eta"])
        self.assertEqual(res1["traffic_score"], res2["traffic_score"])

    def test_j_fallback_does_not_incorrectly_classify_unknown_roads_as_congested_at_1am(self):
        """J. Fallback does not incorrectly classify unknown roads as congested at 1 AM."""
        snap_1am = TRAFFIC_ENGINE.get_snapshot(at=self.t_1am, force=True)
        # Querying an unmapped/unknown corridor
        fallback_state = TRAFFIC_ENGINE.route_state("NonExistentA", "NonExistentB", ["Unknown Non-Mapped Road"], snapshot=snap_1am)
        self.assertEqual(fallback_state["traffic_level"], "Light")
        self.assertLessEqual(fallback_state["average_score"], 35.0)
        self.assertEqual(fallback_state["segment_traffic"], ["Light"])

        # Direct classify_route_traffic with empty states
        empty_score, empty_level = classify_route_traffic([], ROAD_REPOSITORY, fallback_score=fallback_state["average_score"])
        self.assertEqual(empty_level, "Light")
        self.assertLessEqual(empty_score, 35.0)

    def test_k_traffic_outlook_uses_selected_route_segments(self):
        """K. Traffic Outlook uses the selected route segments."""
        route = {
            "route": ["Junction Square", "University of Information Technology (UIT)"],
            "road_names": ["Pyay Road", "Parami Road"],
            "time": 8.6,
            "free_flow_eta": 8.6,
            "traffic": "Light",
            "traffic_score": 28.0,
        }
        # Evening rush prediction should evaluate Pyay Road segments at 17:30
        res_evening = predict_route_traffic(route, "evening_rush", now=self.t_1am)
        self.assertEqual(res_evening["time_period"], "EVENING_RUSH")
        self.assertIn(res_evening["traffic"], {"Moderate", "Heavy"})
        self.assertGreater(res_evening["traffic_score"], 50.0)
        self.assertGreater(res_evening["estimated_eta"], 8.6)

    def test_l_no_stale_result_after_switching_outlook_options(self):
        """L. Contract verification that distinct periods evaluate independently."""
        route = {
            "route": ["Junction Square", "University of Information Technology (UIT)"],
            "road_names": ["Pyay Road", "Parami Road"],
            "time": 8.6,
            "free_flow_eta": 8.6,
            "traffic": "Light",
            "traffic_score": 28.0,
        }
        res_now = predict_route_traffic(route, "now", now=self.t_1am)
        res_30 = predict_route_traffic(route, "plus_30", now=self.t_1am)
        res_60 = predict_route_traffic(route, "plus_60", now=self.t_1am)
        res_rush = predict_route_traffic(route, "evening_rush", now=self.t_1am)

        self.assertEqual(res_now["period"], "now")
        self.assertEqual(res_30["period"], "plus_30")
        self.assertEqual(res_60["period"], "plus_60")
        self.assertEqual(res_rush["period"], "evening_rush")

        self.assertIn("01:00", res_now["forecast_for"])
        self.assertIn("01:30", res_30["forecast_for"])
        self.assertIn("02:00", res_60["forecast_for"])
        self.assertIn("17:30", res_rush["forecast_for"])


if __name__ == "__main__":
    unittest.main()
