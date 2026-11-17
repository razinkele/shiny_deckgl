"""Run the demo with Shiny's silently swallowed websocket send failures logged.

Used by demo_sweep.py. Patches the private shiny._connection.StarletteConnection
(Shiny 1.9), so it may need updating when Shiny changes.
"""
import sys
import traceback

import shiny._connection as c
import uvicorn

_orig = c.StarletteConnection.send


async def send(self, message):
    try:
        await self.conn.send_text(message)
    except BaseException as e:
        print(f"SEND FAILED len={len(message)} {e!r}\n{traceback.format_exc()}", flush=True)
        if not self._is_closed():
            await self.close(1008, "Send failure")


c.StarletteConnection.send = send

from shiny_deckgl.app import app  # noqa: E402

uvicorn.run(app, port=int(sys.argv[1]), log_level="warning")
