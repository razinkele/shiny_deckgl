from shiny import run_app
from .app import app


def default_provider():
    """Return sample data for the demo — two points near Klaipeda."""
    return {"data": [[21.12, 55.70], [21.15, 55.72]]}


def main():
    """CLI entry point for ``shiny_deckgl-demo``."""
    run_app(app(default_provider))
