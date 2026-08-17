"""Application service coordinating real-road routing and decision scoring."""
from agent.real_world_agent import run_real_world_agent
from app.models import RouteRequest


class RouteService:
    def find(self, request: RouteRequest) -> dict:
        return run_real_world_agent(request.start, request.destination, request.vehicle, conditions=request.conditions)
