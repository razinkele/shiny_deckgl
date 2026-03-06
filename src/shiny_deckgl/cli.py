from shiny import run_app
from .app import app


def main() -> None:
    """CLI entry point for ``shiny_deckgl-demo``."""
    run_app(app)  # type: ignore[misc]
