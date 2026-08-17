from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class WindowConfig:
    title: str = "Yangon Traffic Agent"
    page: str = str(PROJECT_ROOT / "web" / "app.html")
    width: int = 1400
    height: int = 900


WINDOW = WindowConfig()
