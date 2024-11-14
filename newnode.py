import logging
import sys
import os
import json
import asyncio
from aiohttp import web
from threading import Thread
from timeflux.core.node import Node
from timeflux.core.exceptions import WorkerLoadError

class DataStreamer(Node):
    """Stream data to the front end via WebSocket."""

    def __init__(self, host="localhost", port=8000, debug=False):
        self._clients = {}
        self._streams = {}

        if not debug:
            logging.getLogger("asyncio").setLevel(logging.WARNING)
            logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

        app = web.Application()
        app.add_routes([web.get("/ws", self._route_ws)])

        handler = app.make_handler()
        self._loop = asyncio.get_event_loop()
        server = self._loop.create_server(handler, host=host, port=port)
        Thread(target=self._run, args=(server,)).start()
        self.logger.info("DataStreamer available at ws://%s:%d/ws" % (host, port))

    def _run(self, server):
        self._loop.run_until_complete(server)
        self._loop.run_forever()

    async def _route_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        uuid = request.remote
        self._clients[uuid] = ws
        self.logger.info("Client connected: %s", uuid)

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                pass  # Handle incoming messages if needed

       # del self._clients[uuid]
        self.logger.info("Client disconnected: %s", uuid)
        return ws


    def update(self):
        # Forward node input streams to WebSocket
        for name, port in self.ports.items():
            if name.startswith("i_") and port.data is not None:
                stream = name[2:]
                data = {
                    "name": stream,
                    "data": port.data.to_dict(orient="records"),
                    "meta": port.meta,
                }
                asyncio.run_coroutine_threadsafe(self._send(data), self._loop)

    def terminate(self):
        self._loop.call_soon_threadsafe(self._loop.stop)
