"""Navigation mixin for MapWidget — camera transitions and bounds fitting."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shiny import Session


class NavigationMixin:
    """Mixin providing navigation and camera control methods.

    Methods
    -------
    fly_to
        Smooth fly-to camera transition.
    ease_to
        Smooth ease-to camera transition.
    fit_bounds
        Fit map to geographic bounds.
    compute_bounds
        Compute bounds from GeoJSON.
    """

    # These attributes are defined in MapWidget but declared here for type checking
    id: str

    @staticmethod
    def _build_view_state(
        longitude: float,
        latitude: float,
        zoom: float | None = None,
        pitch: float | None = None,
        bearing: float | None = None,
    ) -> dict:
        """Build a partial view-state dict, omitting ``None`` values."""
        vs: dict = {"longitude": longitude, "latitude": latitude}
        if zoom is not None:
            vs["zoom"] = zoom
        if pitch is not None:
            vs["pitch"] = pitch
        if bearing is not None:
            vs["bearing"] = bearing
        return vs

    async def fly_to(
        self,
        session: "Session",
        longitude: float,
        latitude: float,
        zoom: float | None = None,
        pitch: float | None = None,
        bearing: float | None = None,
        speed: float = 1.2,
        duration: int | str = "auto",
    ) -> None:
        """Smooth fly-to camera transition using MapLibre ``flyTo``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        longitude
            Target longitude.
        latitude
            Target latitude.
        zoom
            Target zoom level (optional).
        pitch
            Target pitch in degrees (optional).
        bearing
            Target bearing in degrees (optional).
        speed
            Fly speed multiplier (default ``1.2``).
        duration
            Duration in ms, or ``"auto"`` for MapLibre-calculated duration.
        """
        await session.send_custom_message("deck_fly_to", {
            "id": self.id,
            "viewState": self._build_view_state(longitude, latitude, zoom, pitch, bearing),
            "speed": speed,
            "duration": duration,
        })

    async def ease_to(
        self,
        session: "Session",
        longitude: float,
        latitude: float,
        zoom: float | None = None,
        pitch: float | None = None,
        bearing: float | None = None,
        duration: int = 1000,
    ) -> None:
        """Smooth ease-to camera transition using MapLibre ``easeTo``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        longitude
            Target longitude.
        latitude
            Target latitude.
        zoom
            Target zoom level (optional).
        pitch
            Target pitch in degrees (optional).
        bearing
            Target bearing in degrees (optional).
        duration
            Duration in milliseconds (default ``1000``).
        """
        await session.send_custom_message("deck_ease_to", {
            "id": self.id,
            "viewState": self._build_view_state(longitude, latitude, zoom, pitch, bearing),
            "duration": duration,
        })

    async def fit_bounds(
        self,
        session: "Session",
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
