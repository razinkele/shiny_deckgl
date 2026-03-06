"""Drawing mixin for MapWidget — @mapbox/mapbox-gl-draw integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shiny import Session


class DrawingMixin:
    """Mixin providing drawing tool methods via mapbox-gl-draw.

    Methods
    -------
    enable_draw
        Enable drawing tools on the map.
    disable_draw
        Remove drawing tools from the map.
    get_drawn_features
        Request the current set of drawn features.
    delete_drawn_features
        Delete drawn features.
    drawn_features_input_id
        Shiny input ID for drawn GeoJSON features.
    draw_mode_input_id
        Shiny input ID for the current drawing mode.
    """

    # These attributes are defined in MapWidget but declared here for type checking
    id: str
    _bare_id: str

    async def enable_draw(
        self,
        session: "Session",
        *,
        modes: list[str] | None = None,
        controls: dict[str, bool] | None = None,
        default_mode: str = "simple_select",
    ) -> None:
        """Enable drawing tools on the map.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        modes
            Which drawing modes to enable. Defaults to all:
            ``["draw_point", "draw_line_string", "draw_polygon"]``.
        controls
            Override individual control visibility.
        default_mode
            Initial mode: ``"simple_select"`` or ``"direct_select"``.
        """
        payload: dict = {
            "id": self.id,
            "defaultMode": default_mode,
        }
        if modes is not None:
            payload["modes"] = modes
        if controls is not None:
            payload["controls"] = controls
        await session.send_custom_message("deck_enable_draw", payload)

    async def disable_draw(
        self,
        session: "Session",
    ) -> None:
        """Remove drawing tools from the map."""
        await session.send_custom_message("deck_disable_draw", {
            "id": self.id,
        })

    async def get_drawn_features(
        self,
        session: "Session",
    ) -> None:
        """Request the current set of drawn features.

        Result is delivered as ``input.{id}_drawn_features()``.
        """
        await session.send_custom_message("deck_get_drawn_features", {
            "id": self.id,
        })

    async def delete_drawn_features(
        self,
        session: "Session",
        feature_ids: list[str] | None = None,
    ) -> None:
        """Delete drawn features.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        feature_ids
            List of feature IDs to delete. If ``None``, deletes all.
        """
        await session.send_custom_message("deck_delete_drawn", {
            "id": self.id,
            "featureIds": feature_ids,
        })

    @property
    def drawn_features_input_id(self) -> str:
        """Shiny input for drawn GeoJSON features."""
        return f"{self._bare_id}_drawn_features"

    @property
    def draw_mode_input_id(self) -> str:
        """Shiny input for the current drawing mode."""
        return f"{self._bare_id}_draw_mode"
