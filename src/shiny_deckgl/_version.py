__version__ = "1.15.3"


def python_version() -> str:
    """Return the running Python version as ``'major.minor.micro'``."""
    import sys

    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def shiny_version() -> str:
    """Return the installed Shiny for Python version, or ``'unknown'``.

    Prefers the imported module's ``__version__``: a mixed pip/conda upgrade
    can leave an orphaned older ``shiny-*.dist-info`` that
    ``importlib.metadata`` reports instead of the code actually running.
    """
    try:
        import shiny

        ver = getattr(shiny, "__version__", None)
        if isinstance(ver, str) and ver:
            return ver
    except ImportError:
        pass
    try:
        from importlib.metadata import version, PackageNotFoundError

        return version("shiny")
    except (PackageNotFoundError, ImportError):
        return "unknown"
