"""MapLibre layers mixin for MapWidget — native MapLibre sources, layers, and styling."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shiny import Session


class MapLibreLayersMixin:
    """Mixin providing native MapLibre source and layer management.

    Methods
    -------
    add_source
        Add a native MapLibre source.
    add_maplibre_layer
        Add a native MapLibre rendering layer.
    remove_maplibre_layer
        Remove a native MapLibre layer.
    remove_source
        Remove a native MapLibre source.
    set_source_data
        Update GeoJSON source data.
    add_cluster_layer
        Add clustered GeoJSON points.
    remove_cluster_layer
        Remove a cluster layer group.
    add_image
        Load an image for symbol layers.
    remove_image
        Remove a loaded image.
    has_image
        Check if an image is loaded.
    set_paint_property
        Set a paint property on a layer.
    set_layout_property
        Set a layout property on a layer.
    set_filter
        Set a data-driven filter on a layer.
    set_projection
        Set map projection (mercator/globe).
    set_terrain
        Enable/disable 3D terrain.
    set_sky
        Set sky/atmosphere properties.
    """

    # These attributes are defined in MapWidget but declared here for type checking
    id: str
    _serialise_data: Any  # Will be imported from parent

    async def add_source(
        self,
        session: "Session",
        source_id: str,
        source_spec: dict,
    ) -> None:
        """Add a native MapLibre source.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            Unique source identifier.
        source_spec
            MapLibre source specification dict. Must include ``"type"``
            (``"geojson"``, ``"raster"``, ``"vector"``, ``"raster-dem"``,
            ``"image"``).
        """
        await session.send_custom_message("deck_add_source", {
            "id": self.id,
            "sourceId": source_id,
            "spec": source_spec,
        })

    async def add_maplibre_layer(
        self,
        session: "Session",
        layer_spec: dict,
        *,
        before_id: str | None = None,
    ) -> None:
        """Add a native MapLibre rendering layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_spec
            MapLibre layer specification dict with at minimum ``"id"``,
            ``"type"``, and ``"source"``.
        before_id
            Insert this layer before the given layer ID in the stack.
            ``None`` adds on top of all MapLibre layers.
        """
        payload: dict = {
            "id": self.id,
            "layerSpec": layer_spec,
        }
        if before_id is not None:
            payload["beforeId"] = before_id
        await session.send_custom_message("deck_add_maplibre_layer", payload)

    async def remove_maplibre_layer(
        self,
        session: "Session",
        layer_id: str,
    ) -> None:
        """Remove a native MapLibre layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The ``id`` of the MapLibre layer to remove.
        """
        await session.send_custom_message("deck_remove_maplibre_layer", {
            "id": self.id,
            "layerId": layer_id,
        })

    async def remove_source(
        self,
        session: "Session",
        source_id: str,
    ) -> None:
        """Remove a native MapLibre source.

        All layers using this source must be removed first.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            The source identifier to remove.
        """
        await session.send_custom_message("deck_remove_source", {
            "id": self.id,
            "sourceId": source_id,
        })

    async def set_source_data(
        self,
        session: "Session",
        source_id: str,
        data: dict | str,
    ) -> None:
        """Update the data of an existing GeoJSON source.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            The source identifier (must be a GeoJSON source).
        data
            New GeoJSON dict or URL string.
        """
        from .._data_utils import _serialise_data
        serialised = _serialise_data(data)
        await session.send_custom_message("deck_set_source_data", {
            "id": self.id,
            "sourceId": source_id,
            "data": serialised,
        })

    async def add_cluster_layer(
        self,
        session: "Session",
        source_id: str,
        data: dict | str | list,
        *,
        cluster_radius: int = 50,
        cluster_max_zoom: int = 14,
        cluster_color: str = "#51bbd6",
        cluster_stroke_color: str = "#ffffff",
        cluster_stroke_width: int = 1,
        cluster_text_color: str = "#ffffff",
        cluster_text_size: int = 12,
        point_color: str = "#11b4da",
        point_radius: int = 5,
        point_stroke_color: str = "#ffffff",
        point_stroke_width: int = 1,
        size_steps: list | None = None,
        cluster_properties: dict | None = None,
    ) -> None:
        """Add clustered GeoJSON points with click-to-zoom.

        Creates a GeoJSON source with ``cluster: true`` plus three MapLibre
        layers (cluster circles, count labels, and unclustered points).
        Clicking a cluster zooms in to expand it.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            Unique source identifier.  Three layers will be created:
            ``{source_id}-clusters``, ``{source_id}-count``, and
            ``{source_id}-unclustered``.
        data
            GeoJSON ``FeatureCollection`` (dict), URL string, or list of
            ``[lon, lat]`` pairs (auto-wrapped into a FeatureCollection).
        cluster_radius
            Pixel radius within which points are merged.
        cluster_max_zoom
            Maximum zoom level at which clusters are generated.
        cluster_color
            Fill color for cluster circles.
        cluster_stroke_color
            Stroke color for cluster circles.
        cluster_stroke_width
            Stroke width for cluster circles.
        cluster_text_color
            Color for cluster count labels.
        cluster_text_size
            Font size for cluster count labels.
        point_color
            Fill color for unclustered point circles.
        point_radius
            Radius for unclustered point circles.
        point_stroke_color
            Stroke color for unclustered point circles.
        point_stroke_width
            Stroke width for unclustered point circles.
        size_steps
            List of ``[count_threshold, circle_radius]`` pairs for
            interpolating cluster circle size.  Defaults to
            ``[[0, 18], [100, 24], [750, 32]]``.
        cluster_properties
            MapLibre ``clusterProperties`` for aggregate computations.
        """
        from .._data_utils import _serialise_data

        # Auto-wrap a list of [lon, lat] into a GeoJSON FeatureCollection
        if isinstance(data, list) and data and isinstance(data[0], (list, tuple)):
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": pt[:2]},
                        "properties": pt[2] if len(pt) > 2 and isinstance(pt[2], dict) else {},
                    }
                    for pt in data
                ],
            }

        serialised = _serialise_data(data)

        options: dict = {
            "clusterRadius": cluster_radius,
            "clusterMaxZoom": cluster_max_zoom,
            "clusterColor": cluster_color,
            "clusterStrokeColor": cluster_stroke_color,
            "clusterStrokeWidth": cluster_stroke_width,
            "clusterTextColor": cluster_text_color,
            "clusterTextSize": cluster_text_size,
            "pointColor": point_color,
            "pointRadius": point_radius,
            "pointStrokeColor": point_stroke_color,
            "pointStrokeWidth": point_stroke_width,
        }
        if size_steps is not None:
            options["sizeSteps"] = size_steps
        if cluster_properties is not None:
            options["clusterProperties"] = cluster_properties

        await session.send_custom_message("deck_add_cluster_layer", {
            "id": self.id,
            "sourceId": source_id,
            "data": serialised,
            "options": options,
        })

    async def remove_cluster_layer(
        self,
        session: "Session",
        source_id: str,
    ) -> None:
        """Remove a cluster layer group created by :meth:`add_cluster_layer`.

        Removes the three MapLibre layers (``-clusters``, ``-count``,
        ``-unclustered``) and the underlying GeoJSON source.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            The source identifier used in :meth:`add_cluster_layer`.
        """
        await session.send_custom_message("deck_remove_cluster_layer", {
            "id": self.id,
            "sourceId": source_id,
        })

    async def add_image(
        self,
        session: "Session",
        image_id: str,
        url: str,
        *,
        pixel_ratio: float = 1,
        sdf: bool = False,
    ) -> None:
        """Load an image into the map for use with symbol layers.

        The image is fetched by the browser from *url* and registered under
        *image_id*.  Once loaded it can be referenced by a ``symbol`` layer's
        ``layout["icon-image"]`` property.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        image_id
            Unique name to register the image under.
        url
            HTTP(S) URL or data-URI of the image (PNG, JPEG, WebP, SVG).
        pixel_ratio
            Device pixel ratio for retina displays (default ``1``).
        sdf
            If ``True`` the image is treated as a signed-distance-field icon
            that can be recolored at runtime with ``icon-color`` paint
            property.
        """
        await session.send_custom_message("deck_add_image", {
            "id": self.id,
            "imageId": image_id,
            "url": url,
            "pixelRatio": pixel_ratio,
            "sdf": sdf,
        })

    async def remove_image(
        self,
        session: "Session",
        image_id: str,
    ) -> None:
        """Remove a previously loaded image from the map style.

        Any symbol layer still referencing this image will lose its icon.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        image_id
            The image name passed to :meth:`add_image`.
        """
        await session.send_custom_message("deck_remove_image", {
            "id": self.id,
            "imageId": image_id,
        })

    async def has_image(
        self,
        session: "Session",
        image_id: str,
    ) -> None:
        """Check whether *image_id* is loaded and report back via input.

        The result is delivered asynchronously as a boolean through
        ``input.<map_id>_has_image``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        image_id
            The image name to check.
        """
        await session.send_custom_message("deck_has_image", {
            "id": self.id,
            "imageId": image_id,
        })

    async def set_paint_property(
        self,
        session: "Session",
        layer_id: str,
        name: str,
        value: Any,
    ) -> None:
        """Set a paint property on a native MapLibre layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The MapLibre layer id.
        name
            Paint property name (e.g. ``"fill-opacity"``, ``"line-color"``).
        value
            New value (number, string, array, or MapLibre expression).
        """
        await session.send_custom_message("deck_set_paint_property", {
            "id": self.id,
            "layerId": layer_id,
            "name": name,
            "value": value,
        })

    async def set_layout_property(
        self,
        session: "Session",
        layer_id: str,
        name: str,
        value: Any,
    ) -> None:
        """Set a layout property on a native MapLibre layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The MapLibre layer id.
        name
            Layout property name (e.g. ``"visibility"``).
        value
            New value (e.g. ``"visible"`` or ``"none"``).
        """
        await session.send_custom_message("deck_set_layout_property", {
            "id": self.id,
            "layerId": layer_id,
            "name": name,
            "value": value,
        })

    async def set_filter(
        self,
        session: "Session",
        layer_id: str,
        filter_expr: list | None = None,
    ) -> None:
        """Set a data-driven filter on a native MapLibre layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The MapLibre layer id.
        filter_expr
            A MapLibre filter expression, e.g.
            ``[">=", ["get", "depth"], 100]``. Pass ``None`` to clear.
        """
        await session.send_custom_message("deck_set_filter", {
            "id": self.id,
            "layerId": layer_id,
            "filter": filter_expr,
        })

    async def set_projection(
        self,
        session: "Session",
        projection: str = "mercator",
    ) -> None:
        """Set the map projection.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        projection
            ``"mercator"`` (default flat map) or ``"globe"`` (3D sphere).
            Requires MapLibre GL JS v4+.
        """
        if projection not in ("mercator", "globe"):
            raise ValueError(
                f"Unknown projection {projection!r}. Use 'mercator' or 'globe'."
            )
        await session.send_custom_message("deck_set_projection", {
            "id": self.id,
            "projection": projection,
        })

    async def set_terrain(
        self,
        session: "Session",
        source: str | None = None,
        exaggeration: float = 1.0,
    ) -> None:
        """Enable or disable 3D terrain rendering.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source
            The id of a ``raster-dem`` source previously added via
            ``add_source()``. Pass ``None`` to disable terrain.
        exaggeration
            Vertical exaggeration factor (default 1.0 = real scale).
        """
        terrain = None
        if source is not None:
            terrain = {"source": source, "exaggeration": exaggeration}
        await session.send_custom_message("deck_set_terrain", {
            "id": self.id,
            "terrain": terrain,
        })

    async def set_sky(
        self,
        session: "Session",
        sky: dict | None = None,
    ) -> None:
        """Set the sky/atmosphere properties (works best with terrain).

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        sky
            Sky specification dict. Pass ``None`` to reset to default.
        """
        await session.send_custom_message("deck_set_sky", {
            "id": self.id,
            "sky": sky,
        })
