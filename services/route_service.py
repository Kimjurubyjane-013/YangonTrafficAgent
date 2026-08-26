"""Application service coordinating real-road routing and decision scoring."""
from agent.real_world_agent import run_real_world_agent
from app.models import RouteRequest
from services.traffic_service import TRAFFIC_ENGINE


class RouteService:
    def __init__(self, traffic_engine=None):
        self.traffic_engine = traffic_engine or TRAFFIC_ENGINE

    def find(self, request: RouteRequest) -> dict:
        snapshot = self.traffic_engine.get_snapshot()
        return run_real_world_agent(
            request.start, request.destination, request.vehicle,
            conditions=request.conditions, traffic_engine=self.traffic_engine,
            traffic_snapshot=snapshot,
        )
