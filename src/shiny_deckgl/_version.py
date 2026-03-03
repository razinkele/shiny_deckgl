__version__ = "1.3.0"


def python_version() -> str:
    """Return the running Python version as ``'major.minor.micro'``."""
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def shiny_version() -> str:
    """Return the installed Shiny for Python version, or ``'unknown'``."""
    try:
        from importlib.metadata import version
        return version("shiny")
    except Exception:
        return "unknown"
