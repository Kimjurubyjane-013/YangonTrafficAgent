from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class RouteRequest:
    vehicle: str
    start: str
    destination: str
    conditions: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        # `error` remains for backward-compatible browser handling.
        return {"error": self.message, "error_details": {"code": self.code, "message": self.message}}
