from shiny import run_app
from .app import app


def main():
    """CLI entry point for ``shiny_deckgl-demo``."""
    run_app(app)
