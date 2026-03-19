"""Time-series animation controls for Shiny."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

__all__ = ["timeline_control", "timeline_server"]


def timeline_control(
    id: str,
    labels: list[str],
    *,
    interval_ms: int = 1000,
) -> Any:
    """UI fragment for time-series animation controls.

    Returns Play/Pause button, a slider scrubber mapped to label indices,
    and a text display of the current label.

    Parameters
    ----------
    id
        Shiny module namespace ID.
    labels
        List of step labels (e.g. month names). Length determines slider range.
    interval_ms
        Milliseconds between frames during auto-play (default 1000).

    Returns
    -------
    shiny.ui.TagList
        Ready to embed in a sidebar.
    """
    if not labels:
        raise ValueError("labels must be a non-empty list")
    if interval_ms <= 0:
        raise ValueError(f"interval_ms must be > 0, got {interval_ms}")

    from shiny import module, ui

    @module.ui
    def _inner_ui():
        choices = {str(i): lbl for i, lbl in enumerate(labels)}
        return ui.TagList(
            ui.layout_columns(
                ui.input_action_button(
                    "play", "\u25B6 Play",
                    class_="btn-sm btn-success",
                ),
                ui.input_action_button(
                    "pause", "\u23F8 Pause",
                    class_="btn-sm btn-warning",
                ),
                col_widths=(6, 6),
            ),
            ui.input_slider(
                "step", "Time step",
                min=0, max=len(labels) - 1, value=0, step=1,
                ticks=False,
            ),
            ui.output_text("current_label"),
        )

    return _inner_ui(id)


def timeline_server(
    id: str,
    labels: list[str],
    *,
    interval_ms: int = 1000,
) -> Any:
    """Server logic for time-series animation controls.

    Wires the Play/Pause buttons and step slider produced by
    :func:`timeline_control`. Returns a namespace with reactive
    accessors for the current step.

    Unlike ``trips_animation_server``, this does NOT take ``widget``
    or ``session`` because it doesn't directly control a widget —
    it only exposes reactive values that the caller wires into
    their own layer-building logic.

    Parameters
    ----------
    id
        Must match the *id* passed to :func:`timeline_control`.
    labels
        Same label list passed to :func:`timeline_control`.
    interval_ms
        Milliseconds between auto-play frames (default 1000).

    Returns
    -------
    types.SimpleNamespace
        ``.index`` — callable returning current 0-based step index.
        ``.label`` — callable returning current label string.
    """
    import types

    if not labels:
        raise ValueError("labels must be a non-empty list")

    try:
        from shiny import module, reactive
    except ImportError:
        return types.SimpleNamespace(
            index=lambda: 0,
            label=lambda: labels[0] if labels else "",
        )

    result_holder: list = []

    @module.server
    def _inner_server(input, output, inner_session):
        _playing = reactive.Value(False)

        @reactive.Effect
        @reactive.event(input.play)
        def _on_play():
            _playing.set(True)

        @reactive.Effect
        @reactive.event(input.pause)
        def _on_pause():
            _playing.set(False)

        @reactive.Effect
        async def _auto_advance():
            """Polling loop: advances the slider when playing."""
            if not _playing():
                return
            reactive.invalidate_later(interval_ms / 1000.0)
            current = input.step()
            next_val = (current + 1) % len(labels)
            from shiny import ui as _ui
            _ui.update_slider("step", value=next_val, session=inner_session)

        @output
        @reactive.event(input.step)
        def current_label():
            idx = input.step()
            return f"{labels[idx]}"

        result_holder.append(types.SimpleNamespace(
            index=input.step,
            label=lambda: labels[input.step()],
        ))

    try:
        _inner_server(id)
    except RuntimeError:
        # Called outside an active Shiny session (e.g. tests, import time)
        pass

    if result_holder:
        return result_holder[0]

    # Fallback for environments without active Shiny session
    return types.SimpleNamespace(
        index=lambda: 0,
        label=lambda: labels[0] if labels else "",
    )
