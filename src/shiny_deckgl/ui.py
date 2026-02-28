from functools import lru_cache
from importlib import resources as impresources
from pathlib import Path
from htmltools import HTMLDependency


@lru_cache(maxsize=1)
def _resolve_resource_dir() -> str:
    """Resolve the resources directory path once and cache the result."""
    res = impresources.files("shiny_deckgl.resources")
    # MultiplexedPath doesn't support os.fspath; resolve via a child file.
    return str(Path(str(res / "deckgl-init.js")).parent)


def head_includes() -> HTMLDependency:
    """Return an ``HTMLDependency`` that injects deck.gl, MapLibre, and local assets.

    Place as a direct child of any ``ui.page_*()`` layout.  The dependency
    is automatically de-duplicated and injected into ``<head>``::

        ui.page_fluid(head_includes(), ...)
        ui.page_navbar(head_includes(), ui.nav_panel(...), ...)

    .. warning::
       Do **not** wrap the return value in ``ui.head_content()`` — the
       ``HTMLDependency`` object already handles ``<head>`` injection.
       Wrapping it would silently drop all scripts.
    """
    res_dir = _resolve_resource_dir()
    return HTMLDependency(
        name="shiny-deckgl",
        version="0.1.0",
        source={"subdir": res_dir},
        script=[{"src": "deckgl-init.js"}],
        stylesheet=[{"href": "styles.css"}],
        head=(
            '<script src="https://cdn.jsdelivr.net/npm/deck.gl@9.1.4/dist.min.js"></script>\n'
            '<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>\n'
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@3.6.2/dist/maplibre-gl.css"/>'
        ),
    )
