import logging

from api import Api
from app.config import WINDOW


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def run() -> None:
    configure_logging()
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("pywebview is required. Install dependencies with: pip install -r requirements.txt") from exc
    webview.create_window(WINDOW.title, WINDOW.page, js_api=Api(), width=WINDOW.width, height=WINDOW.height)
    webview.start()
