from __future__ import annotations

import base64
import html as _html_mod
import json
import pathlib
from functools import lru_cache
from importlib import resources as impresources
from shiny import ui


from typing import Any

# ---------------------------------------------------------------------------
# Basemap style constants
# ---------------------------------------------------------------------------

CARTO_POSITRON = "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json"
CARTO_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json"
CARTO_VOYAGER = "https://basemaps.cartocdn.com/gl/voyager-nolabels-gl-style/style.json"
OSM_LIBERTY = "https://tiles.openfreemap.org/styles/liberty"


# ---------------------------------------------------------------------------
# Color scale utilities
# ---------------------------------------------------------------------------

# --- Built-in palettes (6 stops each) ---
PALETTE_VIRIDIS: list[list[int]] = [
    [68, 1, 84], [59, 82, 139], [33, 145, 140],
    [94, 201, 98], [253, 231, 37], [240, 249, 33],
]
PALETTE_PLASMA: list[list[int]] = [
    [13, 8, 135], [126, 3, 168], [204, 71, 120],
    [248, 149, 64], [252, 225, 56], [240, 249, 33],
]
PALETTE_OCEAN: list[list[int]] = [
    [0, 0, 40], [0, 30, 80], [0, 80, 120],
    [0, 140, 160], [60, 200, 180], [180, 240, 220],
]
PALETTE_THERMAL: list[list[int]] = [
    [4, 35, 51], [23, 82, 118], [81, 139, 116],
    [186, 177, 82], [227, 103, 55], [192, 39, 41],
]
PALETTE_CHLOROPHYLL: list[list[int]] = [
    [255, 255, 229], [194, 230, 153], [120, 198, 121],
    [49, 163, 84], [0, 104, 55], [0, 69, 41],
]


# ---------------------------------------------------------------------------
# Cached resource reader (O2 – avoid re-reading on every to_html call)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _read_bundled_resources() -> tuple[str, str]:
    """Read and cache the bundled JS and CSS files."""
    res = impresources.files("shiny_deckgl.resources")
    js_src = (res / "deckgl-init.js").read_text(encoding="utf-8")
    css_src = (res / "styles.css").read_text(encoding="utf-8")
    return js_src, css_src


def color_range(
    n: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Generate *n* evenly-spaced RGBA colours by linearly interpolating a palette.

    Parameters
    ----------
    n
        Number of output colours (default 6).
    palette
        Source palette as a list of ``[R, G, B]`` or ``[R, G, B, A]`` stops.
        Defaults to ``PALETTE_VIRIDIS``.

    Returns
    -------
    list[list[int]]
        ``n`` colours, each ``[R, G, B, 255]``.
    """
    palette = palette or PALETTE_VIRIDIS
    if n <= 0:
        return []
    if n == 1:
        c = palette[0]
        return [[c[0], c[1], c[2], c[3] if len(c) > 3 else 255]]
    stops = len(palette)
    result: list[list[int]] = []
    for i in range(n):
        t = i / (n - 1) * (stops - 1)
        lo = int(t)
        hi = min(lo + 1, stops - 1)
        frac = t - lo
        a = palette[lo]
        b = palette[hi]
        r = int(a[0] + (b[0] - a[0]) * frac)
        g = int(a[1] + (b[1] - a[1]) * frac)
        bl = int(a[2] + (b[2] - a[2]) * frac)
        result.append([r, g, bl, 255])
    return result


def color_bins(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Map each value to a colour using equal-width bins.

    Parameters
    ----------
    values
        Numeric values to classify.
    n_bins
        Number of colour bins.
    palette
        Source palette (defaults to ``PALETTE_VIRIDIS``).

    Returns
    -------
    list[list[int]]
        One ``[R, G, B, A]`` colour per input value.
    """
    if not values:
        return []
    colours = color_range(n_bins, palette)
    lo = min(values)
    hi = max(values)
    span = hi - lo if hi != lo else 1.0
    result: list[list[int]] = []
    for v in values:
        idx = int((v - lo) / span * (n_bins - 1))
        idx = max(0, min(idx, n_bins - 1))
        result.append(colours[idx])
    return result


def color_quantiles(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Map each value to a colour using quantile-based bins.

    Each bin contains approximately the same number of values.

    Parameters
    ----------
    values
        Numeric values to classify.
    n_bins
        Number of colour bins.
    palette
        Source palette (defaults to ``PALETTE_VIRIDIS``).

    Returns
    -------
    list[list[int]]
        One ``[R, G, B, A]`` colour per input value.
    """
    if not values:
        return []
    colours = color_range(n_bins, palette)
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    # Compute quantile breakpoints
    breaks = [
        sorted_vals[min(int(i / n_bins * n), n - 1)]
        for i in range(1, n_bins)
    ]

    def _bin(v: float) -> int:
        for i, br in enumerate(breaks):
            if v <= br:
                return i
        return n_bins - 1

    return [colours[_bin(v)] for v in values]


# ---------------------------------------------------------------------------
# Data serialisation helpers
# ---------------------------------------------------------------------------

def _serialise_data(data):
    """Convert pandas/geopandas objects to JSON-safe structures.

    - ``GeoDataFrame`` → GeoJSON ``FeatureCollection`` dict
    - ``DataFrame`` → list of row-dicts
    - Everything else is returned unchanged.
    """
    type_name = type(data).__name__
    if type_name == "GeoDataFrame":
        if hasattr(data, "__geo_interface__"):
            return data.__geo_interface__
        return json.loads(data.to_json())
    if type_name == "DataFrame":
        return data.to_dict(orient="records")
    return data


def encode_binary_attribute(array) -> dict:
    """Encode a numpy array as a base64 binary transport dict.

    deck.gl supports `binary attributes
    <https://deck.gl/docs/developer-guide/performance#supply-attributes-directly>`_
    for large datasets.  This helper converts a numpy array into a dict
    that the JS client decodes into a typed-array attribute.

    Parameters
    ----------
    array
        A ``numpy.ndarray`` (float32 or float64).

    Returns
    -------
    dict
        ``{"@@binary": True, "dtype": "float32", "size": <n_components>,
        "value": "<base64>"}``

    Example
    -------
    >>> import numpy as np
    >>> positions = np.array([[0.0, 51.5], [10.0, 48.8]], dtype="float32")
    >>> layer("ScatterplotLayer", "pts",
    ...       data={"length": len(positions)},
    ...       getPosition=encode_binary_attribute(positions))
    """
    import numpy as np  # noqa: local import — numpy is optional

    arr = np.ascontiguousarray(array)
    dtype_str = str(arr.dtype)
    if dtype_str not in ("float32", "float64", "uint8", "int32"):
        arr = arr.astype("float32")
        dtype_str = "float32"
    encoded = base64.b64encode(arr.tobytes()).decode("ascii")
    size = arr.shape[1] if arr.ndim > 1 else 1
    return {
        "@@binary": True,
        "dtype": dtype_str,
        "size": size,
        "value": encoded,
    }


# ---------------------------------------------------------------------------
# View helpers
# ---------------------------------------------------------------------------

def map_view(**kwargs) -> dict:
    """Create a ``MapView`` spec.

    Parameters
    ----------
    **kwargs
        Any MapView properties (``controller``, ``x``, ``y``, ``width``,
        ``height``, etc.).
    """
    return {"@@type": "MapView", **kwargs}


def orthographic_view(**kwargs) -> dict:
    """Create an ``OrthographicView`` spec (non-geo flat plane).

    Useful for non-geographic visualisations such as graph plots.
    """
    return {"@@type": "OrthographicView", **kwargs}


def first_person_view(**kwargs) -> dict:
    """Create a ``FirstPersonView`` spec (immersive 3D walkthrough)."""
    return {"@@type": "FirstPersonView", **kwargs}


CONTROL_TYPES = {
    "navigation", "scale", "fullscreen", "geolocate",
    "globe", "terrain", "attribution",
}
CONTROL_POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right"}


class MapWidget:
    """Reusable deck.gl map widget for Shiny for Python.

    Parameters
    ----------
    id
        Unique HTML element ID for this map instance.
    view_state
        Initial map view state with ``longitude``, ``latitude``, ``zoom``,
        and optionally ``pitch``, ``bearing``, ``minZoom``, ``maxZoom``.
        Defaults to the Baltic Sea (Klaipeda region).
    style
        MapLibre style URL.  Use one of the ``CARTO_*`` / ``OSM_*``
        constants or pass any MapLibre-compatible style URL.
        Defaults to ``CARTO_POSITRON``.
    tooltip
        Tooltip configuration dict with:

        - ``html`` – template string with ``{field}`` placeholders, e.g.
          ``"<b>{name}</b><br/>depth: {depth} m"``
        - ``style`` (optional) – CSS dict, e.g.
          ``{"backgroundColor": "#222", "color": "#fff"}``

        Set to ``None`` (default) to disable tooltips.
    controls
        List of initial controls to add, each a dict with ``type``,
        ``position`` (optional, default ``"top-right"``), and ``options``
        (optional). Defaults to ``[{"type": "navigation"}]``.
    """

    def __init__(
        self,
        id: str,
        view_state: dict | None = None,
        style: str = CARTO_POSITRON,
        tooltip: dict | None = None,
        mapbox_api_key: str | None = None,
        controls: list[dict] | None = None,
    ):
        self.id = id
        self.view_state = view_state or {
            "longitude": 21.1,
            "latitude": 55.7,
            "zoom": 8,
        }
        self.style = style
        self.tooltip = tooltip
        self.mapbox_api_key = mapbox_api_key
        self.controls = controls if controls is not None else [
            {"type": "navigation", "position": "top-right"},
        ]

    # -- Shiny input property helpers -----------------------------------------

    @property
    def click_input_id(self) -> str:
        """The Shiny input name for click events on this map."""
        return f"{self.id}_click"

    @property
    def hover_input_id(self) -> str:
        """The Shiny input name for hover events on this map."""
        return f"{self.id}_hover"

    @property
    def view_state_input_id(self) -> str:
        """The Shiny input name for the current viewport state."""
        return f"{self.id}_view_state"

    @property
    def drag_input_id(self) -> str:
        """The Shiny input name for drag-marker events on this map."""
        return f"{self.id}_drag"

    @property
    def map_click_input_id(self) -> str:
        """Shiny input for map-level click events (fires even on empty areas).

        Returns ``{longitude, latitude, point: {x, y}}``.
        """
        return f"{self.id}_map_click"

    @property
    def map_contextmenu_input_id(self) -> str:
        """Shiny input for right-click / context-menu events on the map."""
        return f"{self.id}_map_contextmenu"

    # -- UI -------------------------------------------------------------------

    def ui(self, width: str = "100%", height: str = "400px") -> ui.Tag:
        """Return a Shiny ``ui.Tag`` div for this map widget.

        Parameters
        ----------
        width
            CSS width (default ``"100%"``).
        height
            CSS height (default ``"400px"``).
        """
        vs = self.view_state
        attrs: dict = {
            "id": self.id,
            "class_": "deckgl-map",
            "style": f"width:{width};height:{height};",
            "data_initial_longitude": str(vs.get("longitude", 0)),
            "data_initial_latitude": str(vs.get("latitude", 0)),
            "data_initial_zoom": str(vs.get("zoom", 1)),
            "data_initial_pitch": str(vs.get("pitch", 0)),
            "data_initial_bearing": str(vs.get("bearing", 0)),
            "data_initial_min_zoom": str(vs.get("minZoom", 0)),
            "data_initial_max_zoom": str(vs.get("maxZoom", 24)),
            "data_style": self.style,
        }
        if self.tooltip is not None:
            attrs["data_tooltip"] = json.dumps(self.tooltip)
        if self.mapbox_api_key is not None:
            attrs["data_mapbox_api_key"] = self.mapbox_api_key
        if self.controls:
            attrs["data_controls"] = json.dumps(self.controls)
        return ui.div(**attrs)

    # -- Server helpers -------------------------------------------------------

    async def update(
        self,
        session,
        layers: list[dict],
        view_state: dict | None = None,
        transition_duration: int = 0,
        effects: list[dict] | None = None,
        views: list[dict] | None = None,
    ) -> None:
        """Push a new set of deck.gl layers to this map.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layers
            List of layer dicts (use the ``*_layer()`` helpers or ``layer()``).
        view_state
            Optional new view state to fly/jump to.
        transition_duration
            Milliseconds for a ``flyTo`` animation.  ``0`` (default) uses
            ``jumpTo`` for an instant move.
        effects
            Optional list of lighting/effect dicts, e.g.
            ``[{"type": "LightingEffect", "ambientLight": {...}, "pointLights": [...]}]``.
        views
            Optional list of view dicts (e.g. from ``map_view()``,
            ``orthographic_view()``).  When provided the JS client passes
            them to ``overlay.setProps({views})``.
        """
        payload: dict = {
            "id": self.id,
            "layers": layers,
        }
        if view_state is not None:
            payload["viewState"] = view_state
            if transition_duration > 0:
                payload["transitionDuration"] = transition_duration
        if effects:
            payload["effects"] = effects
        if views:
            payload["views"] = views
        await session.send_custom_message("deck_update", payload)

    async def set_layer_visibility(
        self,
        session,
        visibility: dict[str, bool],
    ) -> None:
        """Toggle layer visibility without resending data.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        visibility
            Mapping of ``{layer_id: True/False}``.
        """
        await session.send_custom_message("deck_layer_visibility", {
            "id": self.id,
            "visibility": visibility,
        })

    async def add_drag_marker(
        self,
        session,
        longitude: float | None = None,
        latitude: float | None = None,
    ) -> None:
        """Place a draggable marker on the map.

        When the user finishes dragging, the new ``[lng, lat]`` is sent to
        ``input[widget.drag_input_id]()``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        longitude
            Initial longitude (defaults to the centre of the current view).
        latitude
            Initial latitude (defaults to the centre of the current view).
        """
        await session.send_custom_message("deck_add_drag_marker", {
            "id": self.id,
            "longitude": longitude,
            "latitude": latitude,
        })

    async def set_style(
        self,
        session,
        style: str,
    ) -> None:
        """Change the basemap style dynamically.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        style
            URL of the new map style JSON (e.g. a CARTO or MapLibre style).
        """
        self.style = style
        await session.send_custom_message("deck_set_style", {
            "id": self.id,
            "style": style,
        })

    async def update_tooltip(
        self,
        session,
        tooltip: dict | None = None,
    ) -> None:
        """Update the tooltip configuration dynamically.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        tooltip
            New tooltip configuration dict (same format as the constructor's
            ``tooltip`` parameter), or ``None`` to disable tooltips.
        """
        self.tooltip = tooltip
        await session.send_custom_message("deck_update_tooltip", {
            "id": self.id,
            "tooltip": tooltip,
        })

    # -- Controls (v0.2.0) ---------------------------------------------------

    async def add_control(
        self,
        session,
        control_type: str,
        position: str = "top-right",
        *,
        options: dict | None = None,
    ) -> None:
        """Add a MapLibre control to the map.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        control_type
            One of: ``"navigation"``, ``"scale"``, ``"fullscreen"``,
            ``"geolocate"``, ``"globe"``, ``"terrain"``, ``"attribution"``.
        position
            Corner position: ``"top-left"``, ``"top-right"`` (default),
            ``"bottom-left"``, ``"bottom-right"``.
        options
            Optional dict of control-specific options, e.g.
            ``{"maxWidth": 200, "unit": "metric"}`` for ScaleControl,
            ``{"source": "terrain-dem", "exaggeration": 1.5}`` for TerrainControl.
        """
        if control_type not in CONTROL_TYPES:
            raise ValueError(
                f"Unknown control type {control_type!r}. "
                f"Valid types: {sorted(CONTROL_TYPES)}"
            )
        if position not in CONTROL_POSITIONS:
            raise ValueError(
                f"Unknown position {position!r}. "
                f"Valid positions: {sorted(CONTROL_POSITIONS)}"
            )
        await session.send_custom_message("deck_add_control", {
            "id": self.id,
            "controlType": control_type,
            "position": position,
            "options": options or {},
        })

    async def remove_control(
        self,
        session,
        control_type: str,
    ) -> None:
        """Remove a previously added MapLibre control.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        control_type
            The control type string to remove (e.g. ``"scale"``).
        """
        await session.send_custom_message("deck_remove_control", {
            "id": self.id,
            "controlType": control_type,
        })

    # -- Bounds & Navigation (v0.2.0) ----------------------------------------

    async def fit_bounds(
        self,
        session,
        bounds: list[list[float]],
        *,
        padding: int | dict[str, int] = 50,
        max_zoom: float | None = None,
        duration: int = 0,
    ) -> None:
        """Fly/jump the map to fit the given bounds.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        bounds
            ``[[sw_lng, sw_lat], [ne_lng, ne_lat]]`` in WGS 84.
            Example: ``[[10.0, 54.0], [30.0, 66.0]]`` for the Baltic Sea.
        padding
            Pixels of padding around the bounds. Can be an ``int`` (uniform)
            or a dict ``{"top": 10, "bottom": 10, "left": 10, "right": 10}``.
        max_zoom
            Maximum zoom level to use (prevents over-zooming on small areas).
        duration
            Animation duration in milliseconds. ``0`` (default) = instant.
        """
        payload: dict = {
            "id": self.id,
            "bounds": bounds,
            "padding": padding,
        }
        if max_zoom is not None:
            payload["maxZoom"] = max_zoom
        if duration > 0:
            payload["duration"] = duration
        await session.send_custom_message("deck_fit_bounds", payload)

    @staticmethod
    def compute_bounds(geojson: dict) -> list[list[float]]:
        """Compute ``[[sw_lng, sw_lat], [ne_lng, ne_lat]]`` from GeoJSON.

        Parameters
        ----------
        geojson
            A GeoJSON ``FeatureCollection``, ``Feature``, or geometry dict.

        Returns
        -------
        list[list[float]]
            ``[[min_lng, min_lat], [max_lng, max_lat]]``.
            Returns ``[[-180, -90], [180, 90]]`` if no coordinates found.
        """
        coords: list[list[float]] = []

        def _extract(geom: dict) -> None:
            gtype = geom.get("type", "")
            if gtype == "Point":
                coords.append(geom["coordinates"][:2])
            elif gtype in ("MultiPoint", "LineString"):
                coords.extend(c[:2] for c in geom["coordinates"])
            elif gtype in ("MultiLineString", "Polygon"):
                for ring in geom["coordinates"]:
                    coords.extend(c[:2] for c in ring)
            elif gtype == "MultiPolygon":
                for poly in geom["coordinates"]:
                    for ring in poly:
                        coords.extend(c[:2] for c in ring)
            elif gtype == "GeometryCollection":
                for g in geom.get("geometries", []):
                    _extract(g)

        if geojson.get("type") == "FeatureCollection":
            for f in geojson.get("features", []):
                if f.get("geometry"):
                    _extract(f["geometry"])
        elif geojson.get("type") == "Feature":
            if geojson.get("geometry"):
                _extract(geojson["geometry"])
        elif geojson.get("type"):
            _extract(geojson)

        if not coords:
            return [[-180, -90], [180, 90]]

        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return [[min(lngs), min(lats)], [max(lngs), max(lats)]]

    # -- Serialisation --------------------------------------------------------

    def to_json(self, layers: list[dict], effects: list[dict] | None = None) -> str:
        """Serialise the map spec (view state, style, layers, effects) to JSON.

        Parameters
        ----------
        layers
            List of layer dicts produced by ``layer()`` / ``*_layer()``
            helpers.
        effects
            Optional list of effects dicts.

        Returns
        -------
        str
            A JSON string with keys ``id``, ``viewState``, ``style``,
            ``tooltip``, ``layers``, and optionally ``effects``.
        """
        spec: dict = {
            "id": self.id,
            "viewState": self.view_state,
            "style": self.style,
            "layers": layers,
        }
        if self.tooltip is not None:
            spec["tooltip"] = self.tooltip
        if self.mapbox_api_key is not None:
            spec["mapboxApiKey"] = self.mapbox_api_key
        if effects:
            spec["effects"] = effects
        return json.dumps(spec, indent=2)

    @classmethod
    def from_json(cls, spec_json: str) -> tuple["MapWidget", list[dict]]:
        """Reconstruct a ``MapWidget`` and layer list from a JSON spec.

        Parameters
        ----------
        spec_json
            JSON string previously produced by ``to_json()``.

        Returns
        -------
        tuple[MapWidget, list[dict]]
            ``(widget, layers)`` ready for ``widget.update(session, layers)``.
        """
        spec = json.loads(spec_json)
        widget = cls(
            id=spec["id"],
            view_state=spec.get("viewState"),
            style=spec.get("style", CARTO_POSITRON),
            tooltip=spec.get("tooltip"),
            mapbox_api_key=spec.get("mapboxApiKey"),
        )
        layers = spec.get("layers", [])
        return widget, layers

    def to_html(
        self,
        layers: list[dict],
        path: str | pathlib.Path | None = None,
        effects: list[dict] | None = None,
        title: str = "shiny_deckgl Map",
    ) -> str:
        """Export the map as a standalone HTML file.

        The HTML file embeds CDN links for deck.gl and MapLibre, inlines
        the layer data, and can be opened in any browser without Shiny.

        Parameters
        ----------
        layers
            List of layer dicts.
        path
            Optional file path to write.  If ``None`` the HTML string is
            returned but not written to disk.
        effects
            Optional list of effects dicts.
        title
            HTML ``<title>`` content.

        Returns
        -------
        str
            The full HTML document.
        """
        js_src, css_src = _read_bundled_resources()

        vs = self.view_state
        tooltip_attr = ""
        if self.tooltip is not None:
            tooltip_json = json.dumps(self.tooltip)
            tooltip_attr = f' data-tooltip="{_html_mod.escape(tooltip_json, quote=True)}"'

        mapbox_attr = ""
        if self.mapbox_api_key:
            mapbox_attr = f' data-mapbox-api-key="{self.mapbox_api_key}"'

        layers_json = json.dumps(layers, indent=2)
        effects_json = json.dumps(effects or [], indent=2)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/deck.gl@9.1.4/dist.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@5.3.1/dist/maplibre-gl.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@5.3.1/dist/maplibre-gl.css"/>
<style>{css_src}</style>
</head>
<body>
<div id="{self.id}" class="deckgl-map"
     style="width:100%;height:100vh;"
     data-initial-longitude="{vs.get('longitude', 0)}"
     data-initial-latitude="{vs.get('latitude', 0)}"
     data-initial-zoom="{vs.get('zoom', 1)}"
     data-initial-pitch="{vs.get('pitch', 0)}"
     data-initial-bearing="{vs.get('bearing', 0)}"
     data-initial-min-zoom="{vs.get('minZoom', 0)}"
     data-initial-max-zoom="{vs.get('maxZoom', 24)}"
     data-style="{self.style}"
     {tooltip_attr}{mapbox_attr}></div>
<script>
// Shim: standalone pages have no Shiny runtime
if (typeof Shiny === 'undefined') {{
  window.Shiny = {{
    setInputValue: function() {{}},
    addCustomMessageHandler: function() {{}}
  }};
}}
</script>
<script>{js_src}</script>
<script>
(function() {{
  var initMap = window.__deckgl_initMap;
  var instances = window.__deckgl_instances;
  var buildDeckLayers = window.__deckgl_buildDeckLayers;
  var buildEffects = window.__deckgl_buildEffects;

  // Trigger init manually (no shiny:connected event in standalone mode)
  document.querySelectorAll('.deckgl-map').forEach(initMap);

  // Push layers & effects into the already-initialised overlay
  var layersData = {layers_json};
  var effectsData = {effects_json};

  Object.keys(instances).forEach(function(mapId) {{
    var inst = instances[mapId];
    var deckLayers = buildDeckLayers(
      JSON.parse(JSON.stringify(layersData)), mapId, inst.tooltipConfig
    );
    var overlayProps = {{ layers: deckLayers }};
    var effects = buildEffects(effectsData);
    if (effects) overlayProps.effects = effects;
    inst.map.on('load', function() {{
      inst.overlay.setProps(overlayProps);
    }});
  }});
}})();
</script>
</body>
</html>"""

        if path is not None:
            p = pathlib.Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(html, encoding="utf-8")
        return html


# ---------------------------------------------------------------------------
# Generic layer helper
# ---------------------------------------------------------------------------

def layer(type: str, id: str, data=None, *, extensions: list[str] | None = None, **kwargs) -> dict:
    """Create an arbitrary deck.gl layer definition.

    Works for *any* deck.gl layer class (e.g. ``"HeatmapLayer"``,
    ``"PathLayer"``, ``"ColumnLayer"``).  The JS client resolves
    ``deck[type]`` dynamically.

    Parameters
    ----------
    type
        deck.gl layer class name (e.g. ``"HeatmapLayer"``).
    id
        Unique layer identifier.
    data
        Layer data – list, dict, URL string, DataFrame, or GeoDataFrame.
    extensions
        Optional list of deck.gl extension class names, e.g.
        ``["DataFilterExtension", "BrushingExtension"]``.
        The JS client resolves these into ``new deck.<Name>()`` instances.
    **kwargs
        Any additional deck.gl properties.  ``visible=False`` hides the
        layer without removing it from the stack.
    """
    lyr: dict = {"type": type, "id": id}
    if data is not None:
        lyr["data"] = _serialise_data(data)
    if extensions:
        lyr["@@extensions"] = extensions
    lyr.update(kwargs)
    return lyr


# ---------------------------------------------------------------------------
# Typed layer helpers (convenience wrappers around layer())
# ---------------------------------------------------------------------------

def scatterplot_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ScatterplotLayer`` definition.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points, a remote data URL, or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getFillColor``, ``radiusScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getFillColor": [200, 0, 80, 180],
        "radiusMinPixels": 5,
    }
    defaults.update(kwargs)
    return layer("ScatterplotLayer", id, data, **defaults)


def geojson_layer(id: str, data: dict | list, **kwargs) -> dict:
    """Create a deck.gl ``GeoJsonLayer`` definition.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        A GeoJSON ``FeatureCollection`` or ``Feature`` dict, a URL, or a GeoDataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getFillColor``, ``lineWidthMinPixels``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getFillColor": [0, 128, 255, 120],
        "getLineColor": [0, 128, 255],
        "lineWidthMinPixels": 1,
    }
    defaults.update(kwargs)
    return layer("GeoJsonLayer", id, data, **defaults)


def tile_layer(id: str, data: str | list, **kwargs) -> dict:
    """Create a deck.gl ``TileLayer`` for XYZ or WMS raster tiles.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        A URL template.  For XYZ tiles use ``{z}/{x}/{y}`` placeholders.
        For WMS, use a ``{bbox-epsg-3857}`` or ``{bbox-epsg-4326}``
        placeholder in the ``BBOX`` parameter — the JS client automatically
        converts tile bounds to the appropriate projection.  Example::

            "https://ows.emodnet-bathymetry.eu/wms?"
            "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
            "&FORMAT=image/png&TRANSPARENT=true"
            "&LAYERS=emodnet:mean_atlas_land"
            "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
            "&BBOX={bbox-epsg-3857}"
    """
    defaults: dict[str, Any] = {
        "minZoom": 0,
        "maxZoom": 19,
        "tileSize": 256,
        "renderSubLayers": "@@BitmapLayer",
    }
    defaults.update(kwargs)
    return layer("TileLayer", id, data, **defaults)


def bitmap_layer(id: str, image: str, bounds: list, **kwargs) -> dict:
    """Create a deck.gl ``BitmapLayer`` for a static image overlay.

    Parameters
    ----------
    id
        Unique layer identifier.
    image
        The URL of the image.
    bounds
        ``[left, bottom, right, top]`` in WGS 84.
    """
    return layer("BitmapLayer", id, **{"image": image, "bounds": bounds, **kwargs})
